from flask import Flask, render_template, session, request, redirect, abort, send_file
import random
import string
from pysondb import getDb
import hashlib
import bleach
import qrcode
import datetime
import os

def random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def sha256_hash(password):
    salt = random_string(32)
    salted_password = password + salt
    return {
        'salt': salt,
        'password': hashlib.sha256(salted_password.encode()).hexdigest()
    }

def verify_password(password, salt, hashed_password):
    salted_password = password + salt
    return hashlib.sha256(salted_password.encode()).hexdigest() == hashed_password

app = Flask(__name__)
app.secret_key = random_string(32)
teachers_db = getDb("teachers.json")
student_db = getDb("students.json")
class_db = getDb("class.json")
attendance_db = getDb("attendance.json")

for x in ['profiles', 'qr']:
    if x not in os.listdir():
        print(f"[ + ] Creating directory {x}")
        os.mkdir(x)


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] == 'Teacher':
        account_data = teachers_db.getByQuery({'username': session['username']})
    else:
        account_data = student_db.getByQuery({'username': session['username']})
    return render_template('profile.html', account_data = account_data[0])

@app.route('/scanner/<identifier>')
def scanner(identifier):
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Teacher':
        return redirect('/')
    class_data = class_db.getByQuery({'identifier': identifier})
    if len(class_data) == 0:
        return abort(404)
    if class_data[0]['teacher'] != session['username']:
        return abort(404)
    return render_template('scanner.html', class_data=class_data[0])

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return redirect('/dashboard')
    if request.method == 'POST':
        required = ['username', 'password']
        for field in required:
            if field not in request.form:
                return render_template('login.html', message="Please fill all the fields")
            if len(request.form[field]) < 1:
                return render_template('login.html', message="Please fill all the fields")
            if request.form[field].isspace():
                return render_template('login.html', message="Please fill all the fields")
        for db in [teachers_db, student_db]:
            retrieved_data = db.getByQuery({'username': request.form['username']})
            if len(retrieved_data) == 1 and verify_password(request.form['password'], retrieved_data[0]['salt'], retrieved_data[0]['password']):
                session['username'] = retrieved_data[0]['username']
                session['account_type'] = retrieved_data[0]['account_type']
                session['identifier'] = retrieved_data[0]['identifier']
                return redirect('/dashboard')
        return render_template('login.html', message="Incorrect username or password")
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect('/dashboard')
    if request.method == 'POST':
        required = ['name', 'username', 'password', 'account_type']
        for field in required:
            if field not in request.form:
                return render_template('register.html', message="Please fill all the fields")
            if len(request.form[field]) < 1:
                return render_template('register.html', message="Please fill all the fields")
            if request.form[field].isspace():
                return render_template('register.html', message="Please fill all the fields")
        data = {
            'username': request.form['username']
        }
        if len(teachers_db.getByQuery(data)) > 0:
            return render_template('register.html', message="Username already exists")
        if len(student_db.getByQuery(data)) > 0:
            return render_template('register.html', message="Username already exists")
        if request.form['account_type'] not in ['Student', 'Teacher']:
            return render_template('register.html', message="Invalid account type")
        password = sha256_hash(request.form['password'])
        if request.form['account_type'] == 'Teacher':
            data = {
                'name': bleach.clean(request.form['name']),
                'username':  bleach.clean(request.form['username']),
                'account_type':  bleach.clean(request.form['account_type']),
                'password': password['password'],
                'salt': password['salt'],
                'identifier': random_string(10),
                'registered_ip': request.remote_addr
            }
            teachers_db.add(data)
        else:
            data = {
                'name': bleach.clean(request.form['name']),
                'username':  bleach.clean(request.form['username']),
                'account_type':  bleach.clean(request.form['account_type']),
                'password': password['password'],
                'salt': password['salt'],
                'identifier': random_string(10),
                'classes': [],
                'registered_ip': request.remote_addr
            }
            student_db.add(data)
        session['username'] = request.form['username']
        session['account_type'] = request.form['account_type']
        session['identifier'] = data['identifier']
        return render_template('register.html', message="Account created successfully"), {"Refresh": "1; url=/"}
    else:
        return render_template('register.html')

