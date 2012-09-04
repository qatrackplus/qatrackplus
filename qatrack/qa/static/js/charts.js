"use strict";

var waiting_timeout = null;


/**************************************************************************/
$(document).ready(function(){
	initialize_charts();

	hide_all_tests();

    $(".date").datepicker();

	$("#control-chart-container, #instructions").hide();

	$("#chart-type").change(switch_chart_type);

	$("#toggle-instructions").click(toggle_instructions);

	$("#test-list-filters select, #frequency input, #test-list-container input, #display-options input").change(update_tests);
	$("#gen-chart").click(update_chart);

	update_tests();

});

/****************************************************/
function initialize_charts(){
	create_stockchart([{name:"",data:[[new Date().getTime(),0,0]]}]);
}
/****************************************************/
function hide_all_tests(){
	$("#test input").parent().hide();
}

/***************************************************/
function toggle_instructions(){
	$("#instructions").toggle();

	var visible = $("#instructions").is(":visible");
	var icon = "icon-plus-sign";
	if (visible) {
		icon = "icon-minus-sign";
	}
	$("#toggle-instructions i").removeClass("icon-plus-sign icon-minus-sign").addClass(icon);
}
/***************************************************/
function switch_chart_type(){
	$("#chart-container, #control-chart-container").toggle();
}

/***************************************************/
function update_tests(){
	var frequencies = QAUtils.get_selected_option_vals("#frequency");
	filter_test_lists(frequencies);

	var test_lists = QAUtils.get_checked("#test-list-container");
	var tests = get_tests_for_lists(test_lists);
	var categories = QAUtils.get_selected_option_vals("#category");


	var to_show = filter_tests(tests,categories,frequencies);
	show_tests(to_show);
}

/***************************************************/
function filter_test_lists(frequencies){
	var test_lists = get_test_lists_for_frequencies(frequencies);

	$("#test-list-container input").each(function(i,option){
		var pk = $(this).val();
		if (test_lists.indexOf(pk)>=0){
			$(this).parent().show();
		}else{
			$(this).attr("checked",false)
			$(this).parent().hide();
		}
	});
}

/***************************************************/
function get_test_lists_for_frequencies(frequencies){

	var test_lists = [];

	var i;
	$.each(frequencies,function(i,frequency){
		$.each(QACharts.test_info.test_lists,function(pk,test_list){
			if (test_list.frequencies.indexOf(frequency)>=0){
				test_lists.push(pk)
			}
		});
	});

	return test_lists;

}


/****************************************************/
function get_tests_for_lists(test_lists){
	var all_tests = [];
	var tests,test_list;
	var i;
	$.each(test_lists,function(i,pk){
		test_list =  QACharts.test_info.test_lists[pk];
		if (test_list){
			all_tests.push.apply(all_tests,test_list.tests);
		}
	});

	return all_tests;
}
/****************************************************/
function filter_tests(tests,categories,frequencies){
	var filtered = [];
	$.each(QACharts.test_info.tests,function(idx,test){
		if (
				(categories.indexOf(test.category)>=0) &&
				(tests.indexOf(test.pk) >= 0)
			){
			filtered.push(test.pk);
		}
	});
	return filtered;
}
/****************************************************/
function show_tests(visible_tests){
	$("#test input").each(function(i,option){
		var pk = parseInt($(this).val());
		if (visible_tests.indexOf(pk) >= 0){
			$(this).parent().show();
		}else{
			$(this).attr("checked",false);
			$(this).parent().hide();
		}
	});
}

