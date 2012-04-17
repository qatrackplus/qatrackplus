/*

Only show relevant fields for TaskListItemAdmin

*/
function toggle_task_type(){
    var val = $("#id_task_type").find("option:selected").val();

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
    $("#id_task_type").change(toggle_task_type);
    toggle_task_type();
});