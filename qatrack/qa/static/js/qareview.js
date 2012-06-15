var HISTORY_INSTANCE_LIMIT = 5;

/************************************************************************/
//create a dropdown element for different review statuses
function make_status_select(){
	var status_options =[[null,""]];
	var i,status;
	for (i=0; i < QAUtils.STATUSES.length; i += 1){
		status = QAUtils.STATUSES[i];
		status_options.push([status, QAUtils.STATUS_DISPLAYS[status]]);
	}
	return QAUtils.make_select("","input-medium pull-right status-update-value",status_options)
}
/**************************************************************************/
//creates the html table to hold the tests from a test list
function create_test_list_table(id){
	var headers = '<tr><th class="name-col">Name</th><th>Type</th><th>Comment</th><th>Pass/Fail</th><th>Value</th><th class="ref-col">Ref/Tol</th><th class="history-col">History</th><th>Review URL</th><th>Review Status</th><th><input type="checkbox" class="toggle_children"/></tr>';
	var elements = [
		'<div class="review-status-container ">',
		'<span class="label collection-review-status"></span>',

		make_status_select(),
		'<button data-loading-text="Updating..." class="pull-right btn update-review-status">Apply To Selected</button>',

		'</div>',
		'<table class="table table-bordered table-condensed table-striped sub-table" id="'+id+'">',
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
//return review status span for input instance
function create_review_status(instance){
	var title = "";
	if (instance.reviewed){
		title = 'title="Reviewed by '+instance.reviewed_by+' on '+instance.review_date+'"';
	}
	return '<span class="label label-info review-status '+instance.status+'" '+title+'>'+QAUtils.STATUS_DISPLAYS[instance.status]+'</span>';
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


	data.push(create_review_status(instance));

	data.push('<input type="checkbox" class="test-selected"/>');

	$(parent).dataTable().fnAddData(data);
	var test_row = parent.find("#"+spark_id).parent().parent();
	test_row.data("instance_id",instance.id);
	test_row.data("instance_uri",instance.resource_uri);
	create_spark_line($("#"+spark_id),instance.test,test_list_instances);

	//set color Pass/Fail column based on test
	var pass_fail_td = test_row.find("span.pass-fail");
	pass_fail_td.css("background-color",QAUtils.qa_color(instance.pass_fail));
	pass_fail_td.addClass("label");
	return test_row;
}

/************************************************************************/
//remove instance details row below input test_list_row for a given data_table
function close_details(test_list_row){
	test_list_row.closest("table").dataTable().fnClose(test_list_row[0]);
}

/************************************************************************/
//open test list instance details row below input test_list_row for a given data_table
function open_details(test_list_row,data_table){

	var unit_number = test_list_row.data("unit_number");
	var test_list_id = test_list_row.find(".instance-id").find("option:selected").data("test_list_id");
	var frequency = test_list_row.data("frequency");
	var sub_table_id = 'test-list-'+test_list_id+'-unit-'+unit_number;

	data_table.fnOpen(test_list_row.get(0),create_test_list_table(sub_table_id),"qa-details");

	$("#"+sub_table_id).dataTable( {
		"sDom": "<'row-fluid'<'span12't>>",
		"bFilter":false,
		"bPaginate": false,
		"bLengthChange":true,
	} );

	return test_list_row.next().children(".qa-details");
}

/************************************************************************/
//display all the tests from the the test list instance
function display_test_list_details(container,instance_id,test_list_instances){
	var idx,to_review;
	for (idx = 0; idx < test_list_instances.length; idx+=1){
		if (test_list_instances[idx].id === instance_id){
			to_review = test_list_instances[idx];
			break;
		}
	}

	container.css('background-color',QAUtils.REVIEW_COLOR);

	//add row using to_review test_list_instance
	$.each(to_review.test_instances,function(i,test_instance){
		add_test_row(container.find("table"),test_instance,test_list_instances);
	});

}

/**************************************************************************/
//return all test rows selected within a test collection
function get_selected_test_rows(container){
	return container.find("input.test-selected:checked").closest("tr");
}

/**************************************************************************/
//grab given data attribute from all selected test rows
function get_selected_test_data_elements(container,data_element){
	var data = [];
	get_selected_test_rows(container).each(function(){
		data.push($(this).data(data_element));
	});
	return data;
}

/**************************************************************************/
//set the review status for all input test rows
function set_review_status_for_rows(rows,status){
	var labels = rows.find(".label.review-status");
	labels.removeClass(QAUtils.STATUSES.join(" ")).addClass(status);
	labels.text(QAUtils.STATUS_DISPLAYS[status]);
}

/**************************************************************************/
//update the label for the number of unreviewed tests and adjust the
//drop down option to reflect its review status
function update_collection_review_status(container){
	var unreviewed = container.find(".label.review-status.unreviewed");
	var status = container.find(".collection-review-status");

	status.removeClass("label-info label-warning label-success label-important");
	status.addClass(unreviewed.length === 0 ? "label-success" : "label-warning");
	status.html('<span>'+unreviewed.length + "</span> Unreviewed Tests");

	var collection_row = container.parent().prev();
	var opt = collection_row.find("select.instance-id option:selected");
	opt.removeClass("reviewed").removeClass("unreviewed");
	opt.text(opt.text().replace("*",""));

	if (unreviewed.length > 0){
		opt.addClass("unreviewed");
		opt.text("*"+opt.text()+"*");
	}else{
		opt.addClass("reviewed");
	}

	set_review_status(collection_row);
}

/**************************************************************************/
//User clicked Apply To Selected button. Update the status of the selected
//tests and then update appropriate review statuses
function update_statuses_for_collection(container){

	var new_status = container.find(".status-update-value").val();
	var uris = get_selected_test_data_elements(container,"instance_uri");
	var button = container.find(".update-review-status");
	var button_text = button.text();

	if ((uris.length > 0) && ( new_status !== "")){

		button.button("loading");

		QAUtils.set_test_instances_status(uris,new_status,function(results,status){

			if (status === "success"){
				set_review_status_for_rows(get_selected_test_rows(container),new_status);
				update_collection_review_status(container.closest(".qa-details"));
				update_total_unreviewed();
			}

			button.button("complete");
			button.data("complete-text",button_text).text(button_text);
		});
	}
}
/**************************************************************************/
//update the review status for a test collection row
function set_review_status(container){
	var unreviewed = container.find("select.instance-id").find("option.unreviewed");
	var counter = container.find(".unreviewed-count");
	var wrapper = counter.parent();
	counter.text(unreviewed.length);
	set_review_status_color(counter);
}
/**************************************************************************/
//appropriately color input unreviewed status counter
function set_review_status_color(counter){
	var wrapper = counter.parent();
	wrapper.removeClass("label-warning label-success");
	wrapper.addClass(parseInt(counter.text()) === 0 ? "label-success" : "label-warning");
}
/**************************************************************************/
//update all total unreviewed counters on page
function update_total_unreviewed(){
	var total = 0;
	var counter = $(".total-unreviewed-count");

	$(".unreviewed-count").each(function(){
		total += parseInt($(this).text());
	});
	counter.text(total);
	set_review_status_color(counter);

}

/**************************************************************************/
//when user selects a row either close it if it's already open or
//open it and load details from server
function on_select_test_list(test_list_row){

	var review_table = $(".review-table").dataTable();

	test_list_row.children("td:last").append('<span class="pull-right"><em>Loading...</em></span>');
	var instance_id = test_list_row.find(".instance-id").val();
	var instance_options ={
		test_list:test_list_row.find(".instance-id").find("option:selected").data("test_list_id"),
		unit__number:test_list_row.data("unit_number"),
		frequency:test_list_row.data("frequency"),
		order_by:"-work_completed",
		id__lte:instance_id,
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
				var details_container = open_details(test_list_row, review_table);
				display_test_list_details(details_container,instance_id,test_list_instances);
				update_collection_review_status(details_container);
				set_review_status(details_container.find(".review-status-container"));
			}
		},
		instance_options
	);

}

/**************************************************************************/
$(document).ready(function(){

	//user changed the selected instance for a TestCollection
	$("select.instance-id").change(function(event){
		var test_list_row = $(event.currentTarget).parents("tr");
		if ($(event.currentTarget).val() === "hide"){
			close_details(test_list_row);
		}else{
			on_select_test_list(test_list_row);
		}
	});

	//(de)select checkboxes for child tests when user clicks on header checkbox
	$("input.toggle_children").live("change",function(e){
		$(this).closest(".qa-details").find("input.test-selected, input.toggle_children").attr("checked",$(this).is(":checked"))
	});

	//user updated review status of tests
	$(".update-review-status").live("click",function(){
		update_statuses_for_collection($(this).closest(".qa-details"))
	});

});
