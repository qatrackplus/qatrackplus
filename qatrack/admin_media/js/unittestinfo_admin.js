"use strict";

var content_type = $("select[name='content_type']");
var source_unit = $("select[name='source_unit']");
var dest_unit = $("select[name='dest_unit']");
var testlist = $("select[name='testlist']");


function getTestLists() {

    dest_unit.find("option").remove();
    testlist.find("option").remove();

    if (content_type.val() && source_unit.val()) {

        var testListUrl= ADMINURLs.GETTESTLIST.replace(
            ":source_unit:", source_unit.val()
        ).replace(
            ":content_type:", content_type.val()
        );

        $.getJSON(testListUrl,
            function(data) {
                testlist.find("option").remove();
                testlist.append("<option value selected='selected'>---------</option>");
                $.each(data, function(idx, option) {
                    testlist.append($('<option value="'+option[0]+'"/>').text(option[1]));
                });
        });
    }
}

function getDestUnit() {

    if (content_type.val() && source_unit.val() && testlist.val()) {

        var getDestUnitUrl = ADMINURLs.GETDESTUNIT.replace(
            ":source_unit:", source_unit.val()
        ).replace(
            ":content_type:", content_type.val()
        ).replace(
            ":testlist:", testlist.val()
        );

        $.getJSON(getDestUnitUrl,
            function(data) {
                dest_unit.find("option").remove();
                $.each(data, function(idx, option) {
                    dest_unit.append($('<option value="'+option[0]+'"/>').text(option[1]));
                });
        });
    }
}

$(document).ready(function() {

    // prevent clearning users selection if they hit back button or
    // form is invalid when submitted
    if (!dest_unit.val()){
        dest_unit.find("option").remove();
    }
    if (!testlist.val()){
        testlist.find("option").remove();
    }

    source_unit.change(getTestLists);
    content_type.change(getTestLists);
    testlist.change(getDestUnit);

});
