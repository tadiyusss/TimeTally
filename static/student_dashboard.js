function reload_classes(){
    $.ajax({
        type: "GET",
        url: "/api/get/classes",
        success: function(data){
            console.log(data)
            $("#classes_container").html(`
                <div class="col-lg-auto rounded px-2 py-2 mycard position-relative border border-2 m-2 cursor-pointer" data-bs-toggle="modal" data-bs-target="#joinClass">
                    <div class="position-absolute top-50 start-50 translate-middle">
                        <p class="m-0 fw-semibold text-secondary">Join Class</p>
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




$('#join_class_submit').on('click', function() {
    $.ajax({
        type: "POST",
        url: "/api/join/class",
        data: {
            class_code: $("#class_code").val()
        },
        success: function(data){
            if(data['status'] == "error"){
                $("#join_class_message").text(data['message']);
                $("#class_code").addClass("shake");
                $("#class_code").addClass("border-danger");
                setTimeout(function(){
                    $("#class_code").removeClass("shake");
                }, 1000);
                reload_classes();
            } else {
                $("#joinClass").modal('hide');
                $("#join_class_message").text('');
                $("#class_code").val('');
                $("#class_code").removeClass("border-danger");
                reload_classes();
            }
        }
    })
});

$(document).ready(function(){
    reload_classes()
})