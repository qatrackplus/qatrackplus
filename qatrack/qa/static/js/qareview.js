

/**************************************************************************/
$(document).ready(function(){
	var review_table = $('#qa-review-table').dataTable( {
		"sDom": "<'row-fluid'<'span6'><'span6'>r>t<'row-fluid'<'span3'i><'span3' l><'span6'p>>",

		"bStateSave":true, //save filter/sort state between page loads
		"bFilter":true,
		"bPaginate": true,
		"bLengthChange":true,
		"iDisplayLength":100,
		"sPaginationType": "bootstrap",
		"oLanguage": {
			"sLengthMenu": "_MENU_ per page",
			"sInfo": "_START_ to _END_ of _TOTAL_"
		},
		aoColumns: [
			null,
			null,
			null,
			{"sType":"day-month-year-sort"},
			{"sType":"day-month-year-sort"},
			null
		]

	} ).columnFilter({

		aoColumns: [
			{type: "select"},
			{type: "select"},
			{type: "text" },
			{type: "text" },
			{type: "text" },
			{ type: "text" }
		]
	});

});