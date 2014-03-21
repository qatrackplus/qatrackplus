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
    var calcProcedure = $("#id_calculation_procedure").hide();
    calcProcedure.after('<div style="height:200px; " id="calc-procedure-editor" class="colM aligned vLargeTextField"></div>');

    var editor = ace.edit("calc-procedure-editor");
    var session = editor.getSession();

    editor.setValue(calcProcedure.val());
    session.setMode( "ace/mode/python");
    session.setTabSize(4)
    session.setUseSoftTabs(true)
    editor.on('blur', function(){
        calcProcedure.val(editor.getValue());
    });
    editor.resize();
});
