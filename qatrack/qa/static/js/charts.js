var task_list_data = {};
var main_graph_series = [{}];
var main_graph;
var previous_point = null;
var task_list_members = {}; //short names of task list items belonging to task lists


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
/*************************************************************************/
//Convert a collection of plot values, refs, tols etc to a series that flot can show
function convert_to_flot_series(idx,collection){

    var series = [];

    var create_name = function(type){return collection.short_name+'_unit'+collection.unit+"_"+type;}

    var dates = $.map(collection.data.dates,Date.parse);

    var tolerances = {act_low:[], tol_low:[], tol_high:[], act_high:[]}
    $.each(collection.data.tolerances,function(idx,tol){
        var ref = collection.data.references[idx];
        var date = dates[idx];

        if (tol.type === QAUtils.PERCENT){
            tol = QAUtils.convert_tol_to_abs(ref,tol);
        }

        $.each(["act_low","tol_low","tol_high","act_high"],function(idx,type){
            tolerances[type].push([date,tol[type]]);
        });
    });

    $.each(["act_low","tol_low","tol_high","act_high"],function(idx,type){
        var vals = [];

        var opts = {
            id: create_name(type),
            data:tolerances[type],
            lines: {show:true, lineWidth:0}
        }

        if (idx>0) {
            opts["fillBetween"] = series[series.length-1].id;
            opts.lines["fill"] = 0.2;
            if ((idx===1 ) || (idx===3)){
                opts["color"] = QAUtils.TOL_COLOR;
            }else{
                opts["color"] = QAUtils.OK_COLOR;
            }
        }

        series.push(opts);
    });


    var val_name = create_name("values");
    series.push({
        id: val_name,
        label: collection.name+"- Unit"+collection.unit,
        data:QAUtils.zip(dates,collection.data.values),
        points: {show:true, fill:0.2},
        hoverable: true,
        color:idx
    });

    var ref_name = create_name("references");
    series.push({
        id: ref_name,
        data:QAUtils.zip(dates,collection.data.references),
        lines: {show:true,lineWidth:1},
        points:{show:false},//true,symbol:dash,radius:5},
        color:idx,
        shadowSize:0
    });

    return series;
}
/*************************************************************************/
//Do a full update of the chart
//Currently everything is re-requested and re-drawn which isn't very efficient
function update_chart(){

    var filters = get_filters();
    if ((filters.units === "") || (filters.short_names === "")){
        return;
    }
    QAUtils.task_list_item_values(filters, function(results_data){

        main_graph_series = [];

        $.each(results_data.objects,function(idx,collection){
            var collection_series = convert_to_flot_series(idx,collection);
            var ii;
            for (ii=0; ii<collection_series.length;ii++){
                main_graph_series.push(collection_series[ii]);
            }
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
            check_all:true
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

/************************************************************************/
//populate global list of task list memberships
function populate_task_list_members(){

    QAUtils.get_resources("tasklist",function(task_lists){
        $.each(task_lists.objects,function(idx,task_list){
            task_list_members[task_list.slug] = [];
            $.each(task_list.task_list_items,function(item_idx,item){
                task_list_members[task_list.slug].push(item.short_name)
            });
        });
    })
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
    $(window).resize = function(){main_graph.resize();}
    $("#trend-chart").bind("plothover", on_hover);

    //grab all the task list items, tasks, units etc from server
    setup_filters();

    populate_task_list_members();

    //update chart when a filter changes
    $("#units-filter, #task-list-item-filter").change(update_chart);
    $(".date").datepicker().on('changeDate',update_chart);

    $(".collapse").collapse({selector:true,toggle:true});
    $("#task-list-item-collapse").collapse("show");


});