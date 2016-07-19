/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_list_instance_tables(units, frequencies){

    var unit_names = _.map(units[0].objects,"name");
    var freq_names = _.map(frequencies[0].objects,function(e){return {value:e.id,label:e.name};});
    freq_names.push({value:null,label:"Ad hoc"});

    var pagination = [$("#filtered_records").val(),$("#total_records").val()];

    var cols = [
        {bSortable:false},
        null,
        null,
        null,
        null,
        null,
        {bSortable:false},
        {bSortable:false}
    ];

    var filter_cols = [
        null, //action
        {type: "select",values:unit_names }, // unit
        {type: "select",values:freq_names }, //Freq
        {type: "text"}, //Test List
        null, //work completed
        {type: "text"},//user
        null,
        null //pass/fail status
    ];

    $("#testlistinstance-table").dataTable({
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
        aaSorting:[[1,"asc"],[4,"desc"]],
        aoColumns:cols,
        sDom: '<"row-fluid"<"span6"ir><"span6"p>>t<"row-fluid"<"span12"lp>>',
        sPaginationType: "bootstrap"

    }).columnFilter({
        sPlaceHolder: "head:after",
        aoColumns: filter_cols,
        iFilteringDelay:250
    });

    $("#testlistinstance-table").find("select, input").addClass("input-small");
}

/**************************************************************************/
$(document).ready(function(){

    $.when(
        $.getJSON(QAURLs.API_URL+"unit/?format=json&limit=0"),
        $.getJSON(QAURLs.API_URL+"frequency/?format=json&limit=0")
    ).then(init_test_list_instance_tables);

    $(function () {
        $('[data-toggle="popover"]').popover()
    });

    var categories = $('#category-list > li > a.has-icheck > div > .check-category');
    var showall = $('#category-showall');

    showall.on('ifChecked ifUnchecked', function(e) {
        if (e.type == 'ifChecked') {
            categories.iCheck('check');
        } else {
            categories.iCheck('uncheck');
        }
    });

    categories.on('ifChanged', function(e){
        if(categories.filter(':checked').length == categories.length) {
            showall.prop('checked', true);
        } else {
            showall.prop('checked', false);
        }
        showall.iCheck('update');
        console.log($('.content-wrapper'));
    });

    $('#work-time-range').daterangepicker({
        "timePicker": true,
        "timePickerIncrement": 5,
        "autoApply": true,
        "locale": {
            "format": "DD/MM/YYYY h:mm",
            "separator": " - ",
            "applyLabel": "Apply",
            "cancelLabel": "Cancel",
            "fromLabel": "From",
            "toLabel": "To",
            "customRangeLabel": "Custom",
            "weekLabel": "W",
            "daysOfWeek": [
                "Su",
                "Mo",
                "Tu",
                "We",
                "Th",
                "Fr",
                "Sa"
            ],
            "monthNames": [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December"
            ],
            "firstDay": 1
        },
        "timePicker24Hour": true,
        "startDate": "07/08/2016",
        "endDate": "07/14/2016",
        "buttonClasses": "btn btn-flat"
    }, function(start, end, label) {
        console.log("New date range selected: ' + start.format('YYYY-MM-DD') + ' to ' + end.format('YYYY-MM-DD') + ' (predefined range: ' + label + ')");
    });

    var work_time_range_input = $("#work-time-range");
    $('#work-time-picker-container').click(function() {
        var rect = this.getBoundingClientRect();
        $(work_time_range_input).click();
        $('.daterangepicker.dropdown-menu.show-calendar').css({'left': rect.left, 'top': rect.top + 65});
    });

    $(work_time_range_input).change(function() {
        console.log($(this).val());
        var from = $(this).val().split(' - ')[0];
        var to = $(this).val().split(' - ')[1];
        console.log(from, to);
        // $("#alternate").html($("#datepicker").val());
    });
});