@app.route('/logout')
def logout():
    if 'username' not in session:
        return redirect('/')
    session.pop('username')
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] == 'Student':
        return render_template('dashboard.html')
    else:
        return render_template('dashboard.html')

@app.route('/class/<identifier>')
def class_page(identifier):
    if 'username' not in session:
        return redirect('/')
    class_data = class_db.getByQuery({'identifier': identifier})
    if len(class_data) == 0:
        return abort(404)
    if session['username'] not in class_data[0]['students'] and session['username'] != class_data[0]['teacher']:
        return abort(404)
    del class_data[0]['students']
    if session['account_type'] == 'Teacher':
        attendance_data = attendance_db.getByQuery({'class_identifier': identifier})
    else:
        attendance_data = attendance_db.getByQuery({'class_identifier': identifier, 'username': session['username']})
    return render_template('class.html', class_data=class_data[0], attendance_data=attendance_data)
        

@app.route('/class/edit/<identifier>', methods=['GET', 'POST'])
def edit_attendance(identifier):
    class_identifier = identifier.split(':')[0]
    attendance_id = identifier.split(':')[1]
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Teacher':
        return abort(404)
    class_data = class_db.getByQuery({'identifier': class_identifier})
    attendance_data = attendance_db.getById(attendance_id)
    if len(class_data) == 0:
        return abort(404)
    if class_data[0]['teacher'] != session['username']:
        return abort(404)
    if len(attendance_data) == 0:
        return abort(404)
    if request.method == 'GET':
        return render_template('edit.html', class_data = class_data[0], attendance_data = attendance_data, message = "")
    elif request.method == 'POST':
        required = ['status']
        for x in required:
            if x not in request.form:
                return render_template('edit.html', class_data = class_data[0], attendance_data = attendance_data, message = "Please fill all the fields")
            if len(request.form[x]) < 1:
                return render_template('edit.html', class_data = class_data[0], attendance_data = attendance_data, message = "Please fill all the fields")
            if request.form[x].isspace():
                return render_template('edit.html', class_data = class_data[0], attendance_data = attendance_data, message = "Please fill all the fields")
            if request.form[x] not in ['Present', 'Absent', 'Late', 'Excused']:
                return render_template('edit.html', class_data = class_data[0], attendance_data = attendance_data, message = "Invalid student status")
        attendance_db.updateById(attendance_id, {'status': request.form['status']})
        return redirect(f'/class/{class_identifier}')
    else:
        return abort(404)

# API ROUTES

# API FOR PROFILE HANDLING

@app.route('/api/change/profile_image', methods=['POST'])
def change_profile():
    if 'username' not in session:
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    if 'profile_image' not in request.files:
        return {
            'status': 'error',
            'message': 'Please select a file'
        }
    if request.files['profile_image'].filename == '':
        return {
            'status': 'error',
            'message': 'Please select a file'
        }
    if request.files['profile_image'].filename.isspace():
        return {
            'status': 'error',
            'message': 'Please select a file'
        }
    if request.files['profile_image'].filename.split('.')[-1].lower() not in ['png', 'jpg', 'jpeg', 'gif']:
        return {
            'status': 'error',
            'message': 'Invalid file type'
        }
    if session['account_type'] == 'Teacher':
        account_data = teachers_db.getByQuery({'username': session['username']})
    else:
        account_data = student_db.getByQuery({'username': session['username']})

    profile_image = request.files['profile_image']
    profile_image.save(f"profiles/{account_data[0]['identifier']}.{profile_image.filename.split('.')[-1]}")
    return {
        'status': 'success',
        'message': 'Profile image changed successfully'
    }


