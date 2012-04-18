/************************************************************************/
//data returned from the API has dates in ISO string format and must be converted
//to javascript dates
function convert_timestamps(data){
    var converted = [];
    $(data).each(function(idx,point){
        converted.push([Date.parse(point[0]),point[1]]);
    });
    return converted;

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
        units: $(units).get().join(',')
    };
}

/*************************************************************************/
//Do a full update of the chart
//Currently everything is re-requested and re-drawn which isn't very efficient
function update_chart(){

    var filters = get_filters();
    if ((filters.units === "") || (filters.short_names === "")){
        return;
    }
    QAUtils.task_list_item_values(filters, function(data){
        main_graph_data = [];
        $(data.objects).each(function(idx,task_list_items){
            $(task_list_items.units).each(function(idx,unit){
                if (unit.data.length > 0){

                    main_graph_data.push({
                        label:task_list_items.name + "- Unit" + unit.number,
                        data:convert_timestamps(unit.data),
                        points: {show:true},
                        lines: {show:true},
                        hoverable: true
                    });
                }
            });
        });

        main_graph.setData(main_graph_data);
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
            value_property:"number"
        },
        {
            container:"#task-list-filter",
            resource_name:"tasklist",
            display_property:"name",
            value_property:"slug"
        },
        {
            container:"#task-list-item-filter",
            resource_name:"tasklistitem",
            display_property:"name",
            value_property:"short_name"
        }
    ];

    $(filters).each(function(idx,element){
        /*set up task list item filters */
        QAUtils.get_resources(element.resource_name,function(resources){
            var options = "";
            $(resources.objects).each(function(index,resource){
                var display = resource[element.display_property];
                var value = resource[element.value_property];
                options += '<label class="checkbox"><input type="checkbox" value="' + value + '">' + display + '</input></label>';
            });

            $(element.container).html(options);
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

var previous_point = null;
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
    main_graph_data = [[[]]];

    //set up main chart and options
    main_graph = $.plot(
        $("#trend-chart"),
        main_graph_data,
        {
            xaxis:{
                mode: "time",
                timeformat: "%d/%m/%y"
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
});