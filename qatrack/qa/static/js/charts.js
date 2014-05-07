"use strict";

var waiting_timeout = null;

var next_color = (function(){

    var pointer = 0;

    var colors = [
        '#4572A7',
        '#AA4643',
        '#89A54E',
        '#80699B',
        '#3D96AE',
        '#DB843D',
        '#92A8CD',
        '#A47D7C',
        '#B5CA92'
    ];

    return function(){
        var color = colors[pointer];
        pointer = (colors.length + pointer +1) % colors.length;
        return color;

    }
})();


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

    $("#data-table-wrapper").on('click',"#csv-export",export_csv);


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
        tests:QAUtils.get_checked("#test-container"),
        test_lists:QAUtils.get_checked("#test-list-container"),
        frequencies:QAUtils.get_checked("#frequency-container"),
        n_baseline_subgroups:$("#n-baseline-subgroups").val(),
        subgroup_size:$("#subgroup-size").val(),
        fit_data:$("#include-fit").is(":checked"),
        combine_data:$("#combine-data").is(":checked"),
        relative:$("#relative-diff").is(":checked")
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
        url:QAURLs.CHART_DATA_URL,
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
function convert_data_to_highchart_series(data){
    var hc_series = [];

    var show_tol = $("#show-tolerances").is(":checked");
    var show_ref = $("#show-references").is(":checked");

    var data_max=-1E10, data_min=1E10;
    var notNull = function(x){return !_.isNull(x);};

    _.each(_.keys(data), function(name){
        var series_data = [];
        var ref_data = [];
        var tolerance_high = [],tolerance_low=[],ok=[];
        var series_color = next_color();

        var al, tl, th, ah;

        _.each(data[name], function(point){
            var date = QAUtils.parse_iso8601_date(point.date).getTime();
            var display = '<span style="color:'+series_color+'"><strong>'+name+'</strong></span>: <b>'+ QAUtils.format_float(point.value) + '</b>';

            if (!_.isNull(point.reference)){
                display += "<br/><em>Ref:" + QAUtils.format_float(point.reference)+"</em><br/>";
            }

            display += " <em>Act Low: " + (!_.isNull(point.act_low) ? QAUtils.format_float(point.act_low) : "--");
            display += " Tol Low: " + (!_.isNull(point.tol_low) ? QAUtils.format_float(point.tol_low) : "--");
            display += " Tol High: " + (!_.isNull(point.tol_high) ? QAUtils.format_float(point.tol_high) : "--");
            display += " Act High: " + (!_.isNull(point.act_high) ? QAUtils.format_float(point.act_high) : "--");

            data_max = _.max(_.filter([data_max, point.act_high, point.tol_high, point.reference, point.value],notNull));
            data_min = _.min(_.filter([data_min, point.act_low, point.tol_low, point.reference, point.value],notNull));

            al = !_.isNull(point.act_low) ? point.act_low : -1.e10;
            tl = !_.isNull(point.tol_low) ? point.tol_low : -1.e10;
            th = !_.isNull(point.tol_high) ? point.tol_high : 1.e10;
            ah = !_.isNull(point.act_high) ? point.act_high : 1.e10;

            series_data.push({name:display,x:date,y:point.value});
            ref_data.push({name:"",x:date,y:point.reference});
            ok.push({name:"",x:date,low:tl,high:th});
            tolerance_low.push({name:"",x:date,low:tl,high:al});
            tolerance_high.push({name:"",x:date,low:th,high:ah});
        });

        hc_series.push({
            name:name,
            data:series_data,
            showInLegend:true,
            lineWidth : get_line_width(),
            fillOpacity:1,
            color:series_color,
            marker : {
                enabled : true,
                radius : 4
            }
        });

        hc_series.push({
            name:name + " References",
            data:ref_data,
            lineWidth : 2,
            dashStyle:"ShortDash",
            color:series_color,
            fillOpacity: 1,
            marker : {
                enabled : false
            },
            showInLegend:true,
            enableMouseTracking:false,
            visible: show_ref
        });

        var tol_color = 'rgba(255, 255, 17, 0.2)';
        var act_color = 'rgba(46, 217, 49, 0.2)';

        if (!show_tol){
            tol_color = 'rgba(255, 255, 255, 0)';
            act_color = 'rgba(255, 255, 255, 0)';
        }

        hc_series.push({
            data:_.map(tolerance_high,function(th){
                th.low= _.min([th.low,data_max]);
                th.high=_.min([th.high,data_max]);
                return th;
            }),
            type:'arearange',
            lineWidth:0,
            fillColor: tol_color,
            name:name+" Tol High",
            showInLegend:false,
            enableMouseTracking:false,
            visible:show_tol
        });

        hc_series.push({
            data:_.map(ok,function(v){
                v.low= _.max([v.low,data_min]);
                v.high=_.min([v.high,data_max]);
                return v;
            }),
            type:'arearange',
            lineWidth:0,
            fillColor: act_color,
            name:name + " OK",
            showInLegend:false,
            enableMouseTracking:false,

            visible:show_tol
        });
        hc_series.push({
            data:_.map(tolerance_low,function(tl){
                tl.low =_.max([tl.low,data_min]);
                tl.high=_.max([tl.high,data_min]);
                return tl;
            }),
            type:'arearange',
            fillColor: tol_color,
            lineWidth:0,
            name:name+ " Tol Low",
            showInLegend:false,
            enableMouseTracking:false,

            visible:show_tol
        });



    });
    return hc_series;
}