@app.route('/api/change/password', methods=['POST'])
def change_password():
    if 'username' not in session:
        return redirect('/')
    required = ['currentPassword', 'newPassword', 'confirmNewPassword']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': f'{x} is required'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': f'{x} cannot be empty'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    if request.form['newPassword'] != request.form['confirmNewPassword']:
        return {
            'status': 'error',
            'message': 'Passwords do not match'
        }
    if session['account_type'] == 'Teacher':
        account_data = teachers_db.getByQuery({'username': session['username']})
    else:
        account_data = student_db.getByQuery({'username': session['username']})
    if not verify_password(request.form['currentPassword'], account_data[0]['salt'], account_data[0]['password']):
        return {
            'status': 'error',
            'message': 'Incorrect current password'
        }
    password = sha256_hash(request.form['newPassword'])
    if session['account_type'] == 'Teacher':
        teachers_db.updateByQuery({'username': session['username']}, {'password': password['password'], 'salt': password['salt']})
    else:
        student_db.updateByQuery({'username': session['username']}, {'password': password['password'], 'salt': password['salt']})
    return {
        'status': 'success',
        'message': 'Password changed successfully'
    }

@app.route('/api/update/profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return redirect('/')
    required = ['name', 'username']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    if session['account_type'] == 'Teacher':
        teachers_db.update({'username': session['username']}, {'name': bleach.clean(request.form['name']), 'username': bleach.clean(request.form['username'])})
    else:
        student_db.update({'username': session['username']}, {'name': bleach.clean(request.form['name']), 'username': bleach.clean(request.form['username'])})
    session['username'] = bleach.clean(request.form['username'])
    return {
        'status': 'success',
        'message': 'Profile updated successfully'
    }
# API FOR QR HANDLING
@app.route('/api/get/qr/<data>')
def get_qr(data):
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Student':
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    if len(data.split('-')) != 2:
        return {
            'status': 'error',
            'message': 'Invalid argument'
        }
    student_identifier = data.split('-')[0]
    class_identifier = data.split('-')[1]
    student_data = student_db.getByQuery({'identifier': student_identifier})
    class_data = class_db.getByQuery({'identifier': class_identifier})
    if len(student_data) == 0:
        return {
            'status': 'error',
            'message': 'Student not found'
        }
    if len(class_data) == 0:
        return {
            'status': 'error',
            'message': 'Unable to find class'
        }
    if class_data[0]['class_code'] not in student_data[0]['classes']:
        return {
            'status': 'error',
            'message': 'You are not in this class'
        }
    if session['username'] != student_data[0]['username']:
        return {
            'status': 'error',
            'message': 'You do not have permission to view this QR code'
        }
    if f"{data}.png" not in os.listdir('qr'):
        qr_img = qrcode.make(data)
        qr_img.save(f'qr/{data}.png')
    return send_file(f'qr/{data}.png', mimetype='image/png')


@app.route('/api/scan/qr', methods=['POST'])
def scan_qr():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Teacher':
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    required = ['identifier']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    student_identifier = request.form['identifier'].split('-')[0]
    class_identifier = request.form['identifier'].split('-')[1]
    student_data = student_db.getByQuery({'identifier': student_identifier})
    class_data = class_db.getByQuery({'identifier': class_identifier})
    if len(student_data) == 0:
        return {
            'status': 'error',
            'message': 'Student not found'
        }
    if len(class_data) == 0:
        return {
            'status': 'error',
            'message': 'Unable to find class'
        }
    if class_data[0]['class_code'] not in student_data[0]['classes']:
        return {
            'status': 'error',
            'message': 'Student is not in this class'
        }
    attendance_db.add({
        "name": student_data[0]['name'],
        "username": student_data[0]['username'],
        "user_identifier": student_data[0]['identifier'],
        "class_identifier": class_data[0]['identifier'],
        "class_name": class_data[0]['class_name'],
        "class_code": class_data[0]['class_code'],
        "status": "Present",
        "time": datetime.datetime.now().strftime("%H:%M %p"),
        "date": datetime.datetime.now().strftime("%B %d, %Y"),
        "complete_date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })
    return {
        'status': 'success',
        'message': 'Attendance marked successfully',
        'name': student_data[0]['name']
    }
            

# API FOR CLASS HANDLING

@app.route('/api/delete/class', methods=['POST'])
def delete_class():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Teacher':
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    required = ['class_code']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    class_data = class_db.getByQuery({'class_code': request.form['class_code']})
    if len(class_data) == 0:
        return {
            'status': 'error',
            'message': 'Invalid class code'
        }
    if class_data[0]['teacher'] != session['username']:
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    
    for account in student_db.getAll():
        if request.form['class_code'] in account['classes']:
            account['classes'].remove(request.form['class_code'])
            student_db.update({'username': account['username']}, {'classes': account['classes']})
    class_db.deleteById(class_data[0]['id'])
    return {
        'status': 'success',
        'message': 'Class deleted successfully'
    }


@app.route('/api/get/classes')
def get_class():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] not in ['Student', 'Teacher']:
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    if session['account_type'] == 'Teacher':
        classes = class_db.getByQuery({'teacher': session['username']})
    else:
        classes = []
        class_codes = student_db.getByQuery({'username': session['username']})[0]['classes']
        for code in class_codes:

            classes.append(class_db.getByQuery({'class_code': code})[0])
    classes.reverse()
    return classes

@app.route('/api/leave/class', methods=['POST'])
def leave_class():
    if 'username' not in session:
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    if session['account_type'] != 'Student':
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    required = ['class_code']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    class_data = class_db.getByQuery({'class_code': request.form['class_code']})
    if len(class_data) == 0:
        return {
            'status': 'error',
            'message': 'Invalid class code'
        }
    if session['username'] not in class_data[0]['students']:
        return {
            'status': 'error',
            'message': 'You are not in this class'
        }
    class_data[0]['students'].remove(session['username'])
    class_db.update({'class_code': request.form['class_code']}, {'students': class_data[0]['students']})
    student_data = student_db.getByQuery({'username': session['username']})
    student_data[0]['classes'].remove(class_data[0]['class_code'])
    student_db.update({'username': session['username']}, {'classes': student_data[0]['classes']})
    return {
        'status': 'success',
        'message': 'Class left successfully'
    }

@app.route('/api/join/class', methods=['POST'])
def join_class():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Student':
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    required = ['class_code']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    class_data = class_db.getByQuery({'class_code': request.form['class_code']})
    if len(class_data) == 0:
        return {
            'status': 'error',
            'message': 'Invalid class code'
        }
    if session['username'] in class_data[0]['students']:
        return {
            'status': 'error',
            'message': 'You are already in this class'
        }
    class_data[0]['students'].append(session['username'])
    class_db.update({'class_code': request.form['class_code']}, {'students': class_data[0]['students']})
    student_data = student_db.getByQuery({'username': session['username']})
    student_data[0]['classes'].append(class_data[0]['class_code'])
    student_db.update({'username': session['username']}, {'classes': student_data[0]['classes']})
    return {
        'status': 'success',
        'message': 'Class joined successfully'
    }

@app.route('/api/create/class', methods=['POST'])
def create_class():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] != 'Teacher':
        return {
            'status': 'error',
            'message': 'You are not authorized to perform this action'
        }
    required = ['class_name', 'class_code']
    for x in required:
        if x not in request.form:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if len(request.form[x]) < 1:
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
        if request.form[x].isspace():
            return {
                'status': 'error',
                'message': 'Please fill all the fields'
            }
    if len(class_db.getByQuery({'class_code': request.form['class_code']})) > 0:
        return {
            'status': 'error',
            'message': 'Class code already exists'
        }
    class_db.add({
        'class_name':  bleach.clean(request.form['class_name']),
        'class_code':  bleach.clean(request.form['class_code']),
        'teacher':  bleach.clean(session['username']),
        'color': 'default',
        'identifier': random_string(32),
        'students': []
    })
    return {
        'status': 'success',
        'message': 'Class created successfully'
    }

@app.route('/profiles')
def get_profile_image():
    if 'username' not in session:
        return redirect('/')
    if session['account_type'] == 'Teacher':
        account_data = teachers_db.getByQuery({'username': session['username']})
    else:
        account_data = student_db.getByQuery({'username': session['username']})
    for x in os.listdir('profiles'):
        if x.split('.')[0] == account_data[0]['identifier']:
            return send_file(f'profiles/{x}')
    return send_file('profiles/default.png')

app.run(debug=True, host='0.0.0.0', ssl_context="adhoc")