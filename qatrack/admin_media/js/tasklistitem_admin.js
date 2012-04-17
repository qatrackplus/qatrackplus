/*

Only show relevant fields for TaskListItemAdmin

*/

$(document).ready(function() {
    $("#id_task_type").change(function(){
        var val = $(this).find("option:selected").val();

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
    });
});