
/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_collection_tables(units, frequencies, groups){
    /*pagination_info is array like [total_records, num_filtered_records]*/
    var unit_names = _.pluck(units[0].objects,"name");
    var freq_names = _.map(frequencies[0].objects,function(e){return {value:e.id,label:e.name};});
    freq_names.push({value:null,label:"Ad hoc"});
    var group_names = _.pluck(groups[0].objects,"name");

    var pagination = [$("#filtered_records").val(),$("#total_records").val()];

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
        null, //due date
        {type: "select",values:unit_names }, // unit
        {type: "select",values:freq_names }, //Freq
        {type: "select",values:group_names }, //assigned to
        null, //date completed
        null, //pass/fail status
        null //review-status
    ];



    $(".test-collection-table").dataTable({
        bProcessing:true,
        bServerSide:true,
        sAjaxSource:"./",
        sAjaxDataProp:"data",
        bAutoWidth:false,
        fnAdjustColumnSizing:false,
        fnPreDrawCallback:function(){$("#pagination-placeholder").remove()},
        bFilter:true,
        bPaginate:true,
        bStateSave:true, /*remember filter/sort state on page load*/
        iDisplayLength:50,
        iDeferLoading:pagination,
        aaSorting:[[3,"asc"],[4,"desc"],[1,"asc"]],
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
        $.getJSON(QAUtils.API_URL+"unit/?format=json"),
        $.getJSON(QAUtils.API_URL+"frequency/?format=json"),
        $.getJSON(QAUtils.API_URL+"group/?format=json")
    ).then(init_test_collection_tables);

});

