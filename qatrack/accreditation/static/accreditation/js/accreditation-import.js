// Accreditation Import JavaScript
// Handles file upload and table selection functionality for importing accreditation data

var tables = ["organizations", "documents", "requirements"];
var dataTables = {};

function setSelected(type, selected){
    var all = selected.length > 0 && dataTables[type].column(0).data().length === selected.length;
    $("#"+type + "-summary").html(all ? "All" : selected.length + " Selected");
    var val;
    if (all){
        val = "all";
    } else {
        val = JSON.stringify(selected);
    }
    $("input[name="+type+"]").attr("value", val);
}

function initializeTables() {
    for (var i = 0; i < tables.length; i++) {
        dataTables[tables[i]] = $("#"+ tables[i] + "-table").dataTable({
            buttons: [
                {extend: "selectAll", className: "button"},
                {extend: "selectNone", className: "button"},
                {
                    text: 'Select Filtered',
                    className: "button",
                    action: function () {
                        $(this).DataTable().rows( {search:'applied'} ).select();
                    }
                },
                {extend: "pageLength", className: "button"},
            ],
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
                var tableType = $(dt.table().container()).attr("id").split("-")[0];
                setSelected(tableType, data);
            }
        }).column(0).visible(false);
    }
}

function handleFileUpload() {
    console.log("handleFileUpload called");
    var fileInput = $("#id_accreditation_file")[0];
    var file = fileInput.files[0];
    
    if (!file) {
        alert("Please select an accreditation file to upload.");
        return;
    }
    
    console.log("File selected:", file.name, "Size:", file.size);
    
    // Check file extension
    if (!file.name.toLowerCase().endsWith('.accr')) {
        alert("Please select a valid .accr file.");
        return;
    }
    
    // Check file size (10MB limit)
    var maxSize = 10 * 1024 * 1024; // 10MB in bytes
    if (file.size > maxSize) {
        alert("File size exceeds the 10MB limit. Please select a smaller file.");
        return;
    }
    
    var reader = new FileReader();
    reader.onload = function(e) {
        console.log("File read successfully, content length:", e.target.result.length);
        try {
            var jsonData = JSON.parse(e.target.result);
            console.log("JSON parsed successfully:", jsonData);
            
            // Validate the file structure
            if (!jsonData.objects || !jsonData.meta) {
                throw new Error("Invalid accreditation file format");
            }
            
            // Store the parsed data in the hidden field
            $("#id_accreditation_data").val(JSON.stringify(jsonData));
            console.log("Data stored in hidden field");
            
            // Populate tables with the data
            console.log("Calling populateTablesFromData...");
            populateTablesFromData(jsonData);
            
            // Show success message
            $("#upload-status").html('<div class="alert alert-success">File uploaded successfully! Select the items you want to import below.</div>');
            console.log("Success message displayed");
            
        } catch (error) {
            console.error("Error processing file:", error);
            alert("Error reading file: " + error.message + ". Please ensure you selected a valid accreditation file.");
        }
    };
    
    reader.onerror = function() {
        console.error("FileReader error");
        alert("Error reading file. Please try again.");
    };
    
    console.log("Starting to read file...");
    reader.readAsText(file);
}

function populateTablesFromData(jsonData) {
    console.log("populateTablesFromData called with:", jsonData);
    console.log("Organizations data:", jsonData.objects.organizations);
    console.log("Documents data:", jsonData.objects.documents);
    console.log("Requirements data:", jsonData.objects.requirements);
    
    // Clear existing tables
    for (var i = 0; i < tables.length; i++) {
        if (dataTables[tables[i]]) {
            console.log("Clearing existing DataTable for:", tables[i]);
            dataTables[tables[i]].clear().destroy();
        }
    }
    
    // Populate organizations table
    if (jsonData.objects.organizations) {
        console.log("Processing", jsonData.objects.organizations.length, "organizations");
        var orgsTableBody = $("#organizations-table tbody");
        orgsTableBody.empty();
        
        jsonData.objects.organizations.forEach(function(orgData, index) {
            console.log("Processing organization", index, ":", orgData);
            var org = JSON.parse(orgData).object.fields;
            console.log("Parsed org data:", org);
            var row = "<tr>" +
                "<td>" + index + "</td>" +
                "<td>" + org.name + "</td>" +
                "<td>" + (org.country || '') + "</td>" +
                "</tr>";
            orgsTableBody.append(row);
        });
        
        console.log("Showing organizations table");
        $("#organizations-table").show();
    } else {
        console.log("No organizations data found");
    }
    
    // Populate documents table
    if (jsonData.objects.documents) {
        var docsTableBody = $("#documents-table tbody");
        docsTableBody.empty();
        
        jsonData.objects.documents.forEach(function(docData, index) {
            var doc = JSON.parse(docData).object.fields;
            var row = "<tr>" +
                "<td>" + index + "</td>" +
                "<td>" + doc.name + "</td>" +
                "<td>" + (doc.organization || '') + "</td>" +
                "<td>" + (doc.tag_name || '') + "</td>" +
                "</tr>";
            docsTableBody.append(row);
        });
        
        $("#documents-table").show();
    }
    
    // Populate requirements table
    if (jsonData.objects.requirements) {
        var reqsTableBody = $("#requirements-table tbody");
        reqsTableBody.empty();
        
        jsonData.objects.requirements.forEach(function(reqData, index) {
            var req = JSON.parse(reqData).object.fields;
            var row = "<tr>" +
                "<td>" + index + "</td>" +
                "<td>" + (req.tag_name || '') + "</td>" +
                "<td>" + (req.document || '') + "</td>" +
                "<td>" + (req.tag_name || '') + "</td>" +
                "<td>" + (req.periodicity || '') + "</td>" +
                "</tr>";
            reqsTableBody.append(row);
        });
        
        $("#requirements-table").show();
    }
    
    // Reinitialize DataTables
    initializeTables();
}

$(document).ready(function() {
    // Handle file upload
    $("#id_accreditation_file").on("change", handleFileUpload);
    
    // Initialize summary displays
    for (var i = 0; i < tables.length; i++) {
        $("#" + tables[i] + "-summary").html("0 Selected");
    }
    
    // Form submission handler
    $("form").on("submit", function(e) {
        var accreditationData = $("#id_accreditation_data").val();
        if (!accreditationData) {
            alert("Please upload an accreditation file first.");
            e.preventDefault();
            return false;
        }
        
        var orgsSelected = $("input[name='organizations']").attr("value");
        var docsSelected = $("input[name='documents']").attr("value");
        var reqsSelected = $("input[name='requirements']").attr("value");
        
        if (!orgsSelected && !docsSelected && !reqsSelected) {
            alert("Please select at least one organization, document, or requirement to import.");
            e.preventDefault();
            return false;
        }
        
        // Show loading message
        $("input[type='submit']").val("Processing...").prop("disabled", true);
    });
});