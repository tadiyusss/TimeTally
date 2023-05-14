from flask import Flask, render_template, session, request, redirect, send_file
import random
import string
from pysondb import getDb
from werkzeug.utils import secure_filename
import hashlib
import qrcode
import json
import os
from getpass import getpass
from datetime import datetime
import sys

image_extensions = {"png", "jpg", "jpeg", "gif"}

if not os.path.exists('profile'):
    os.mkdir('profile')
if not os.path.exists('qr'):
    os.mkdir('qr')
    
def random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def md5_hash(password):
    salt = random_string(32)
    salted_password = password + salt
    return {
        'salt': salt,
        'password': hashlib.md5(salted_password.encode()).hexdigest()
    }

def verify_password(password, salt, hashed_password):
    salted_password = password + salt
    return hashlib.md5(salted_password.encode()).hexdigest() == hashed_password

def allowed_file(filename, extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in extensions

if not os.path.exists('admin_details.json'):
    username = input("Enter admin username: ")
    password = getpass("Enter admin password: ")
    hashed_password = md5_hash(password)
    data = {
        'username': username,
        'password': hashed_password['password'],
        'salt': hashed_password['salt']
    }
    with open('admin_details.json', 'w') as f:
        json.dump(data, f)
    print("Admin account created successfully")

app = Flask(__name__)
app.secret_key = random_string(32)
users_db = getDb("users.json")
attendance_db = getDb("attendance.json")

# ADMIN ROUTES

@app.route('/admin/dashboard/scanner')
def scanner():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect('/')
    return render_template('scanner.html')

@app.route('/admin/dashboard/edit/<identifier>', methods=['GET', 'POST'])
def edit(identifier):
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect('/')
    if request.method == 'POST':
        required = ['date', 'identifier', 'status', 'student_number', 'time']
        for field in required:
            if field not in request.form:
                data = {
                    'status': 'error',
                    'message': f'{field} is required'
                }
                return render_template('edit.html', response_data=data)
            if len(request.form[field]) < 1:
                data = {
                    'status': 'error',
                    'message': f'{field} cannot be empty'
                }
                return render_template('edit.html', response_data=data)
            if request.form[field].isspace():
                data = {
                    'status': 'error',
                    'message': f'{field} cannot be spaces'
                }
                return render_template('edit.html', response_data=data)
        attendance_db.updateByQuery({'identifier': identifier}, request.form)
        data = {
            'status': 'success',
            'message': 'Attendance updated successfully'
        }
        return redirect('/admin/dashboard')
    else:
        attendance_data = attendance_db.getByQuery({'identifier': identifier})
        if len(attendance_data) == 0:
            data = {
                'status': 'error',
                'message': 'Attendance not found'
            }
        else:
            attendance_data = attendance_data[0]
            data = {
                'status': 'success',
                'attendance_data': attendance_data
            }
        return render_template('edit.html', data=data)

@app.route('/admin/dashboard/search', methods=['GET', 'POST'])
def search():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect('/')
    if request.method == 'POST':
        if 'student_number' in request.form:
            user_data = users_db.getByQuery({'student_number': request.form['student_number']})
            attendance = sorted(attendance_db.getByQuery({'student_number': request.form['student_number']}), key=lambda k: datetime.strptime(k['complete_date'], '%d/%m/%Y %H:%M:%S'), reverse=True)
            if len(user_data) != 0:
                user_data = user_data[0]
                user_data.pop('salt')
                user_data.pop('password')
                user_data.pop('identifer')
            data = {
                'status': 'success',
                'user_data': user_data,
                'attendance': attendance
            }
            return render_template('search.html', data=data)
    else:
        return render_template('search.html')

@app.route('/dashboard')
def dashboard():
    if 'user_type' in session:
        if session['user_type'] == 'admin':
            return redirect('/admin/dashboard')
        else: 
            retrieved_data = users_db.getByQuery({'student_number': session['student_id']})[0]
            retrieved_data.pop('salt')
            retrieved_data.pop('password')
            retrieved_data.pop('identifer')
            attendance = attendance_db.getByQuery({'student_number': session['student_id']})
            #sort attendance by date
            attendance = sorted(attendance, key=lambda k: datetime.strptime(k['complete_date'], '%d/%m/%Y %H:%M:%S'), reverse=True)
            return render_template('dashboard.html', data=retrieved_data, attendance=attendance)

    else:
        return redirect('/')
    
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_type' in session:
        if session['user_type'] == 'admin':
            return redirect('/admin/dashboard')
        else:
            return redirect('/dashboard')
    if request.method == 'POST':
        required = ['student_id', 'password']
        for field in required:
            if field not in request.form:
                return render_template('login.html', message="Please fill all the fields")
            if len(request.form[field]) < 1:
                return render_template('login.html', message="Please fill all the fields")
            if request.form[field].isspace():
                return render_template('login.html', message="Please fill all the fields")
        with open('admin_details.json', 'r') as f:
            admin_details = json.load(f)
        if request.form['student_id'] == admin_details['username']:
            if verify_password(request.form['password'], admin_details['salt'], admin_details['password']):
                session['student_id'] = admin_details['username']
                session['user_type'] = 'admin'
                return redirect('/admin/dashboard')

        retrieved_data = users_db.getByQuery({'student_number': request.form['student_id']})
        if len(retrieved_data) == 0:
            return render_template('login.html', message="Student ID does not exist")
        if not verify_password(request.form['password'], retrieved_data[0]['salt'], retrieved_data[0]['password']):
            return render_template('login.html', message="Incorrect password")
        session['student_id'] = retrieved_data[0]['student_number']
        session['user_type'] = 'student'
        return redirect('/dashboard')
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        required = ['fname', 'mname', 'lname', 'snumber', 'password', 'confirmPassword', 'section', 'gradeLevel']
        for field in required:
            if field not in request.form:
                return render_template('register.html', message="Please fill all the fields")
            if len(request.form[field]) == 0:
                return render_template('register.html', message="Please fill all the fields")
            if request.form[field].isspace():
                return render_template('register.html', message="Please fill all the fields")
        if request.form['password'] != request.form['confirmPassword']:
            return render_template('register.html', message="Passwords do not match")
        if len(request.form['password']) < 8:
            return render_template('register.html', message="Password must be at least 8 characters long")
        if len(request.form['snumber']) != 9:
            return render_template('register.html', message="Student number must be 9 digits long")
        if not request.form['snumber'].isdigit():
            return render_template('register.html', message="Student number must be a number")
        if users_db.getByQuery({'student_number': request.form['snumber']}):
            return render_template('register.html', message="Student number already exists")
        if 'profile' not in request.files:

            return render_template('register.html', message=request.files)
        file = request.files['profile']
        if file.filename == '':
            return render_template('register.html', message="File name cannot be empty")
        if file and allowed_file(file.filename, image_extensions):
            filename = request.form['snumber'] + "." + secure_filename(file.filename).split(".")[-1]
            file.save(os.path.join('profile/', filename))
        else:
            return render_template('register.html', message="Invalid file type")
        hashed_password = md5_hash(request.form['password'])
        img_qr = qrcode.make(request.form['snumber'])
        img_qr.save('qr/' + request.form['snumber'] + '.png')
        users_data = {
            'fname': request.form['fname'],
            'mname': request.form['mname'],
            'lname': request.form['lname'],
            'student_number': request.form['snumber'],
            'password': hashed_password['password'],
            'identifer': random_string(32),
            'section': request.form['section'],
            'profile': filename,
            'type': 'Student',
            'grade_level': request.form['gradeLevel'],
            'salt': hashed_password['salt']
        }
        users_db.add(users_data)
        return redirect('/')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_type' not in session or session['user_type'] != 'admin':
        return redirect('/')
    attendance = attendance_db.getAll()
    attendance = sorted(attendance, key=lambda x: datetime.strptime(x['complete_date'], "%d/%m/%Y %H:%M:%S"), reverse=True)
    return render_template('admin_dashboard.html', attendance=attendance)

# API ROUTES

@app.route('/api/addAttendance', methods=['POST'])
def addAttendance():
    data = {
        'student_number': request.form['student_id'],
        'status': 'Success',
        'date': datetime.now().strftime("%b %m %Y"),
        'time': datetime.now().strftime("%H:%M:%S"),
        'complete_date': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'identifier': random_string(32)
    }
    retrieved_data = users_db.getByQuery({'student_number': request.form['student_id']})[0]
    retrieved_data.pop('salt')
    retrieved_data.pop('password')
    retrieved_data.pop('identifer')

    attendance_db.add(data)
    return {
        'status': 'success',
        'message': 'Attendance added successfully',
        'student_number': request.form['student_id'],
        'data': retrieved_data
    }

@app.route('/api/view_profile/<student_id>')
def view_profile(student_id):
    if 'user_type' not in session:
        return redirect('/')
    if session['student_id'] != student_id and session['user_type'] != 'admin':
        return redirect('/')
    retrieved_data = users_db.getByQuery({'student_number': student_id})[0]
    return send_file('profile/' + retrieved_data['profile'], mimetype='image/png')

@app.route('/api/view_qr/<student_id>')
def view_qr(student_id):
    if 'user_type' not in session:
        return redirect('/')
    if session['student_id'] != student_id:
        return redirect('/')
    return send_file('qr/' + student_id + '.png', mimetype='image/png')

if __name__ == '__main__':
    if '--ssl' in sys.argv:
        app.run(host='0.0.0.0', ssl_context='adhoc')
    else:
        app.run(host='0.0.0.0')