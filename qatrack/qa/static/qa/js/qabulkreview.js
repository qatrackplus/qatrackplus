(function(){

"use strict";

/* globals jQuery, window, QAUtils, require, document */

require(['jquery', 'lodash'], function ($, _) {

    var csrf_token = $("input[name=csrfmiddlewaretoken]").val();

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    function sameOrigin(url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });

    $(".test-selected-toggle").eq(0).hide();
    $(".bulk-status").eq(0).parent().html("Bulk Review");
    $(".bulk-status").eq(0).parent().parent().css("color", "black");
    $(".bulk-review-all").eq(0).hide();

    /*
    $("input.test-selected-toggle").on("change", function (e) {
        $(this).closest("table").find("input.test-selected").prop("checked", $(this).is(":checked"));
    });
    */

    $(".bulk-status").on('change', function () {
        var val = $(this).val();
        $(".bulk-status").not($(this)).val(val);
        $("#listable-table-unreviewed tbody tr td select").val(val);
        /*
        if (val !== ""){
            $("input.test-selected:checked").parents("tr").find("select").val(val);
        }
        */
        return false;
    });

    $("#submit-review").click(function(){
        var unitIdx = 1;
        var testListNameIdx = 3;
        var statusIdx = 8;
        var $tableBody = $("#instance-summary tbody");

        var $rows = $("#listable-table-unreviewed tbody tr td select option:selected").filter(function(i, v){
            return $(v).val() !== "";
        }).parents("tr");

        var counter = {};
        $rows.each(function(idx, el){
            var $el = $(el);
            var children = $el.children();
            var unit = children[unitIdx].innerText;
            var tl = children[testListNameIdx].innerText;
            var statusVal = $(children[statusIdx]).find("option:selected ").val();
            var statusText = $(children[statusIdx]).find("option:selected ").text();
            var key = [tl, unit, statusText].join("||");

            if (statusVal !== ""){
                if (key in counter){
                    counter[key] += 1;
                } else {
                    counter[key] = 1;
                }
            }
        });

        var $tbody = $("#instance-summary tbody");
        $tbody.html("");
        var sorted = _(_.keys(counter)).sortBy(function(k){return counter[k];}).reverse();
        sorted.each(function(k){
            var count = counter[k];
            if (count <= 0){
                return;
            }
            var split = k.split("||");
            var row = "<tr><td>" + split[0] + "</td><td>" + split[1] + "</td><td>" + count + "</td><td>" + split[2] + "</td></tr>";
            $tbody.append(row);
        });
    });


    $("#confirm-update").click(function(e){

        var toUpdate = $("#listable-table-unreviewed tbody tr td select option:selected").filter(function(i, v){
            return $(v).val() !== "";
        }).toArray().map(function(k,v){
            return [$(k).val(), $(k).parent("select").data("tli")];
        });
        var data = {tlis: toUpdate};

        $.ajax({
            type:"POST",
            url: '{% url "qa-bulk-review" %}',
            data: data,
            dataType:"json",
            success: function (result) {
                if (result.ok){
                    location.reload();
                }else{
                    $("#bulk-review-msg").html('<span style="color: red"><em>Sorry reviewing the test list instances failed.</em></span>');
                }
            },
            traditional:true,
            error: function(e, data){
                $("#bulk-review-msg").html('<span style="color: red"><em>Sorry reviewing the test list instances failed.</em></span>');
            }
        });

        e.preventDefault();

    });
});

})(); /* use strict IIFE */
