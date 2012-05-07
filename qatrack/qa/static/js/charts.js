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
    var units = get_checked("#unit-filter");
    var review_status = get_checked("#review-status-filter");
    return {
        short_names: $(short_names).get().join(','),
        units: $(units).get().join(','),
        from_date: $("#from-date").val(),
        to_date: $("#to-date").val(),
        review_status: $(review_status).get().join(',')
    };
}
/*************************************************************************/
//Convert a collection of plot values, refs, tols etc to a series that flot can show
function convert_to_flot_series(idx,collection){

    var series = [];

    var create_name = function(type){return collection.short_name+'_unit'+collection.unit+"_"+type;}

    var dates = $.map(collection.data.dates,QAUtils.parse_iso8601_date);

    var show_tolerances = $("#show-tolerances").is(":checked");
    var show_references = $("#show-references").is(":checked");
    var show_lines = $("#show-lines").is(":checked");
    if(show_tolerances){
        var tolerances = {act_low:[], tol_low:[], tol_high:[], act_high:[]};
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
                lines: {show:true, lineWidth:0,steps:true}
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
    }

    var val_name = create_name("values");
    series.push({
        id: val_name,
        label: collection.name+"- Unit"+collection.unit,
        data:QAUtils.zip(dates,collection.data.values),
        points: {show:true, fill:0.2},
        lines: {show:show_lines,lineWidth:1},
        hoverable: true,
        color:idx
    });

    if (show_references){
        var ref_name = create_name("references");
        series.push({
            id: ref_name,
            data:QAUtils.zip(dates,collection.data.references),
            lines: {show:true,lineWidth:2,steps:true},
            points:{show:false},//true,symbol:dash,radius:5},
            color:idx,
            shadowSize:0
        });
    }
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
function setup_filters(on_complete){

    //list of filter resources
    var filters = [
        {
            container:"#unit-filter",
            resource_name:"unit",
            display_property:"name",
            value_property:"number",
            to_check : ["all"]
        },
        {
            container:"#task-list-filter",
            resource_name:"tasklist",
            display_property:"name",
            value_property:"slug",
            to_check : ["all"]
        },
        {
            container:"#frequency-filter",
            resource_name:"frequency",
            display_property:"display",
            value_property:"value",
            to_check : ["all"]
        },
        {
            container:"#category-filter",
            resource_name:"category",
            display_property:"name",
            value_property:"slug",
            to_check : ["all"]

        },
        {
            container:"#review-status-filter",
            resource_name:"status",
            display_property:"display",
            value_property:"value",
            check_all:false,
            to_check:[QAUtils.APPROVED, QAUtils.UNREVIEWED]
        }


    ];
    var ajax_counter =0;
    $(filters).each(function(idx,filter){
        $(filter.container).html('<i class="icon-time"></i><em>Loading...</em>');

        /*set up task list item filters */
        QAUtils.get_resources(filter.resource_name,function(resources){
            var options = "";
            $(resources.objects).each(function(index,resource){
                var display = resource[filter.display_property];
                var value = resource[filter.value_property];

                if (
                    (filter.to_check.length >= 0) && (
                        ($.inArray(value,filter.to_check)>=0) ||
                        (filter.to_check[0] === "all")
                    )
                ){
                    var checked = 'checked="checked"';
                }else{
                    var checked = filter.check_all ? 'checked="checked"' : "";
                }
                options += '<label class="checkbox"><input type="checkbox" ' + checked + ' value="' + value + '">' + display + '</input></label>';
            });

            $(filter.container).html(options);

            //signal when we've completed all async calls
            ajax_counter += 1;
            if (ajax_counter >= filters.length){
                on_complete(ajax_counter,filters.length);
            }

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
function populate_task_list_members(on_complete){

    QAUtils.get_resources("tasklist",function(task_lists){
        $.each(task_lists.objects,function(idx,task_list){
            task_list_members[task_list.slug] = task_list;
        });
        //signal we've finished all our tasks
        var counter=1, ntasks=1
        on_complete(counter,ntasks);
    })
}
/*************************************************************************/
//filter the task list items based on user choices
function filter_task_list_items(){
    var task_lists = get_checked("#task-list-filter");
    var task_list_items = [];
    var categories = get_checked("#category-filter");
    var frequencies = get_checked("#frequency-filter");

    var options = "";
    $.each(task_list_members,function(name,task_list){

        if ($.inArray(name,task_lists)>=0){
            $.each(task_list.task_list_items,function(idx,item){
                if (
                    ($.inArray(item.category.slug,categories)>=0) &&
                    (QAUtils.intersection(frequencies,task_list.frequencies).length>0)
                ){

                    task_list_items.push(item);
                    options += '<label class="checkbox"><input type="checkbox"' + ' value="' + item.short_name + '">' + item.name + '</input></label>';
                }
            });
        }

    });
    $("#task-list-item-filter").html(options);

}
/**************************************************************************/
//set initial options based on url hash
function set_options_from_url(){
    var options = QAUtils.options_from_url_hash(document.location.hash);

    $.each(options,function(key,value){
        switch(key){
            case  "task_list_item" :
                $("#task-list-item-filter input").attr("checked",false);
                $("#task-list-item-filter input[value="+value+"]").attr("checked","checked");
            break;
            case "unit":
                $("#unit-filter input").attr("checked",false);
                $("#unit-filter input[value="+value+"]").attr("checked","checked");
                break;
            default:
                break;
        }

    });
    update_chart();
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


    //filters are populated asynchronously so we need to wait until that's done
    //before final initialization
    var after_init = function(){
        filter_task_list_items();
        set_options_from_url();
    }
    var async_finished = 0;
    var total_async_tasks = 2;
    var update_count = function(){
        async_finished += 1;
        if (async_finished >= total_async_tasks){
            after_init();
        }
    };

    //grab all the task list items, tasks, units etc from server
    setup_filters(update_count);
    populate_task_list_members(update_count);

    //update chart when a data filter changes
    $("#unit-filter, #task-list-item-filter, #review-status-filter").change(update_chart);

    $("#task-list-filter, #category-filter, #frequency-filter").change(filter_task_list_items);

    $(".chart-options").change(update_chart);

    $(".date").datepicker().on('changeDate',update_chart);

    $(".collapse").collapse({selector:true,toggle:true});
    $("#task-list-item-collapse").collapse("show");



});