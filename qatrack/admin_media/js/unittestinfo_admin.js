"use strict";

$(document).ready(function() {

    $("select[name='dest_unit'] > option").remove();
    $("select[name='testlist'] > option").remove();

    var content_type, source_unit, testlist;

    var getTestLists = function() {

        $("select[name='dest_unit'] > option").remove();
        $("select[name='testlist'] > option").remove();

        if (content_type && source_unit) {

            var testListUrl= ADMINURLs.GETTESTLIST.replace(
                ":source_unit:", source_unit
            ).replace(
                ":content_type:", content_type
            );

            $.getJSON(testListUrl,
                function(data) {
                    var dropdown = $("select[name='testlist']");
                    $("select[name='testlist'] > option").remove();
                    dropdown.append("<option value selected='selected'>---------</option>");
                    $.each(data, function(idx, option) {
                        dropdown.append($('<option value="'+option[0]+'"/>').text(option[1]));
                    });
            });
        }
    };

    var getDestUnit = function() {

        if (content_type && source_unit) {

            var getDestUnitUrl = ADMINURLs.GETDESTUNIT.replace(
                ":source_unit:", source_unit
            ).replace(
                ":content_type:", content_type
            ).replace(
                ":testlist:", testlist
            );

            $.getJSON(getDestUnitUrl,
                function(data) {
                    var dropdown = $("select[name='dest_unit']");
                    $("select[name='dest_unit'] > option").remove();
                    $.each(data, function(idx, option) {
                        dropdown.append($('<option value="'+option[0]+'"/>').text(option[1]));
                    });
            });
        }
    };

    $("select[name='source_unit']").change(function() {
        $( "select[name='source_unit'] option:selected" ).each(function() {
            source_unit = $( this ).val();
            getTestLists();
        });

    });

    $("select[name='content_type']").change(function() {
        $( "select[name='content_type'] option:selected" ).each(function() {
            content_type = $( this ).val();
            getTestLists();
        });
    });

    $("select[name='testlist']").change(function() {
        $( "select[name='testlist'] option:selected" ).each(function() {
            testlist = $( this ).val();
            getDestUnit();
        });
    });

});
