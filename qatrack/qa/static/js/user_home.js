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

/************************************************************************/
//update row color based on its review status
function update_row_color(row){
	var review_td = row.find("td.review_status");
	var reviewed = review_td.hasClass(QAUtils.APPROVED);
	review_td.removeClass("alert-info").removeClass("alert-success");
	if (reviewed){
		review_td.find("span").addClass("alert-success");
	}else{
		review_td.find("span").addClass("alert-info");
	}
}
/**************************************************************************/
$(document).ready(function(){

	init_test_list_table();

	$("#qa-test-list-table tbody tr").each(function(idx,row){
		update_row_color($(row));
	});

});
