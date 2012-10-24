var supress_initial_reload = true;
var column_sort_keys = [
	null,
	"unit_test_collection__unit__name",
	"unit_test_collection__frequency__nominal_interval",
	"test_list__name",
	"work_completed",
	"created_by__username",
	null,
	null
];

/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_list_instance_tables(){
	$(".test-list-instance-table").each(function(idx,table){

		if ($(this).find("tr.empty-table").length>0){
			return;
		}

		//we are using datatables to keep track of the direction of the sort
		//and also provide the sort images but the actual sorting
		//is handled through page refreshes and django on the backend
		var cols = [
			{"sType":"null-sort"},
			{"sType":"null-sort"},
			{"sType":"null-sort"},
			{"sType":"null-sort"},
			{"sType":"null-sort"},
			{"sType":"null-sort"},
			{"sType":"null-sort"},
			{"sType":"null-sort"}
		];

		$(table).dataTable( {
			sDom: "t",
			bStateSave:true, //save filter/sort state between page loads
			bPaginate: false,
			aaSorting:[],//false,//[[1,"desc"],[3,"desc"],[4,"desc"]],
			aoColumns: cols,
			fnAdjustColumnSizing:false,
			fnDrawCallback: on_table_sort

		});

		$(table).find("select, input").addClass("input-small");

	});

}

function on_table_sort(){

	if (supress_initial_reload){
		supress_initial_reload = false;
		return;
	}

	var sorts = this.fnSettings().aaSorting;
	var qs = "?";
	var refresh_required = false;

	_.each(sorts,function(sort_info){

		var col = sort_info[0];
		var dir = sort_info[1];
		var key = column_sort_keys[col];

		var ordering;

		if (!_.isNull(key)){

			refresh_required = true;

			if (dir === "desc"){
				key = "-"+key;
			}

			qs += "order="+key+"&";
		}
	});

	if (refresh_required){
		var url = document.location.href.replace(document.location.search,"")+qs;
		document.location.replace(url);
	}


}
/**************************************************************************/
$(document).ready(function(){
	init_test_list_instance_tables();
});

