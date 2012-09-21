/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_collection_tables(){
	$(".test-collection-table").each(function(idx,table){

		if ($(this).find("tr.empty-table").length>0){
			return;
		}

		var cols = [
			null, //Action
			null,  // Test list name
			{"sType":"span-timestamp"}, //due date
			null, //Unit
			null, //Freq
			null,//assigned to
			{"sType":"span-timestamp"}, //date completed
			null, //pass/fail status
			null // review -status
		];

		var	filter_cols = [
				null, //action
				{type: "text" }, // Test list name
				{type: "text" }, //due date
				{type: "select"}, //Unit
				{type: "select"}, //Freq
				{type: "select"},//assigned to
				{type: "text" }, //date completed
				null, //pass/fail status
				null //review-status
			];


		$(table).dataTable( {
			sDom: "t",
			bStateSave:false, //save filter/sort state between page loads
			bFilter:true,
			bPaginate: false,
			aaSorting:[[3,"asc"],[1,"asc"]],//sort by unit then name
			aoColumns: cols,
			fnAdjustColumnSizing:false

		}).columnFilter({
			sPlaceHolder: "head:after",
			aoColumns: filter_cols
		});

		$(table).find("select, input").addClass("input-small");

	});

}

/**************************************************************************/
$(document).ready(function(){
	init_test_collection_tables();
});

