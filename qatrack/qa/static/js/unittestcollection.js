
/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_collection_tables(units, frequencies){

    var unit_names = _.pluck(units[0].objects,"name");
    var freq_names = _.pluck(frequencies[0].objects,"name");

    var cols = [
        {bSortable:false},
        null,//{bSortable:false},
        {bSortable:false},
        null, //Unit
        null, //Freq
        null,//assigned to
        null, //date completed
        {bSortable:false},
        {bSortable:false}
    ];

    var filter_cols = [
        null, //action
        {type: "text" }, // Test list name
        {type: "text" }, //due date
        {type: "select",values:unit_names }, // unit
        {type: "select",values:freq_names }, //Freq
        {type: "select"},//assigned to
        {type: "text" }, //date completed
        null, //pass/fail status
        null //review-status
    ];

    $(".test-collection-table").dataTable({
        bProcessing:true,
        bServerSide:true,
        sAjaxSource:"./data/",
        sAjaxDataProp:"data",
        bAutoWidth:false,
        fnAdjustColumnSizing:false,
        bFilter:true,
        bPaginate:true,
        iDisplayLength:50,
        aaSorting:[[4,"desc"],[1,"asc"]],
//        aaSorting:[[1,"asc"],[4,"desc"]],
        aoColumns:cols,
        sDom: '<"row-fluid"<"span6"ir><"span6"p>>t<"row-fluid"<"span12"lp>>',
        sPaginationType: "bootstrap"

    }).columnFilter({
        sPlaceHolder: "head:after",
        aoColumns: filter_cols,
        iFilteringDelay:250
    });

    $(".test-collection-table").find("select, input").addClass("input-small");
}

/**************************************************************************/
$(document).ready(function(){

    $.when(
        $.getJSON("/qa/api/v1/unit/?format=json"),
        $.getJSON("/qa/api/v1/frequency/?format=json")
    ).then(init_test_collection_tables);

});

