// Accreditation Export JavaScript
// Handles table selection functionality for exporting accreditation data

var tables = ["organizations", "documents"];
var dataTables = {};

function setSelected(type, selected){
    var all = selected.length > 0 && dataTables[type].column(0).data().length === selected.length;
    $("#"+type + "-summary").html(all ? "All" : selected.length + " Selected");
    var val;
    if (all){
        val = "all";
    } else {
        val = selected.join(",");
    }
    $("input[name="+type+"]").attr("value", val);
}

var columns = [];

for (var i=0; i < tables.length; i++){
    // Different column configurations based on table type
    if (tables[i] === "organizations") {
        columns = [{width: "10%", "targets": 0}, {width: "60%", "targets": 1}, {width: "30%", "targets": 2}];
    } else if (tables[i] === "documents") {
        columns = [{width: "10%", "targets": 0}, {width: "40%", "targets": 1}, {width: "30%", "targets": 2}, {width: "20%", "targets": 3}];
    }

    dataTables[tables[i]] = $("#"+ tables[i] + "-table").dataTable({
        buttons: [
            {extend: "selectAll", className: "button"},
            {extend: "selectNone", className: "button"},
            {
                text: 'Select Filtered',
                className: "button",
                action: function () {
                    this.rows( {search:'applied'} ).select();
                }
            }
        ],
        columnDefs: columns,
        autoWidth: false,
        dom: 'Bfrtip',
        language: {
            buttons: {
                selectAll: "Select all items",
                selectNone: "Select none"
            }
        },
        pagingType: "full_numbers",
        select: "multi",
        initComplete: function(settings, json){
            $(this).parents(".tp-container").find(".loading").remove();
            $(".dt-button").removeClass("dt-button");
        }
    }).show().DataTable().on('select deselect', function ( e, dt, type, indexes ) {
        if (type === 'row') {
            var data = dt.rows({selected: true}).data().pluck(0).toArray();
            var table_type = $(dt.table().container()).attr("id").split("-")[0];
            setSelected(table_type, data);
        }
    }).column(0).visible(false);
}

$(document).ready(function() {
    // Initialize summary displays
    for (var i = 0; i < tables.length; i++) {
        $("#" + tables[i] + "-summary").html("0 Selected");
    }
    // Initialize requirements summary (even though there's no requirements table)
    $("#requirements-summary").html("0 Selected");
    
    // Form submission handler
    $("form").on("submit", function(e) {
        // Validate that at least something is selected
        var orgsSelected = $("input[name='organizations']").attr("value");
        var docsSelected = $("input[name='documents']").attr("value");
        
        if (!orgsSelected && !docsSelected) {
            alert("Please select at least one organization or document to export.");
            e.preventDefault();
            return false;
        }
        
        // Show loading message
        $("input[type='submit']").val("Processing...").prop("disabled", true);
    });
});