var supress_initial_reload = true;
var column_sort_keys = [
    null,
    "unit_test_collection__unit__name",
    "unit_test_collection__frequency__nominal_interval",
    "test_list__name",
    "work_completed",
    "created_by__username",
    null,
    null
];

/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_list_instance_tables(units, frequencies){

    var unit_names = _.pluck(units[0].objects,"name");
    var freq_names = _.pluck(frequencies[0].objects,"name");

    var cols = [
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null
    ];

    var filter_cols = [
        null, //action
        {type: "select",values:unit_names }, // unit
        {type: "select",values:freq_names }, //Freq
        {type: "text"}, //Test List
        {type: "text"}, //work completed
        {type: "text"},//user
        null,
        null //pass/fail status
    ];

    $("#testlistinstance-table").dataTable({
        bProcessing:true,
        bServerSide:true,
        sAjaxSource:'../data-tables/',
        sAjaxDataProp:"data",
        bAutoWidth:false,
        fnAdjustColumnSizing:false,
        bFilter:true,
        bPaginate:true,
        aoColumns:cols,
        sPaginationType: "bootstrap"

    }).columnFilter({
        sPlaceHolder: "head:after",
        aoColumns: filter_cols
    }).find("select, input").addClass("input-small");

}

function on_table_sort(){

    if (supress_initial_reload){
        supress_initial_reload = false;
        return;
    }

    var sorts = this.fnSettings().aaSorting;
    var qs = "?";
    var refresh_required = false;

    _.each(sorts,function(sort_info){

    var col = sort_info[0];
    var dir = sort_info[1];
    var key = column_sort_keys[col];

    var ordering;

    if (!_.isNull(key)){

    refresh_required = true;

    if (dir === "desc"){
        key = "-"+key;
    }

    qs += "order="+key+"&";
}
});

    if (refresh_required){
        var url = document.location.href.replace(document.location.search,"")+qs;
        document.location.replace(url);
    }


}

function get_units(){

}
/**************************************************************************/
$(document).ready(function(){

    $.when(
        $.getJSON("/qa/api/v1/unit/?format=json"),
        $.getJSON("/qa/api/v1/frequency/?format=json")
    ).then(init_test_list_instance_tables);

});

