function generate_string(len){
    var result = '';
    var characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    var charactersLength = characters.length;
    for ( var i = 0; i < len; i++ ) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}
function shakeElement(element) {
    $(element).addClass("shake").on("animationend", function() {
      $(element).removeClass("shake");
    });
}

  