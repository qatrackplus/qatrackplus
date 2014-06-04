"use strict";

var content_type = $("select[name='content_type']");
var source_unit = $("select[name='source_unit']");
var dest_unit = $("select[name='dest_unit']");
var source_testlist = $("select[name='source_testlist']");

function getTestLists() {
    source_testlist.find("option").remove();

    if (content_type.val() && source_unit.val()) {

        var testListUrl= ADMINURLs.GETTESTLIST.replace(
            ":source_unit:", source_unit.val()
        ).replace(
            ":content_type:", content_type.val()
        );

        $.getJSON(testListUrl,
            function(data) {
                source_testlist.find("option").remove();
                source_testlist.append("<option value selected='selected'>---------</option>");
                $.each(data, function(idx, option) {
                    source_testlist.append($('<option value="'+option[0]+'"/>').text(option[1]));
                });
        });

    }
}

$(document).ready(function() {
    // prevent clearning users selection if they hit back button or
    // form is invalid when submitted
    if (!source_testlist.val()){
        source_testlist.find("option").remove();
    }

    source_unit.change(getTestLists);
    content_type.change(getTestLists);
});
