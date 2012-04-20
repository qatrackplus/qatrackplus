var task_list_data = {};
var main_graph_series = [{}];
var main_graph;
var previous_point = null;

/************************************************************************/
//data returned from the API has dates in ISO string format and must be converted
//to javascript dates
function convert_data(data){
    var converted = [];
    $(data).each(function(idx,measured){
        converted.push([Date.parse(measured.date),measured.value]);
    });
    return converted;

}
function convert(data){
    var series = {
        values:[],
        references:[],
        act_low:[],
        tol_low:[],
        tol_high:[],
        act_high:[]
    };
    $(data).each(function(idx,measured){
        var date = Date.parse(measured.date);
        series.values.push([date,measured.value]);
        series.references.push([date,measured.reference]);

        var tol = measured.tolerance;
        if (measured.tolerance.type == QAUtils.PERCENT){
            tol = QAUtils.convert_tol_to_abs(measured.reference,measured.tolerance);
        }
        series.act_low.push([date,tol.act_low]);
        series.tol_low.push([date,tol.tol_low]);
        series.tol_high.push([date,tol.tol_high]);
        series.act_high.push([date,tol.act_high]);
    });
    return series;
}
/*************************************************************************/
//Take data from api and set up task_list_item data
function process_data(data){
    var processed = {};
    $(data.objects).each(function(item_idx,task_list_item_data){
        var name = task_list_item_data.name;
        processed[name] = {};
        $(task_list_item_data.units).each(function(unit_idx,unit){
            processed[name][unit.number] = convert(unit.data);
        });

    });
    return processed;
}
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
//get all filters for data request
function get_filters(){
    var short_names = get_checked("#task-list-item-filter");
    var units = get_checked("#units-filter");
    return {
        short_names: $(short_names).get().join(','),
        units: $(units).get().join(','),
        from_date: $("#from-date").val(),
        to_date: $("#to-date").val()
    };
}
function next_color(){
    var next = -1;
    var get_next_color = function(){
        next+=1;
         return next;
    };
    return get_next_color;
}
function plot_task_list_item_curves(name,data,color_generator){
    $.each(data,function(unit,series){
        var create_name = function(type){return name+'_unit'+unit+"_"+type;}


        $.each(["act_low","tol_low","tol_high","act_high"],function(idx,type){

            var opts = {
                id: create_name(type),
                data:series[type],
                lines: {show:true, lineWidth:0}
            }

            if (idx>0) {
                opts["fillBetween"] = main_graph_series[main_graph_series.length-1].id;
                opts.lines["fill"] = 0.2;
                if ((idx===1 ) || (idx===3)){
                    opts["color"] = QAUtils.TOL_COLOR;
                }else{
                    opts["color"] = QAUtils.OK_COLOR;
                }
            }

            main_graph_series.push(opts);
        });
        var color = color_generator();
        var val_name = create_name("values");
        main_graph_series.push({
            id: val_name,
            label: name+"- Unit"+unit,
            data:series.values,
            points: {show:true, fill:0.2},
            hoverable: true,
            color:color
        });

        var ref_name = create_name("references");
        main_graph_series.push({
            id: ref_name,
            data:series.references,
            lines: {show:true,lineWidth:1},
            points:{show:false},//true,symbol:dash,radius:5},
            color:color,
            shadowSize:0
        });

    });
}
/*************************************************************************/
//Do a full update of the chart
//Currently everything is re-requested and re-drawn which isn't very efficient
function update_chart(){

    var filters = get_filters();
    if ((filters.units === "") || (filters.short_names === "")){
        return;
    }
    var color_gen = next_color();
    QAUtils.task_list_item_values(filters, function(data){
        task_list_data = process_data(data);
        main_graph_series = [];

        $.each(task_list_data,function(name,data){
            plot_task_list_item_curves(name,data,color_gen)
        });

        main_graph.setData(main_graph_series);
        main_graph.setupGrid();
        main_graph.draw();
    });

}

/**********************************************************************/
//sets up all avaialable filters by querying server to find avaialable values
function setup_filters(){

    //list of filter resources
    var filters = [
        {
            container:"#units-filter",
            resource_name:"unit",
            display_property:"name",
            value_property:"number",
            check_all:true
        },
        {
            container:"#task-list-filter",
            resource_name:"tasklist",
            display_property:"name",
            value_property:"slug",
            check_all:false
        },
        {
            container:"#task-list-item-filter",
            resource_name:"tasklistitem",
            display_property:"name",
            value_property:"short_name",
            check_all:false
        }
    ];

    $(filters).each(function(idx,filter){
        $(filter.container).html('<i class="icon-time"></i><em>Loading...</em>');

        /*set up task list item filters */
        QAUtils.get_resources(filter.resource_name,function(resources){
            var options = "";
            $(resources.objects).each(function(index,resource){
                var display = resource[filter.display_property];
                var value = resource[filter.value_property];
                var checked = filter.check_all ? 'checked="checked"' : "";
                var option = '<label class="checkbox"><input type="checkbox" ' + checked + ' value="' + value + '">' + display + '</input></label>';
                options += option;
            });

            $(filter.container).html(options);
        });

    });


}
/*********************************************************************/
//Interactions with plot
function show_tooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
        position: 'absolute',
        display: 'none',
        top: y + 5,
        left: x + 5,
        border: '1px solid #fdd',
        padding: '2px',
        'background-color': '#fee',
        opacity: 0.80
    }).appendTo("body").fadeIn(200);
}

function on_hover(event, pos, item) {

    if (item) {
        if (previous_point != item.dataIndex) {

            previous_point = item.dataIndex;

            $("#tooltip").remove();
            var x = new Date(item.datapoint[0]);
            var y = item.datapoint[1].toFixed(2);

            show_tooltip(item.pageX, item.pageY, item.series.label + " of " + x + " = " + y);
        }
    }
    else {
        $("#tooltip").remove();
        previousPoint = null;
    }
}


/**************************************************************************/
$(document).ready(function(){

    //set up main chart and options
    main_graph = $.plot(
        $("#trend-chart"),
        main_graph_series,
        {
            xaxis:{
                mode: "time",
                timeformat: "%d %b %y",
                autoscaleMargin:0.001
            },
            legend:{
                container:"#chart-legend"
            },
            grid:{
                hoverable:true
            }
        }
    )


    $("#trend-chart").bind("plothover", on_hover);

    setup_filters();

    $(".checkbox-container").change(update_chart);
    $(".collapse").collapse({selector:true,toggle:true});
    $("#task-list-item-collapse").collapse("show");

    $(".nav-tabs a:first").tab('show');

    $(".date").datepicker().on('changeDate',update_chart);



    $(window).resize = function(){
        main_graph.resize();
    }
});