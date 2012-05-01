/**************************************************************************/
function init_task_list_table(){
	var review_table = $('#qa-task-list-table').dataTable( {
		"sDom": "<'row-fluid'<'span6'><'span6'>r>t<'row-fluid'<'span3'><'span3' l><'span6'p>>",

		"bStateSave":true, //save filter/sort state between page loads
		"bFilter":true,
		"bPaginate": false,
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
			null,
			null
		]

	} ).columnFilter({

		aoColumns: [
			{type: "select"},
			{type: "select"},
			{type: "text" },
			{type: "text" },
			{type: "text" },
			{ type: "text" },
			null

		]
	});

}
/**************************************************************************/
function init_item_table(table_id){
	return $(table_id).dataTable( {
		"sDom": "<'row-fluid'<'span12't>>",
		"bFilter":false,
		"bPaginate": false,
		"bLengthChange":true,
	} );

}


function create_task_list_table(id){
	var headers = '<tr><th class="name-col">Name</th><th>Status</th><th>Type</th><th>Comment</th><th>Pass/Fail</th><th>Value</th><th class="ref-col">Ref/Tol</th><th class="history-col">History</th><th>Review URL</th></tr>';
	var elements = [
		'<table class="table table-bordered table-condensed sub-table" id="'+id+'">',
		'<thead>',headers,'</thead>',
		'<tbody></tbody>',
		'<tfoot>',headers,'</tfoot>',
		'</table>'
	];

	return elements.join("");
}

