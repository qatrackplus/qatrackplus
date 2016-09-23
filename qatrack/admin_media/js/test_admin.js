/*

Only show relevant fields for TestListItemAdmin

*/
function toggle_test_type(){
    var val = $("#id_type").find("option:selected").val();

    if (val == "constant"){
        $(".field-constant_value, .field-hidden").show();
        $(".field-calculation_procedure, .field-choices, .field-display_image, .field-skip_without_comment").not(".errors").hide();

    }else if (val == "composite" || val === "scomposite" ){
        $(".field-calculation_procedure, .field-hidden").show();
        $(".field-constant_value, .field-choices, .field-skip_without_comment").not(".errors").hide();

    }else if (val === "upload"){
        $(".field-calculation_procedure, .field-display_image, .field-skip_without_comment").show();
        $(".field-constant_value, .field-choices, .field-hidden").not(".errors").hide();

    }else if (val == "multchoice"){
        $(".field-choices, .field-skip_without_comment").show();
        $(".field-constant_value, .field-calculation_procedure, .field-display_image, .field-hidden").not(".errors").hide();

    }else{
        $(".field-skip_without_comment").show();
        $(".field-calculation_procedure").not(".errors").hide();
        $(".field-constant_value, .field-choices, .field-display_image, .field-hidden").not(".errors").hide();
    }
}

$(document).ready(function() {
    $("#id_type").change(toggle_test_type);
    toggle_test_type();

    var isNotIE78 = jQuery.support.leadingWhitespace;
    var element = $("#id_calculation_procedure");

    if (isNotIE78 && element.length > 0){
        // IE7-8 explode with Ace editor sigh

        var calcProcedure = element.hide();
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
