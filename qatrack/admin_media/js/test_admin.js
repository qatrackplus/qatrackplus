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

function toggle_not_required_field(field_class, not_required_for_test_types, test_type){
    if (not_required_for_test_types.indexOf(test_type) >= 0){
        $(field_class).not('.errors').hide();
    }else{
        $(field_class).show();
    }
}

function toggle_required_field(selector, required_for_test_types, test_type){
    if (required_for_test_types.indexOf(test_type) >= 0){
        $(selector).show();
    }else{
        $(selector).not('.errors').hide();
    }
}

function toggle_test_type(){
    var test_type = $("#id_type").find("option:selected").val();

    toggle_required_field(".field-formatting", ["constant", "composite", "simple", "wraparound"], test_type);
    toggle_not_required_field(".field-calculation_procedure", ["constant"], test_type);
    toggle_not_required_field(".field-skip_without_comment", ["constant", "composite", "scomposite"], test_type);
    toggle_required_field(".field-constant_value", ["constant"], test_type);
    toggle_required_field(".field-hidden", ["constant", "composite", "scomposite"], test_type);
    toggle_required_field(".field-display_image", ["upload", "composite", "scomposite"], test_type);
    toggle_required_field(".field-choices", ["multchoice"], test_type);
    toggle_required_field(".field-wrap_low,.field-wrap_high", ["wraparound"], test_type);
    toggle_required_field(".field-flag_when", ["boolean"], test_type);

    var never_visible_in_charts = ["string", "scomposite", "date", "datetime", "upload"];
    if (never_visible_in_charts.indexOf(test_type) > 0){
        $(".field-chart_visibility").find("input[type=checkbox]").prop("checked", false);
    }
    toggle_not_required_field(".field-chart_visibility", never_visible_in_charts, test_type);
}

$(document).ready(function() {
    $("#id_type").change(toggle_test_type);
    toggle_test_type();

    var element = $("#id_calculation_procedure");

    if (element.length > 0){

        var calcProcedure = element.hide();
        calcProcedure.after('<div style="width: 50%; " id="calc-procedure-editor" class="colM aligned vLargeTextField"></div>');

        var calcProcedureEditor = ace.edit("calc-procedure-editor");
        var session = calcProcedureEditor.getSession();

        calcProcedureEditor.setValue(calcProcedure.val());
        session.setMode("ace/mode/python");
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