/**********************************************************/
function create_stockchart(data){

    var prev_range = window.chart.rangeSelector ? window.chart.rangeSelector.selected:"";


    var ntests = QAUtils.get_checked("#test-container").length;

    window.chart = new Highcharts.StockChart({
        chart : {
            renderTo : 'chart'
        },

        rangeSelector : get_range_options(prev_range),
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
        tooltip:{

            formatter: function() {
                var tip = _.pluck(this.points,"key").join("<br/>");
                return tip;
            },
            useHTML:true
        },
        series : data
    });

}
/*********************************************************************/
function get_range_options(prev_selection){

    return {
        buttons: [
            { type: 'week', count: 1, text: '1w' },
            { type: 'month', count: 1, text: '1m'},
            { type: 'month', count: 6, text: '6m'},
            { type: 'year',    count: 1, text: '1y' },
            { type: 'all', text: 'All' }
        ],
        selected: prev_selection || 4
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
    $("#data-table-wrapper").html("");
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

    return QAURLs.CONTROL_CHART_URL+"?"+props.join("&");
}


function update_data_table(data){
    $("#data-table-wrapper").html(data.table);
}
/*************************************************************************/
//Return all test lists that contain one ore more of the input tests
function get_test_lists_from_tests(tests){
    var test_lists = [];
    _.each(tests,function(test){
        _.each(QACharts.test_info.test_lists,function(e,i){
            if (_.contains(e,parseInt(test))){
                test_lists.push(i);
            }
        });
    });

    return _.uniq(test_lists);
}
/**************************************************************************/
//set initial options based on url hash
function set_options_from_url(){
    var unit_ids,test_ids,freq_ids,test_list_ids;

    var options = QAURLs.options_from_url_hash(document.location.hash);

    var units = get_filtered_option_values("units",options);
    var tests = get_filtered_option_values("tests",options);
    var    test_lists = get_test_lists_from_tests(tests);

    if ((units.length === 0) || (tests.length === 0)){
        return;
    }

    unit_ids = _.map(units,function(pk){return "#unit-"+pk;});
    test_ids = _.map(tests,function(pk){return "#test-"+pk;});
    test_list_ids = _.map(test_lists,function(pk){return "#test-list-"+pk;});


    var filters = ["#unit-container","#frequency-container","#test-list-container"];

    _.map(filters,show_all_inputs);

    //    $(".test-list").attr("checked",true);
    QAUtils.set_checked_state(test_list_ids,true);
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

function export_csv(){
    var header = [];
    _.each($("#data-table-wrapper table thead tr:first-child th"),function(e){
        header.push(["Date",'"'+e.innerHTML.replace('"','""')+'"',"Ref"].join(","));
    });
    header = header.join(",");
    var lines = [header];

    _.each($("#data-table-wrapper table tbody tr"),function(row){
        lines.push(_.map($(row).find("td"),function(e){return e.innerHTML;}).join(","));
    });

    var blob = new Blob([lines.join("\n")], {type: "text/plain;charset=utf-8"});
    saveAs(blob, "qatrack_export.csv");

}
