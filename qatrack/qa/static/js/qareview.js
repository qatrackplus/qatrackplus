var HISTORY_INSTANCE_LIMIT = 5;

/**************************************************************************/
//Initialize sortable/filterable task list table data types
function init_task_list_table(){
	var review_table = $('#qa-task-list-table').dataTable( {
		"sDom": "<'row-fluid'<'span6'><'span6'>r>t<'row-fluid'<'span3'><'span3' l><'span6'p>>",

		"bStateSave":false, //save filter/sort state between page loads
		"bFilter":true,
		"bPaginate": false,
		aoColumns: [
			null, //Unit
			null, //Freq
			null,  // Task list name
			{"sType":"day-month-year-sort"}, //date completed
			{"sType":"day-month-year-sort"}, //due date
			null, //status of task list items
			null  //review status of list
		]

	} ).columnFilter({

		aoColumns: [
			{type: "select"}, //Unit
			{type: "select"}, //Freq
			{type: "text" }, // Task list name
			{type: "text" }, //date completed
			{type: "text" }, //due date
			{ type: "text" }, //status of task list items
			null //review status of list
		]
	});

}
/**************************************************************************/
//creates the html table to hold the task list items from a task list
function create_task_list_table(id){
	var headers = '<tr><th class="name-col">Name</th><th>Type</th><th>Comment</th><th>Pass/Fail</th><th>Value</th><th class="ref-col">Ref/Tol</th><th class="history-col">History</th><th>Review URL</th></tr>';
	var elements = [
		'<div class="review-button-container ">',
		'<button data-toggle="button" data-loading-text="Updating..." class="pull-right btn toggle-review-status">Toggle Review Status</button>',
		'</div>',
		'<table class="table table-bordered table-condensed sub-table" id="'+id+'">',
		'<thead>',headers,'</thead>',
		'<tbody></tbody>',
		'<tfoot>',headers,'</tfoot>',
		'</table>'
	];

	return elements.join("");
}
/**************************************************************************/
//generate a spark line in the provided container for a given task list item
function create_spark_line(container,task_list_item,task_list_instances){
	//find historical values for this item
	var vals = [], refs = [], dates=[];
	var tols = {act_high:[],act_low:[],tol_high:[],tol_low:[]};

	$.each(task_list_instances.reverse(),function(i,tl_instance){
		//above is reverse since query was ordered by -work_complete
		$.each(tl_instance.item_instances,function(j,item_instance){
			if (item_instance.task_list_item.id === task_list_item.id){
				dates.push(QAUtils.parse_iso8601_date(item_instance.work_completed))
				vals.push(item_instance.value)

				if (item_instance.reference !== null){
					refs.push(item_instance.reference.value);
				}else{
					refs.push(null);
				}

				if ((item_instance.tolerance !== null) && (item_instance.reference !== null)){
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

	var chart_min = Math.min(
		Math.min.apply(Math,tols["act_low"].filter(QAUtils.is_number)),
		Math.min.apply(Math,refs.filter(QAUtils.is_number)),
		Math.min.apply(Math,vals.filter(QAUtils.is_number))
	);

	var chart_max = Math.max(
		Math.max.apply(Math,tols["act_high"].filter(QAUtils.is_number)),
		Math.max.apply(Math,refs.filter(QAUtils.is_number)),
		Math.max.apply(Math,vals.filter(QAUtils.is_number))
	);

	var formatter = function(sparkline,options,fields){
		var cur  = sparkline.getCurrentRegionFields();
		var idx = dates.indexOf(cur.x);
		var tooltip = "<div><strong>"+QAUtils.format_date(cur.x)+" = "+cur.y+"</strong>";
		if (idx >= 0){

			tooltip += "<br/>(A Lo, T Lo,  Ref, T Hi, A Hi) = ";
			tooltip += [
				 tols.act_low[idx],tols.tol_low[idx],
				 refs[idx],
				 tols.tol_high[idx],tols.act_high[idx]
			].join(", ");
			tooltip += "</div>";

		}else{
			tooltip = "<div>("+QAUtils.format_date(cur.x)+","+cur.y+")</div>";
		}
		return tooltip;

	};

	var spark_opts = {
		width:container.parent().width(),
		height:container.parent().height(),
		defaultPixelsPerValue:1,
		xvalues:dates,
		chartRangeMin: chart_min,
		chartRangeMax: chart_max,
		fillColor:false,
		spotRadius:0,
		highlightLineColor:null,
		minSpotColor:"",
		maxSpotColor:"",
		spotColor:false,
		tooltipFormatter:function(){return "";}
	}


	spark_opts["lineColor"] = QAUtils.ACT_COLOR;
	container.sparkline(tols[QAUtils.ACT_LOW],spark_opts);
	spark_opts['composite']=true;
	container.sparkline(tols[QAUtils.ACT_HIGH],spark_opts);

	spark_opts["spotColor"] = "blue";
	spark_opts["valueSpots"] = true;
	spark_opts["lineColor"] = "blue";
	spark_opts["lineWidth"] = 2;
	spark_opts["spotRadius"] = 3;
	spark_opts["highlightSpotColor"] = "blue";
	spark_opts["highlightLineColor"] = "blue";
	spark_opts["tooltipFormatter"]=formatter;

	if (vals.length < 2){
		container.html("<em>Not enough data</em>");
	}else{
		container.sparkline(vals,spark_opts);
	}
}

/************************************************************************/
//add a row to a details table for the input item instance
function add_item_row(parent,instance,task_list_instances){

	var item = instance.task_list_item;

	var data = [];
	data.push("<strong>"+item.name+"</strong>");
	data.push(item.category.name);

	var comment = instance.comment ? '<a title="'+instance.comment+'">Hover for Comment</a>' : "<em>no comment</em>";;
	data.push(comment)

	var pass_fail;
	if (QAUtils.instance_has_ref_tol(instance)){
		pass_fail = '<span class="pass-fail">'+QAUtils.qa_display(instance.pass_fail)+'</span>';
	}else{
		pass_fail = '<span class="pass-fail">No Reference</span>';
	}
	data.push(pass_fail)

	var val = QAUtils.format_instance_value(instance);
	data.push(val)

	var ref_tol = QAUtils.format_ref_tol(instance.reference, instance.tolerance);
	data.push(ref_tol)

	var spark_id = 'id-'+instance.id;
	var spark = '<span id="'+spark_id+'" class="sparklines"></span>';
	data.push(spark);

	var review_link = QAUtils.unit_item_chart_link(instance.unit,item,"Details");
	data.push(review_link);

	$(parent).dataTable().fnAddData(data);
	var item_row = $(parent).find("tbody tr:first");

	create_spark_line($("#"+spark_id),instance.task_list_item,task_list_instances);

	//set color Pass/Fail column based on test
	var pass_fail_td = item_row.find("span.pass-fail").parent();
	pass_fail_td.css("background-color",QAUtils.qa_color(instance.pass_fail));
	pass_fail_td.addClass("label");
	return item_row;
}

/************************************************************************/
//remove instance details row below input task_list_row for a given data_table
function close_details(task_list_row,data_table){
	data_table.fnClose(task_list_row[0]);
}
/************************************************************************/
//open task list instance details row below input task_list_row for a given data_table
function open_details(task_list_row,data_table){

	var unit_number = task_list_row.attr("data-unit_number");
	var task_list_id = task_list_row.attr("data-task_list_id");
	var frequency = task_list_row.attr("data-frequency");
	var sub_table_id = 'task-list-'+task_list_id+'-unit-'+unit_number;

	data_table.fnOpen(task_list_row.get(0),create_task_list_table(sub_table_id),"qa-details");

	$("#"+sub_table_id).dataTable( {
		"sDom": "<'row-fluid'<'span12't>>",
		"bFilter":false,
		"bPaginate": false,
		"bLengthChange":true,
	} );

	var details = task_list_row.next().children(".qa-details");
	details.find("table").css("background-color","whiteSmoke");
	return details;
}

/************************************************************************/
//update row color based on its review status
function update_row_color(row){
	var review_td = row.find("td.review_status");
	var reviewed = review_td.hasClass(QAUtils.APPROVED);
	review_td.removeClass("alert-info").removeClass("alert-success");
	if (reviewed){
		review_td.addClass("alert-success");
	}else{
		review_td.addClass("alert-info");
	}
}
/************************************************************************/
//update review status displayed for a given row
function set_task_list_review_status(row,user,date){

	var status = "Unreviewed";
	var review_button = row.next("tr").find(".btn").button();
	var review_cell = 	row.find("td.review_status");
	var cls = QAUtils.UNREVIEWED;

	if (user && date){
		date = QAUtils.parse_iso8601_date(date);
		status = "Reviewed by "+ user;
		status+= " on " + QAUtils.format_date(date,true);
		cls = QAUtils.APPROVED;
	}

	review_cell.html(status).removeClass(QAUtils.UNREVIEWED).removeClass(QAUtils.APPROVED);
	review_cell.addClass(cls);
	update_row_color(row);
}

/************************************************************************/
//display all the task list items from the the task list instance
function display_task_list_details(container,task_list_instances){

	var latest = task_list_instances[0];
	var details_table = container.children().find("table");
	var parent_row = container.parent().prev();
	var review_button = container.find(".btn");
	var item_instance_uris = [];
	var unreview_text = "Unreview List";
	var review_text = "Mark List as Reviewed";

	//add row using latest task_list_instance
	$.each(latest.item_instances,function(i,item_instance){
		add_item_row(details_table,item_instance,task_list_instances);
		item_instance_uris.push(item_instance.resource_uri);
	});


	if (latest.review_status.length > 0){
		review_button.text(unreview_text);
		review_button.button("toggle");
	}else{
		review_button.text(review_text);
	}

	review_button.click(function(event){
		review_button.button("loading");
		var reviewed =$(event.currentTarget).hasClass("active");
		var review_status;
		var button_text;
		var review_user;
		var review_date;

		if (reviewed){
			//since we're already approved user wants to unnaprove
			review_status = QAUtils.UNREVIEWED;
			button_text = review_text;
		}else{
			review_status = QAUtils.APPROVED;
			button_text = unreview_text;
			review_user = "you";
			review_date = (new Date()).toISOString();
		}

		QAUtils.set_item_instances_status(item_instance_uris,review_status,function(results,status){
			//status successfully updated
			review_button.button("complete");
			review_button.attr("data-complete-text",button_text).text(button_text);
			set_task_list_review_status(parent_row,	review_user,review_date);
		});
	});

}
/**************************************************************************/
//when user selects a row either close it if it's already open or
//open it and load details from server
function on_select_task_list(task_list_row){

	var task_lists_data_table = $("#qa-task-list-table").dataTable();
	var table_is_closing = task_list_row.next().children(".qa-details").length > 0;

	if (table_is_closing){
		close_details(task_list_row, task_lists_data_table);
	}else{

		task_list_row.children("td:last").append('<span class="pull-right"><em>Loading...</em></span>');

		var instance_options ={
			task_list:task_list_row.attr("data-task_list_id"),
			unit__number:task_list_row.attr("data-unit_number"),
			frequency:task_list_row.attr("data-frequency"),
			order_by:"-work_completed",
			limit:HISTORY_INSTANCE_LIMIT
		}

		//fetch resources from server and then display them
		QAUtils.get_resources(
			"tasklistinstance",

			function(resources){
				task_list_row.children("td:last").children("span").remove();
				var task_list_instances = resources.objects;

				//make sure we got results from server & user hasn't closed table
				if (task_list_instances.length > 0){
				    var details_container = open_details(task_list_row, task_lists_data_table);
					display_task_list_details(details_container,task_list_instances);
				}
			},
			instance_options
		);
	}
}
/**************************************************************************/
$(document).ready(function(){

	init_task_list_table();

	$("#qa-task-list-table tbody tr").each(function(idx,row){
		update_row_color($(row));
	});

	$("#qa-task-list-table tbody tr").click(function(event){
		on_select_task_list($(event.currentTarget));
	});


});
