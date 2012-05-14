/*

Only show relevant fields for TestListItemAdmin

*/
function toggle_test_type(){
    var val = $("#id_test_type").find("option:selected").val();

    if (val == "constant"){
        $(".field-constant_value").show();
        $(".field-calculation_procedure").hide();
    }else if (val == "composite"){
        $(".field-calculation_procedure").show();
        $(".field-constant_value").hide();
    }else{
        $(".field-calculation_procedure").hide();
        $(".field-constant_value").hide();
    }
}

$(document).ready(function() {
    $("#id_test_type").change(toggle_test_type);
    toggle_test_type();
});