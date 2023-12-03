function delete_class(class_code){
    $.ajax({
        url: "/api/delete/class",
        type: "POST",
        data: {
            class_code: class_code
        },
        success: function(data){
            if(data['status'] == 'success'){
                window.location.href = "/";
            }
        }
    })
}