(function () {

    "use strict";

    /* globals jQuery, window, QAUtils, require, document */

    require(['jquery', 'lodash'], function ($, _) {

        $(".test-selected-toggle").eq(0).hide();
        $(".bulk-status").eq(0).parent().html("Bulk Review");
        $(".bulk-status").eq(0).parent().parent().css("color", "black");
        $(".bulk-review-all").eq(0).hide();

        $("input.test-selected-toggle").on("change", function (e) {
            $("input.test-selected-toggle").not($(this)).prop("checked", $(this).is(":checked"));
            $(this).closest("table").find("input.test-selected").prop("checked", $(this).is(":checked"));
        });

        $(".bulk-status").on('change', function () {
            var val = $(this).val();
            $(".bulk-status").not($(this)).val(val);

            if (val !== "") {
                $("input.test-selected:checked").parents("tr").find("select").val(val);
            }

            return false;
        });

        var headers = _.map($("#listable-table-unreviewed").find("thead tr:first th"), function (el) {
            return el.innerText.toLowerCase();
        });
        var siteIdx = headers.indexOf("site");
        var unitIdx = headers.indexOf("unit");
        var testListNameIdx = headers.indexOf("test list name");
        var statusIdx = headers.indexOf("bulk review");

        $("#submit-review").click(function () {

            if (unitIdx === -1 || testListNameIdx === -1 || statusIdx === -1) {
                console.error("Missing required table columns (unit, test list name, or bulk review) for aggregation.");
                alert("Cannot aggregate reviews: missing required table columns.");
                return;
            }

            var $tableBody = $("#instance-summary tbody");

            var $rows = $("#listable-table-unreviewed tbody tr").filter(function () {
                var isChecked = $(this).find("input.test-selected").is(":checked");
                var hasStatus = $(this).find("td select").val() !== "";
                return isChecked && hasStatus;
            });

            var counter = {};
            var abort = false;
            $rows.each(function (idx, el) {
                var $el = $(el);
                var children = $el.children();

                if (!children[unitIdx] || !children[testListNameIdx] || !children[statusIdx]) {
                    console.error("Row is missing required columns.");
                    abort = true;
                    return false;
                }

                var site = (siteIdx >= 0 && children[siteIdx]) ? (children[siteIdx].innerText || "Other") + ": " : "";
                var unit = site + children[unitIdx].innerText;
                var tl = children[testListNameIdx].innerText;
                var statusVal = $(children[statusIdx]).find("option:selected ").val();
                var statusText = $(children[statusIdx]).find("option:selected ").text();
                var key = [tl, unit, statusText].join("||");

                if (statusVal !== "") {
                    if (key in counter) {
                        counter[key] += 1;
                    } else {
                        counter[key] = 1;
                    }
                }
            });

            if (abort) {
                alert("Failed to build summary: a row is missing required data.");
                return;
            }

            var $tbody = $("#instance-summary tbody");
            $tbody.html("");
            var sorted = _(_.keys(counter)).sortBy(function (k) { return counter[k]; }).reverse();
            sorted.each(function (k) {
                var count = counter[k];
                if (count <= 0) {
                    return;
                }
                var split = k.split("||");
                var row = "<tr><td>" + split[0] + "</td><td>" + split[1] + "</td><td>" + count + "</td><td>" + split[2] + "</td></tr>";
                $tbody.append(row);
            });
        });


        $("#confirm-update").click(function (e) {

            var toUpdate = $("#listable-table-unreviewed tbody tr").filter(function () {
                var isChecked = $(this).find("input.test-selected").is(":checked");
                var hasStatus = $(this).find("td select").val() !== "";
                return isChecked && hasStatus;
            }).toArray().map(function (tr) {
                var $select = $(tr).find("td select");
                return [$select.val(), $select.data("tli")];
            });
            var data = { tlis: toUpdate };

            $.ajax({
                type: "POST",
                url: QAURLs.TLI_BULK_REVIEW,
                data: data,
                dataType: "json",
                success: function (result) {
                    if (result.ok) {
                        location.reload();
                    } else {
                        $("#bulk-review-msg").html('<span style="color: red"><em>Sorry reviewing the test list instances failed.</em></span>');
                    }
                },
                traditional: true,
                error: function (e, data) {
                    $("#bulk-review-msg").html('<span style="color: red"><em>Sorry reviewing the test list instances failed.</em></span>');
                }
            });

            e.preventDefault();

        });
    });

})(); /* use strict IIFE */
