"use strict";
var test_list_data = {};
var main_graph;
var previous_point = null;
var test_list_members = {}; //short names of test list tests belonging to test lists


/*************************************************************************/
//return all checked checkboxes within container
function get_checked(container){
    var vals =  [];
    $(container+" input[type=checkbox]:checked").each(function(i,cb){
        vals.push(cb.value);
    });
    return vals;
}

/*************************************************************************/
//Clean up after Control Chart created
var waiting_timeout = null;
function check_cc_loaded(){

	if ($("#control-chart-container img").height()>100){
		$("#control-chart-container div.please-wait").remove();
		clearInterval(waiting_timeout);
		finished_chart_update()
	}
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
/**************************************************************************/
function get_control_chart_url(){
	var filters = get_data_filters();

	var	props = [
		"width="+$("#chart-container").width(),
		"height="+$("#chart").height(),
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
	console.log(props.join("&"));

	return QACharts.control_chart_url+"?"+props.join("&");
}


/**************************************************************************/
$(document).ready(function(){
	$.when(QAUtils.init()).done(function(){
		initialize_charts();

		hide_all_tests();
				
		$("#control-chart-container").hide();
		
		$("#chart-type").change(switch_chart_type);
		
		$("#test-list-filters select").change(update_tests);

		$("#gen-chart").click(update_chart);
		$("#display-options input").change(update_chart);
	});
});

function initialize_charts(){
	create_stockchart([{name:"",data:[[new Date().getTime(),0]]}]);
}
function switch_chart_type(){
	$("#chart-container, #control-chart-container").toggle();
}

function hide_all_tests(){
	$("#test input").parent().hide();	
}

function update_tests(){
	var test_lists = get_selected_option_vals("#test-list");
	var tests = get_tests_for_lists(test_lists);
	var categories = get_selected_option_vals("#category");
	var frequencies = get_selected_option_vals("#frequency");

	var to_show = filter_tests(tests,categories,frequencies);
	show_tests(to_show);
}

function get_selected_option_vals(select_id){
	var selected = [];

	$(select_id).find(":selected").each(function(){
		selected.push(parseInt($(this).val()));
	});
	return selected;
}

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

function filter_tests(tests,categories,frequencies){
	var filtered = [];
	$.each(QACharts.test_info.tests,function(idx,test){
		if (
				(categories.indexOf(test.category)>=0) &&
				(test.frequency === null || frequencies.indexOf(test.frequency) >= 0) &&
				(tests.indexOf(test.pk) >= 0)
			){
			filtered.push(test.pk);
		}
	});
	return filtered;
}

function show_tests(visible_tests){
	$("#test input").each(function(i,option){
		var pk = parseInt($(this).val());
		if (visible_tests.indexOf(pk) >= 0){
			$(this).parent().show();
		}else{
			$(this).attr(":checked",false);
			$(this).parent().hide();
		}
	});
}

function update_chart(){
	start_chart_update();
	set_chart_url();
	if (basic_chart_selected()){
		create_basic_chart();
	}else{
		create_control_chart();
	}
}
function basic_chart_selected(){
	return $("#chart-type").val() === "basic";
}
function create_basic_chart(){

	var data = get_data_filters();
	if (data.tests.length === 0){
		initialize_charts();
		finished_chart_update();
		return;
	}

	$.ajax({
            type:"get",
            url:QACharts.data_url,
            data:data,
            contentType:"application/json",
            dataType:"json",
            success: function(result,status,jqXHR){
                finished_chart_update();
				plot_data(result);
            },
            error: function(error){
                finished_chart_update();
                if (typeof console != "undefined") {console.log(error)};
            }
	});

}

function plot_data(data){

	var data_to_plot = convert_data_to_highchart_series(data);
	create_stockchart(data_to_plot);
}
function create_stockchart(data){
	window.chart = new Highcharts.StockChart({
            chart : {
                renderTo : 'chart',
				animation:false
            },

            rangeSelector : {
                selected : 1
            },

            title : {
                text : 'QA Values'
            },

            plotOptions: {
                series: {
					lineWidth : get_line_width(),
					marker : {
						enabled : true,
						radius : 4
					}					
                },
				line:{
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
function get_line_width(){
	if ($("#show-lines").is(":checked")){
		return 2;
	}else{
		return 0;
	}
}
function convert_data_to_highchart_series(data){
	var hc_series = [];
	
	$.each(data,function(idx,series){
		var series_data = []
		$.each(series.data,function(idx,values){
			var date = QAUtils.parse_iso8601_date(values[0]).getTime();
			series_data.push([date,values[1]]);
		});
		

		hc_series.push({
			name:series.unit.name+" " +series.test.name,
			data:series_data
		});


	});
	return hc_series;
}

function create_control_chart(){
	$("#control-chart-container img").remove();
	$("#control-chart-container").append("<img/>");

	$("#control-chart-container").append('<div class="please-wait"><em>Please wait for control chart to be generated...this could take a few minutes.</em></div>');

	waiting_timeout = setInterval("check_cc_loaded()",250);
	var chart_src_url = get_control_chart_url();
	$("#control-chart-container img").attr("src",chart_src_url);

}
function start_chart_update(){
	$("#gen-chart").button("loading");
}
function finished_chart_update(){
	$("#gen-chart").button("reset");
}
function get_data_filters(){
	var filters = {	
		units:get_selected_option_vals("#unit"),
		statuses:get_selected_option_vals("#status"),
		from_date:get_date("#from-date"),
		to_date:get_date("#to-date"),
		tests:get_selected_tests(),
		n_baseline_subgroups:$("#n-baseline-subgroups").val(),
		subgroup_size:$("#subgroup-size").val(),
		fit_data:$("#include-fit").is(":checked")		
	};

	return filters;
}

function get_date(date_id){
	return $(date_id).val();


}
function get_selected_tests(){
	return get_checked("#test");
	var tests = [];
	$("input.test:checked").each(function(){
		tests.push($(this).val());
	});
	return tests;
}
