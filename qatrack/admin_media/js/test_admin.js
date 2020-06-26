/*

Only show relevant fields for TestListItemAdmin

*/

function toggle_formatting(test_type){
    var $el = $(".field-formatting");
    if (["constant", "composite", "simple", "wraparound"].indexOf(test_type) >= 0){
        $el.show();
    }else{
        $el.hide();
    }
}

function toggle_test_type(){
    var val = $("#id_type").find("option:selected").val();

    toggle_formatting(val);

    // this is ugly and error prone. Should be refactored
    if (val == "constant"){
        $(".field-constant_value, .field-hidden").show();
        $(".field-calculation_procedure,.field-wrap_low,.field-wrap_high,.field-choices, .field-display_image, .field-skip_without_comment, .field-require_comment").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", true).show();
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
    }else if (val == "wraparound"){
        $(".field-wrap_low, .field-wrap_high").show();
        $(".field-constant_value, .field-choices, .field-display_image, .field-skip_without_comment, .field-require_comment, .field-hidden").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", true).show();
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
    }else if (val == "composite" || val === "scomposite" ){
        $(".field-calculation_procedure, .field-hidden, .field-display_image").show();
        $(".field-constant_value, .field-wrap_high, .field-wrap_low, .field-choices, .field-skip_without_comment, .field-require_comment").not(".errors").hide();
        if (val === "scomposite"){
            $(".field-chart_visibility").prop("checked", false).hide();
        }else{
            $(".field-chart_visibility").prop("checked", true).show();
        }
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
    }else if (val == "string" || val == "date" || val == "datetime"){
        $(".field-skip_without_comment, .field-require_comment").show();
        $(".field-constant_value, .field-hidden").hide();
        $(".field-choices, .field-display_image").not(".errors").hide();
        $(".field-constant_value, .field-wrap_high, .field-wrap_low, .field-choices, .field-display_image, .field-hidden").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", false).hide();
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
    }else if (val === "upload"){
        $(".field-calculation_procedure, .field-display_image, .field-skip_without_comment").show();
        $(".field-constant_value, .field-wrap_high, .field-wrap_low, .field-choices, .field-hidden").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", false).hide();
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
    }else if (val == "multchoice"){
        $(".field-choices, .field-skip_without_comment, .field-require_comment").show();
        $(".field-constant_value, .field-wrap_high, .field-wrap_low, .field-display_image, .field-hidden").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", false).hide();
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
    }else if (val == "boolean"){
        $(".field-flag_when").show();
        $(".field-skip_without_comment, .field-require_comment").show();
        //$(".field-calculation_procedure").not(".errors").hide();
        $(".field-constant_value, .field-wrap_high, .field-wrap_low, .field-choices, .field-display_image, .field-hidden").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", true).show();
    }else{
        $(".field-skip_without_comment, .field-require_comment").show();
        //$(".field-calculation_procedure").not(".errors").hide();
        $(".field-constant_value, .field-wrap_high, .field-wrap_low, .field-choices, .field-display_image, .field-hidden").not(".errors").hide();
        $(".field-chart_visibility").prop("checked", true).show();
        $("#id_flag_when").val("").parents(".field-flag_when").hide();
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
        calcProcedure.after('<div style="width: 50%; " id="calc-procedure-editor" class="colM aligned vLargeTextField"></div>');

        var calcProcedureEditor = ace.edit("calc-procedure-editor");
        var session = calcProcedureEditor.getSession();

        calcProcedureEditor.setValue(calcProcedure.val());
        session.setMode( "ace/mode/python");
        session.setTabSize(4);
        session.setUseSoftTabs(true);
        calcProcedureEditor.on('blur', function(){
            calcProcedure.val(calcProcedureEditor.getValue());
        });
        calcProcedureEditor.setAutoScrollEditorIntoView(true);
        calcProcedureEditor.setOption("maxLines", 20);
        calcProcedureEditor.setOption("minLines", 5);
        calcProcedureEditor.setShowPrintMargin(false);
        calcProcedureEditor.resize();
    }


    var formatters = [
        ['', 'Default'],
        ['%.0f', 'Fixed - 0 decimals (%.0f)'],
        ['%.1f', 'Fixed - 1 decimals (%.1f)'],
        ['%.2f', 'Fixed - 2 decimals (%.2f)'],
        ['%.3f', 'Fixed - 3 decimals (%.3f)'],
        ['%.4f', 'Fixed - 4 decimals (%.4f)'],
        ['%.5f', 'Fixed - 5 decimals (%.5f)'],
        ['%.6f', 'Fixed - 6 decimals (%.6f)'],
        ['%.0E', 'Scientific - 1 sig figs (%.0E) '],
        ['%.1E', 'Scientific - 2 sig figs (%.1E) '],
        ['%.2E', 'Scientific - 3 sig figs (%.2E) '],
        ['%.3E', 'Scientific - 4 sig figs (%.3E) '],
        ['%.4E', 'Scientific - 5 sig figs (%.4E) '],
        ['%.5E', 'Scientific - 6 sig figs (%.5E) '],
        ['%.0G', 'General - up to 1 sig figs (%.0G)'],
        ['%.1G', 'General - up to 2 sig figs (%.1G)'],
        ['%.2G', 'General - up to 3 sig figs (%.2G)'],
        ['%.3G', 'General - up to 4 sig figs (%.3G)'],
        ['%.4G', 'General - up to 5 sig figs (%.4G)'],
        ['%.5G', 'General - up to 6 sig figs (%.5G)'],
    ];

    var sel = $('<select id="formatters">').insertAfter('#id_formatting');
    $(formatters).each(function(idx, item) {
        sel.append($("<option>").prop('value', item[0]).text(item[1]));
    });
    sel.change(function(el){
        $("#id_formatting").val(el.target.value);
    });

    $("#id_category, #id_type, #id_autoreviewruleset").select2();


});
