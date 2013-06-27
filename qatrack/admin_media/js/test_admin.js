/*

Only show relevant fields for TestListItemAdmin

*/
function toggle_test_type(){
    var val = $("#id_type").find("option:selected").val();

    if (val == "constant"){
        $(".field-constant_value").show();
        $(".field-calculation_procedure, .field-choices").hide();

    }else if (val == "composite" || val === "upload" || val === "scomposite" ){
        $(".field-calculation_procedure").show();
        $(".field-constant_value, .field-choices").hide();
    }else if (val == "multchoice"){
        $(".field-choices").show();
        $(".field-constant_value, .field-calculation_procedure").hide();

    }else{
        $(".field-calculation_procedure").hide();
        $(".field-constant_value, .field-choices").hide();
    }
}

$(document).ready(function() {
    $("#id_type").change(toggle_test_type);
    toggle_test_type();
});
