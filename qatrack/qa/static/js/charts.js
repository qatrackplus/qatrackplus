"use strict";

var waiting_timeout = null;


/**************************************************************************/
$(document).ready(function(){
   initialize_charts();

    var test_filters = ["#test-list-container","#test-container","#frequency-container"];
    _.each(test_filters,function(container){
        hide_all_inputs(container);
    });

    $(".date").datepicker({autoclose:true});

    $("#control-chart-container, #instructions").hide();

    $("#chart-type").change(switch_chart_type);

    $("#toggle-instructions").click(toggle_instructions);

    $(".test-filter input").change(update_tests);

    $("#gen-chart").click(update_chart);

    set_chart_options();
    set_options_from_url();

});

/****************************************************/
function initialize_charts(){
    create_stockchart([{name:"",data:[[new Date().getTime(),0,0]]}]);
}
/****************************************************/
function hide_all_inputs(container){
    $(container + " input").parent().hide();
}
function show_all_inputs(container){
    $(container + " input").parent().show();
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
    set_chart_options();
    $("#chart-container, #control-chart-container").toggle();
}
/***************************************************/
function set_chart_options(){
    if (basic_chart_selected()){
        $("#basic-chart-options").show();
        $("#cc-chart-options").hide();
    }else{
        $("#basic-chart-options").hide();
        $("#cc-chart-options").show();
    }
}
/***************************************************/
function update_tests(){
    set_frequencies();
    set_test_lists();
    set_tests();
}
/***************************************************/
function set_frequencies(){
    var units = QAUtils.get_checked("#unit-container");
    var frequencies = [];
    _.each(units,function(unit){
        frequencies = _.union(frequencies,_.keys(QACharts.test_info.unit_frequency_lists[unit]))
    });

    filter_container("#frequency-container",frequencies);
}

/***************************************************/
function set_test_lists(){
    var units = QAUtils.get_checked("#unit-container");
    var frequencies = QAUtils.get_checked("#frequency-container");

    var test_lists = [];

    _.each(units,function(unit){
        _.each(frequencies,function(freq){
            test_lists = _.union(test_lists,QACharts.test_info.unit_frequency_lists[unit][freq]);
        });
    });

    filter_container("#test-list-container",test_lists);
}
/***************************************************/
function set_tests(){

    var test_lists = QAUtils.get_checked("#test-list-container");
    var tests = []
    _.each(test_lists,function(test_list){
        tests = _.union(tests,QACharts.test_info.test_lists[test_list]);
    });

    filter_container("#test-container",tests);
}
/***************************************************/
function filter_container(container,visible){
    visible = _.map(visible,function(x){return parseInt(x);});
    $(container+" input").each(function(i,option){
        var pk = parseInt($(this).val());
        if (visible.indexOf(pk)>=0){
            $(this).parent().show();
        }else{
            $(this).attr("checked",false)
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

    var filters = get_data_filters();

    var options = [];

    $.each(filters,function(key,values){
        if (_.isArray(values)){
            $.each(values,function(idx,value){
                options.push(key+QAUtils.OPTION_DELIM+value)
            });
        }else if (!_.isEmpty(values)){
            options.push(key+QAUtils.OPTION_DELIM+values)
        }
    });

    var loc = window.location.protocol + "//"+window.location.hostname;
    if (window.location.port !== ""){
        loc += ":"+window.location.port;
    }

    loc += window.location.pathname;

    $("#chart-url").val(loc+"#"+options.join(QAUtils.OPTION_SEP));
}

/***************************************************/
function get_data_filters(){
    var filters = {
        units:QAUtils.get_checked("#unit-container"),
        statuses:QAUtils.get_checked("#status-container"),
        from_date:get_date("#from-date"),
        to_date:get_date("#to-date"),
        tests:QAUtils.get_checked("#test-container")    ,
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
        xAxis:{
            ordinal: false
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
            { type: 'year',    count: 1, text: '1y' },
            { type: 'all', text: 'All' }
        ],
        selected: 4
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

    var    props = [
        "width="+$("#chart-container").width(),
        "height="+$("#chart").height(),
        "timestamp="+ new Date().getTime()
    ];

    $.each(filters,function(k,v){
        if(    $.isArray(v)){
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
    var unit_ids,test_ids,freq_ids,test_list_ids;

    var options = QAUtils.options_from_url_hash(document.location.hash);

    var units = get_filtered_option_values("units",options);
    var tests = get_filtered_option_values("tests",options);

    if ((units.length === 0) || (tests.length === 0)){
        return;
    }

    unit_ids = _.map(units,function(pk){return "#unit-"+pk;});
    test_ids = _.map(tests,function(pk){return "#test-"+pk;});

    var filters = ["#unit-container","#frequency-container","#test-list-container"];

    _.map(filters,show_all_inputs);
    $(".test-list").attr("checked",true);
    QAUtils.set_checked_state(unit_ids,true);
    update_tests();
    QAUtils.set_checked_state(test_ids,true);

    update_chart();

}


function get_filtered_option_values(opt_type,options){
    var opt_value = function(opt){return opt[1];};
    var f = function(opt){return opt[0] == opt_type;};
    return _.map(_.filter(options,f),opt_value);
}