/****************************************************/
function update_chart(){
	start_chart_update();
	set_chart_url();
	if (basic_chart_selected()){
		create_basic_chart();
	}else{
		create_control_chart();
	}
}
/****************************************************/
function start_chart_update(){
	$("#gen-chart").button("loading");
}
function finished_chart_update(){
	$("#gen-chart").button("reset");
}
/*************************************************************************/
//generate a url to allow linking directly to chart
function set_chart_url(){
	$("#chart-url").val("not implemented yet");
	var filters = get_data_filters();
	filters.from_date = [filters.from_date];
	filters.to_date = [filters.to_date];

	var options = [];

	$.each(filters,function(key,values){
		$.each(values,function(idx,value){
			options.push(key+QAUtils.OPTION_DELIM+value)
		});
	});

	var loc = window.location.protocol + "//"+window.location.hostname+":"+window.location.port+window.location.pathname;

	$("#chart-url").val(loc+"#"+options.join(QAUtils.OPTION_SEP));
}

/***************************************************/
function get_data_filters(){
	var filters = {
		units:QAUtils.get_selected_option_vals("#unit"),
		statuses:QAUtils.get_selected_option_vals("#status"),
		from_date:get_date("#from-date"),
		to_date:get_date("#to-date"),
		tests:QAUtils.get_checked("#test")	,
		n_baseline_subgroups:$("#n-baseline-subgroups").val(),
		subgroup_size:$("#subgroup-size").val(),
		fit_data:$("#include-fit").is(":checked")
	};

	return filters;
}
/***************************************************/
function get_date(date_id){
	return $(date_id).val();
}
/***************************************************/
function basic_chart_selected(){
	return $("#chart-type").val() === "basic";
}

/***************************************************/
function create_basic_chart(){
	retrieve_data(plot_data);
}
/*****************************************************/
function retrieve_data(callback,error){
	var data_filters = get_data_filters();
	if (data_filters.tests.length === 0){
		initialize_charts();
		finished_chart_update();
		return;
	}

	$.ajax({
            type:"get",
            url:QACharts.data_url,
            data:data_filters,
            contentType:"application/json",
            dataType:"json",
            success: function(result,status,jqXHR){
                finished_chart_update();
				callback(result);
            },
            error: function(error){
                finished_chart_update();
                if (typeof console != "undefined") {console.log(error)};
            }
	});

}

/*****************************************************/
function plot_data(data){
	var data_to_plot = convert_data_to_highchart_series(data.data);
	create_stockchart(data_to_plot);
	update_data_table(data);
}
/****************************************************/
function convert_data_to_highchart_series(data){
	var hc_series = [];

	$.each(data,function(idx,series){
		var series_data = [];
		var ref_data = [];
		var tolerance_high = [],tolerance_low=[],ok=[];

		$.each(series.dates,function(idx,date){
			date = QAUtils.parse_iso8601_date(date).getTime();
			series_data.push([date,series.values[idx]]);
			ref_data.push([date,series.references[idx]]);
			ok.push([date,series.tol_low[idx],series.tol_high[idx]]);
			tolerance_low.push([date,series.tol_low[idx],series.act_low[idx]]);
			tolerance_high.push([date,series.tol_high[idx],series.act_high[idx]]);

		});

		hc_series.push({
			name:series.unit.name+" " +series.test.name,
			data:series_data,
			showInLegend:true,
			lineWidth : get_line_width(),
			fillOpacity:1,
			marker : {
				enabled : true,
				radius : 4
			}
		});

		if ($("#show-references").is(":checked")){
			hc_series.push({
				name:series.unit.name+" " +series.test.name + " References",
				data:ref_data,
				lineWidth : 2,
				color:"#468847",
				fillOpacity:1,
				marker : {
					enabled : false
				},
				showInLegend:true
			});
		}
		var tol_color = 'rgba(255, 255, 17, 0.2)';
		var act_color = 'rgba(46, 217, 49, 0.2)';

		if ($("#show-tolerances").is(":checked")){
			hc_series.push({
				data:tolerance_high,
				type:'arearange',
				lineWidth:0,
				fillColor: tol_color,
				name:series.unit.name+" " +series.test.name + " Tol High",
				showInLegend:false

			});

			hc_series.push({
				data:ok,
				type:'arearange',
				lineWidth:0,
				fillColor: act_color,
				name:series.unit.name+" " +series.test.name + " OK",
				showInLegend:false
			});
			hc_series.push({
				data:tolerance_low,
				type:'arearange',
				fillColor: tol_color,
				lineWidth:0,
				name:series.unit.name+" " +series.test.name + " Tol Low",
				showInLegend:false
			});

		}

	});
	return hc_series;
}