function create_spark_line(spark_id,instance,task_list_instances){
	//find historical values for this item
	var vals = [], refs = [], dates=[];
	var tols = {act_high:[],act_low:[],tol_high:[],tol_low:[]};

	$.each(task_list_instances.reverse(),function(i,tl_instance){
		//above is reverse since query was ordered by -work_complete
		$.each(tl_instance.item_instances,function(j,item_instance){
			if (item_instance.task_list_item.id === instance.task_list_item.id){
				dates.push(QAUtils.parse_iso8601_date(item_instance.work_completed))
				vals.push(item_instance.value)

				if (typeof item_instance.reference === "object"){
					refs.push(item_instance.reference.value);
				}else{
					refs.push(null);
				}

				if (typeof item_instance.tolerance === "object" && typeof item_instance.reference === "object"){
					var tol = QAUtils.convert_tol_to_abs(item_instance.reference.value,item_instance.tolerance);
					$.each(QAUtils.TOL_TYPES,function(i,tol_type){
						tols[tol_type].push(tol[tol_type]);
					});
				}else{
					$.each(QAUtils.TOL_TYPES,function(i,tol_type){
						tols[tol_type].push(null);
					});
				}

				return false;
			}
		});

	});


	var is_number = function(n){return !isNaN(parseFloat(n)) && isFinite(n)};

	var chart_min = Math.min(
		Math.min.apply(Math,tols["act_low"].filter(is_number)),
		Math.min.apply(Math,refs.filter(is_number)),
		Math.min.apply(Math,vals.filter(is_number))
	);

	var chart_max = Math.max(
		Math.max.apply(Math,tols["act_high"].filter(is_number)),
		Math.max.apply(Math,refs.filter(is_number)),
		Math.max.apply(Math,vals.filter(is_number))
	);

	var formatter = function(sparkline,options,fields){
		var cur  = sparkline.getCurrentRegionFields();
		var date = [cur.x.getDate(), QAUtils.MONTHS[cur.x.getMonth()], cur.x.getFullYear()];
		return "<div>("+date.join(" ")+","+cur.y+")</div>";

	};

	var spark_opts = {
		width:"100%",
		height:"20px",
		defaultPixelsPerValue:1,
		xvalues:dates,
		chartRangeMin: chart_min,
		chartRangeMax: chart_max,
		fillColor:false,
		spotRadius:0,
		highlightLineColor:null,
		minSpotColor:"",
		maxSpotColor:"",
		tooltipFormatter:function(){return "";}
	}

	spark_opts["lineWidth"] = 1;
	spark_opts["spotColor"] = false;
	spark_opts["lineColor"] = QAUtils.OK_COLOR;
	$('#'+spark_id).sparkline(refs,spark_opts);

	spark_opts['composite']=true;
	spark_opts["lineColor"] = QAUtils.TOL_COLOR;
	$('#'+spark_id).sparkline(tols[QAUtils.TOL_LOW],spark_opts);

	$('#'+spark_id).sparkline(tols[QAUtils.TOL_HIGH],spark_opts);

	spark_opts["lineColor"] = QAUtils.ACT_COLOR;
	$('#'+spark_id).sparkline(tols[QAUtils.ACT_LOW],spark_opts);

	$('#'+spark_id).sparkline(tols[QAUtils.ACT_HIGH],spark_opts);

	spark_opts["spotColor"] = "blue";
	spark_opts["valueSpots"] = true;
	spark_opts["lineColor"] = "blue";
	spark_opts["lineWidth"] = 2;
	spark_opts["spotRadius"] = 3;
	spark_opts["highlightSpotColor"] = "blue";
	spark_opts["highlightLineColor"] = "blue";
	spark_opts["tooltipFormatter"]=formatter;

	$('#'+spark_id).sparkline(vals,spark_opts);


}
function add_item_row(parent,instance,task_list_instances){
	var dt = $(parent).dataTable();
	var item = instance.task_list_item;
	var val = instance.value;
	var tol = "";
	if ((instance.tolerance !== null) && (instance.reference !== null)){
		var t = instance.tolerance;
		var v = instance.reference.value;
		tol = [t.act_low,t.tol_low, v, t.tol_high, t.act_high].join(" < ");
	}else if (instance.reference !== null){
		tol = instance.reference.value;
	}

	var spark_id = 'id-'+instance.id;
	var spark = '<span id="'+spark_id+'" class="sparklines"></span>';

	var comment = "<em>no comment</em>";
	if (instance.comment){
		comment = '<a title="'+instance.comment+'">View Comment</a>';
	}

	dt.fnAddData([
		item.name,
		instance.status,
		item.category.name,
		comment,
		'<span class="pass-fail">'+QAUtils.qa_display(instance.pass_fail)+'</span>',
		val,
		tol,
		spark,
		'<a href="#">Review</a>'
	]);

	create_spark_line(spark_id,instance,task_list_instances);

	var pass_fail_td = $(parent).find("tbody tr:last td span.pass-fail").parent();
	pass_fail_td.css("background-color",QAUtils.qa_color(instance.pass_fail));

}
/**************************************************************************/
function on_select_row(row){

	var dt = $("#qa-task-list-table").dataTable();



	var unit_number = $(row).attr("data-unit_number");
	var task_list_id = $(row).attr("data-task_list_id");
	var frequency = $(row).attr("data-frequency");
	var sub_table_id = 'task-list-'+task_list_id+'-unit-'+unit_number;

	if ($(row).next().children(".qa-details").length > 0){
		$(row).children().css('background-color','');
		dt.fnClose(row);
	}else{
		$(row).children().css('background-color','#C3E6FF');
		dt.fnOpen(row,create_task_list_table(sub_table_id),"qa-details");
		init_item_table('#'+sub_table_id);
		QAUtils.get_resources(
			"tasklistinstance",
			function(resources){
				var task_list_instances = resources.objects;
				if (task_list_instances.length>0){

					//add row using latest task_list_instance
					$.each(task_list_instances[0].item_instances,function(i,item_instance){
						add_item_row($('#'+sub_table_id),item_instance,task_list_instances);
					});
				}
			},
			{
				task_list:task_list_id,
				unit__number:unit_number,
				frequency:frequency,
				order_by:"-work_completed",
				limit:5
			}
		);
	}

}
/**************************************************************************/
$(document).ready(function(){
	init_task_list_table();
	//init_item_table();

	$("#qa-task-list-table tbody tr").click(function(event){
		on_select_row(event.currentTarget);
	});

	//on_select_row($("#qa-task-list-table tbody tr").first());


});
