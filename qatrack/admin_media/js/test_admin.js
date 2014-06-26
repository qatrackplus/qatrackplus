/*

Only show relevant fields for TestListItemAdmin

*/
function toggle_test_type(){
    var val = $("#id_type").find("option:selected").val();

    if (val == "constant"){
        $(".field-constant_value").show();
        $(".field-calculation_procedure, .field-choices, .field-display_image").hide();

    }else if (val == "composite" || val === "scomposite" ){
        $(".field-calculation_procedure").show();
        $(".field-constant_value, .field-choices").hide();

    }else if (val === "upload"){
        $(".field-calculation_procedure, .field-display_image").show();
        $(".field-constant_value, .field-choices").hide();

    }else if (val == "multchoice"){
        $(".field-choices").show();
        $(".field-constant_value, .field-calculation_procedure, .field-display_image").hide();

    }else{
        $(".field-calculation_procedure").hide();
        $(".field-constant_value, .field-choices, .field-display_image").hide();
    }
}

$(document).ready(function() {
    $("#id_type").change(toggle_test_type);
    toggle_test_type();

    var isNotIE78 = jQuery.support.leadingWhitespace;
    if (isNotIE78){
        // IE7-8 explode with Ace editor sigh

        var calcProcedure = $("#id_calculation_procedure").hide();
        calcProcedure.after('<div style="height:200px; " id="calc-procedure-editor" class="colM aligned vLargeTextField"></div>');

        var calcProcedureEditor = ace.edit("calc-procedure-editor");
        var session = calcProcedureEditor.getSession();

        calcProcedureEditor.setValue(calcProcedure.val());
        session.setMode( "ace/mode/python");
        session.setTabSize(4)
        session.setUseSoftTabs(true)
        calcProcedureEditor.on('blur', function(){
            calcProcedure.val(calcProcedureEditor.getValue());
        });
        calcProcedureEditor.resize();
    }

});