/**********************************************************/
function create_stockchart(data){

	window.chart = new Highcharts.StockChart({
		chart : {
			renderTo : 'chart'
		},

		rangeSelector : get_range_options(),
		legend: get_legend_options(),
		plotOptions: {
			line:{
				animation:false
			},
			arearange:{
				animation:false
			}
		},
		tooltip: {
			pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.change})<br/>',
			valueDecimals: 2
		},
		series : data
	});

}
/*********************************************************************/
function get_range_options(){
	return {
		buttons: [
			{ type: 'week', count: 1, text: '1w' },
			{ type: 'month', count: 1, text: '1m'},
			{ type: 'month', count: 6, text: '6m'},
			{ type: 'year',	count: 1, text: '1y' },
			{ type: 'all', text: 'All' }
		],
		selected: 1
	}
}
/*********************************************************************/
function get_legend_options(){
	var legend = {};
	if ($("#show-legend").is(":checked")){
		legend = {
			align: "right",
			layout: "vertical",
			enabled: true,
			verticalAlign: "middle"
		}
	}
	return legend;
}
/*********************************************************************/
function get_line_width(){
	if ($("#show-lines").is(":checked")){
		return 2;
	}else{
		return 0;
	}
}
/*********************************************************************/
function create_control_chart(){
	$("#control-chart-container").find("img, div.please-wait, div.cc-error").remove();
	$("#control-chart-container").append("<img/>");
	$("#control-chart-container img").error(control_chart_error);
	$("#control-chart-container").append('<div class="please-wait"><em>Please wait for control chart to be generated...this could take a few minutes.</em></div>');

	waiting_timeout = setInterval("check_cc_loaded()",250);
	var chart_src_url = get_control_chart_url();
	$("#control-chart-container img").attr("src",chart_src_url);

}

/*************************************************************************/
//Clean up after Control Chart created
function check_cc_loaded(){

	if ($("#control-chart-container img").height()>100){
		control_chart_finished();
	}
}
function control_chart_error(){
	control_chart_finished();
	$("#control-chart-container img").remove();
	$("#control-chart-container").append('<div class="cc-error">Something went wrong while generating your control chart</div>');
}
function control_chart_finished(){
	$("#control-chart-container div.please-wait").remove();
	clearInterval(waiting_timeout);
	retrieve_data(update_data_table);
}
/**************************************************************************/
function get_control_chart_url(){
	var filters = get_data_filters();

	var	props = [
		"width="+$("#chart-container").width(),
		"height="+$("#test").height(),
		"timestamp="+ new Date().getTime()
	];

	$.each(filters,function(k,v){
		if(	$.isArray(v)){
			$.each(v,function(i,vv){
				props.push(encodeURI(k+"[]="+vv));
			});
		}else{
			props.push(encodeURI(k+"="+v));
		}
	});

	return QACharts.control_chart_url+"?"+props.join("&");
}


function update_data_table(data){
	$("#data-table-wrapper").html(data.table);
}

/**************************************************************************/
//set initial options based on url hash
function set_options_from_url(){
    var options = QAUtils.options_from_url_hash(document.location.hash);
	var f,o;
	var clear_if_option_exists = ["unit", "test"];
	for (f in clear_if_option_exists){
		for (o in options){
			if (clear_if_option_exists[f] == options[o][0]){
				$("#"+clear_if_option_exists[f]+"-filter input").attr("checked",false);
				break;
			}
		}
	}

	var key,value;
    $.each(options,function(idx,option){
		key = option[0];
		value = option[1];
        switch(key){
            case  "slug" :
                $("#test-filter input[value="+value+"]").attr("checked","checked");
            break;
            case "unit":
                $("#unit-filter input[value="+value+"]").attr("checked","checked");
                break;
            default:
                break;
        }

    });
    update();
}

