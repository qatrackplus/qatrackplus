var HISTORY_INSTANCE_LIMIT = 5;

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
			{"sType":"span-day-month-year-sort"}, //due date
			null, //status of test list tests
			null  //review status of list
		]

	} ).columnFilter({

		aoColumns: [
			{type: "select"}, //Unit
			{type: "select"}, //Freq
			{type: "text" }, // Test list name
			{type: "text" }, //date completed
			{type: "text" }, //due date
			{ type: "text" }, //status of test list tests
			null //review status of list
		]
	});

}
/**************************************************************************/
//creates the html table to hold the tests from a test list
function create_test_list_table(id){
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
//generate a spark line in the provided container for a given test
function create_spark_line(container,test,test_list_instances){
	//find historical values for this test
	var vals = [], refs = [], dates=[];
	var tols = {act_high:[],act_low:[],tol_high:[],tol_low:[]};

	$.each(test_list_instances.reverse(),function(i,tl_instance){
		//above is reverse since query was ordered by -work_complete
		$.each(tl_instance.test_instances,function(j,test_instance){
			if (test_instance.test.id === test.id){
				dates.push(QAUtils.parse_iso8601_date(test_instance.work_completed))
				vals.push(test_instance.value)

				if (test_instance.reference !== null){
					refs.push(test_instance.reference.value);
				}else{
					refs.push(null);
				}

				if ((test_instance.tolerance !== null) && (test_instance.reference !== null)){
					var tol = QAUtils.convert_tol_to_abs(test_instance.reference.value,test_instance.tolerance);
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
//add a row to a details table for the input test instance
function add_test_row(parent,instance,test_list_instances){

	var test = instance.test;

	var data = [];
	data.push("<strong>"+test.name+"</strong>");
	data.push(test.category.name);

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

	var review_link = QAUtils.unit_test_chart_link(instance.unit,test,"Details");
	data.push(review_link);

	$(parent).dataTable().fnAddData(data);
	var test_row = parent.find("#"+spark_id).parent().parent();

	create_spark_line($("#"+spark_id),instance.test,test_list_instances);

	//set color Pass/Fail column based on test
	var pass_fail_td = test_row.find("span.pass-fail");
	pass_fail_td.css("background-color",QAUtils.qa_color(instance.pass_fail));
	pass_fail_td.addClass("label");
	return test_row;
}

/************************************************************************/
//remove instance details row below input test_list_row for a given data_table
function close_details(test_list_row,data_table){
	data_table.fnClose(test_list_row[0]);
}
/************************************************************************/
//open test list instance details row below input test_list_row for a given data_table
function open_details(test_list_row,data_table){

	var unit_number = test_list_row.attr("data-unit_number");
	var test_list_id = test_list_row.attr("data-test_list_id");
	var frequency = test_list_row.attr("data-frequency");
	var sub_table_id = 'test-list-'+test_list_id+'-unit-'+unit_number;

	data_table.fnOpen(test_list_row.get(0),create_test_list_table(sub_table_id),"qa-details");

	$("#"+sub_table_id).dataTable( {
		"sDom": "<'row-fluid'<'span12't>>",
		"bFilter":false,
		"bPaginate": false,
		"bLengthChange":true,
	} );

	var details = test_list_row.next().children(".qa-details");
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
		review_td.find("span").addClass("alert-success");
	}else{
		review_td.find("span").addClass("alert-info");
	}
}
/************************************************************************/
//update review status displayed for a given row
function set_test_list_review_status(row,user,date){

	var status = '<span class="label label-info">Unreviewed</span>';
	var review_button = row.next("tr").find(".btn").button();
	var review_cell = 	row.find("td.review_status");
	var cls = QAUtils.UNREVIEWED;

	if (user && date){
		date = QAUtils.parse_iso8601_date(date);
		status = '<span class="label label-success">Reviewed by '+ user;
		status+= " on " + QAUtils.format_date(date,true)+'</span>';
		cls = QAUtils.APPROVED;
	}

	review_cell.html(status).removeClass(QAUtils.UNREVIEWED).removeClass(QAUtils.APPROVED);
	review_cell.addClass(cls);
	update_row_color(row);
}

/************************************************************************/
//display all the tests from the the test list instance
function display_test_list_details(container,test_list_instances){

	var latest = test_list_instances[0];
	var details_table = container.children().find("table");
	var parent_row = container.parent().prev();
	var review_button = container.find(".btn");
	var test_instance_uris = [];
	var unreview_text = "Unreview List";
	var review_text = "Mark List as Reviewed";

	//add row using latest test_list_instance
	$.each(latest.test_instances,function(i,test_instance){
		add_test_row(details_table,test_instance,test_list_instances);
		test_instance_uris.push(test_instance.resource_uri);
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

		QAUtils.set_test_instances_status(test_instance_uris,review_status,function(results,status){
			//status successfully updated
			review_button.button("complete");
			review_button.attr("data-complete-text",button_text).text(button_text);
			set_test_list_review_status(parent_row,	review_user,review_date);
		});
	});

}
/**************************************************************************/
//when user selects a row either close it if it's already open or
//open it and load details from server
function on_select_test_list(test_list_row){

	var test_lists_data_table = $("#qa-test-list-table").dataTable();
	var table_is_closing = test_list_row.next().children(".qa-details").length > 0;

	if (table_is_closing){
		close_details(test_list_row, test_lists_data_table);
	}else{

		test_list_row.children("td:last").append('<span class="pull-right"><em>Loading...</em></span>');

		var instance_options ={
			test_list:test_list_row.attr("data-test_list_id"),
			unit__number:test_list_row.attr("data-unit_number"),
			frequency:test_list_row.attr("data-frequency"),
			order_by:"-work_completed",
			limit:HISTORY_INSTANCE_LIMIT
		};

		//fetch resources from server and then display them
		QAUtils.get_resources(
			"testlistinstance",

			function(resources){
				test_list_row.children("td:last").children("span:last").remove();
				var test_list_instances = resources.objects;

				//make sure we got results from server & user hasn't closed table
				if (test_list_instances.length > 0){
				    var details_container = open_details(test_list_row, test_lists_data_table);
					display_test_list_details(details_container,test_list_instances);
				}
			},
			instance_options
		);
	}
}
/**************************************************************************/
$(document).ready(function(){

	init_test_list_table();

	$("#qa-test-list-table tbody tr").each(function(idx,row){
		update_row_color($(row));
	});

	$("#qa-test-list-table tbody tr").click(function(event){
		on_select_test_list($(event.currentTarget));
	});

	$("tbody tr.has-due-date").each(function(idx,row){
		var date_string = $(this).data("due");
		var due_date = null;
		if (date_string !== ""){
			due_date = QAUtils.parse_iso8601_date(date_string);
		}
		var freq = $(this).data("frequency");
		QAUtils.set_due_status_color($(this).find(".due-status"),due_date,freq);
	});

});
