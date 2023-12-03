function reload_classes(){
    $.ajax({
        type: "GET",
        url: "/api/get/classes",
        success: function(data){
            console.log(data)
            $("#classes_container").html(`
                <div class="col-lg-auto rounded px-2 py-2 mycard position-relative border border-2 m-2 cursor-pointer" data-bs-toggle="modal" data-bs-target="#createClass">
                    <div class="position-absolute top-50 start-50 translate-middle">
                        <p class="m-0 fw-semibold text-secondary">Create Class</p>
                    </div>
                </div>
            `);
            data.forEach(element => {
                $("#classes_container").prepend(`
                    <a href="/class/${element['identifier']}" class="border col-lg-auto rounded px-2 py-2 mycard position-relative bg-primary m-2 cursor-pointer">
                        <div class="position-absolute bottom-0 start-50 translate-middle-x text-start w-100 bg-light rounded-bottom-2 p-2 border">
                            <p class="m-0 fw-semibold text-muted">${element['class_name']}</p>
                        </div>
                    </a>
                `);
            });
            
        }
    });
}

$("#create_class_submit").on("click", function() {
    var inputs = ["#class_name", "#class_code"];
    // ajax send post 
    $.ajax({
        type: "POST",
        url: "/api/create/class",
        data: {
            class_name: $("#class_name").val(),
            class_code: $("#class_code").val(),
        },
        success: function(data) {
            if(data['status'] == "error"){
                console.log()
                inputs.forEach(element => {
                    if($(element).val() == ""){
                        $(element).addClass("shake");
                        $(element).addClass("border-danger");
                        setTimeout(function(){
                            $(element).removeClass("shake");
                        }, 1000);
                    }
                });
                $("#create_class_message").text(data['message']);
            } else {
                $("#createClass").modal('hide');
                $("#create_class_message").text('');
                inputs.forEach(element => {
                    $(element).val('');
                    $(element).removeClass("border-danger");
                });
                reload_classes();
            }
        }
    });
});


$('#generate_class_code').click(function(){
    $('#class_code').val(generate_string(6));
});

$(document).ready(function() {
    reload_classes()    
});
