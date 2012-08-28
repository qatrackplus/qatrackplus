/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_list_instance_tables(){
	$(".test-list-instance-table").each(function(idx,table){

		if ($(this).find("tr.empty-table").length>0){
			return;
		}

		var cols = [
			null, //Action
			null, //Unit
			null, //Freq
			null,  // Test list name
			{"sType":"span-timestamp"}, //date completed
			null,//completed by
			null, //qa status
		];

		var	filter_cols = [
				null, //action
				{type: "select"}, //Unit
				{type: "select"}, //Freq
				{type: "text" }, // Test list name
				{type: "text" }, //date completed
				{type: "select" }, //completed by
				null, //qa status
			];


		$(table).dataTable( {
			sDom: "t",
			bStateSave:false, //save filter/sort state between page loads
			bFilter:true,
			bPaginate: false,
			aaSorting:[],
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
	init_test_list_instance_tables();
});

