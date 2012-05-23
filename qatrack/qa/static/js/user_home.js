/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_list_table(){
	var review_table = $('#qa-test-list-table').dataTable( {
		"sDom": "<'row-fluid'<'span6'><'span6'>r>t<'row-fluid'<'span3'><'span3' l><'span6'p>>",

		"bStateSave":false, //save filter/sort state between page loads
		"bFilter":true,
		"bPaginate": false,
		aoColumns: [
			null, //Unit
			null, //Freq
			null,  // Test list name
			{"sType":"day-month-year-sort"}, //date completed
			{"sType":"day-month-year-sort"}, //due date
			null, //perform link
		]

	} ).columnFilter({

		aoColumns: [
			{type: "select"}, //Unit
			{type: "select"}, //Freq
			{type: "text" }, // Test list name
			{type: "text" }, //date completed
			{type: "text" }, //due date
			null, //perform link
		]
	});

}

/**************************************************************************/
$(document).ready(function(){

	init_test_list_table();

	$("#qa-test-list-table tbody tr.has-due-date").each(function(idx,row){
		var date_string = $(this).data("due");
		var due_date = null;
		if (date_string !== ""){
			due_date = QAUtils.parse_iso8601_date(date_string);
		}
		var freq = $(this).data("frequency");
		QAUtils.set_due_status_color($(this).find(".due-status"),due_date,freq);
	});

});
