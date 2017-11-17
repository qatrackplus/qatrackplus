
require(['jquery', 'moment', 'autosize', 'daterangepicker', 'select2', 'felter', 'sl_utils', 'inputmask', 'json2'], function ($, moment, autosize) {

    var date_range_locale = {
        "format": "DD MMM YYYY",
        "separator": " - ",
        "applyLabel": "Apply",
        "cancelLabel": "Clear",
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
    };

    var ranges = {
        "Last 7 Days": [
            moment().subtract(7, 'days'),
            moment()
        ],
        "Last 30 Days": [
            moment().subtract(30, 'days'),
            moment()
        ],
        "Last 365 Days": [
            moment().subtract(365, 'days'),
            moment()
        ],
        "This Week": [
            moment().startOf('week'),
            moment().endOf('week')
        ],
        "This Month": [
            moment().startOf('month'),
            moment().endOf('month')
        ],
        "This Year": [
            moment().startOf('year'),
            moment().endOf('year')
        ],
        "Last Week": [
            moment().subtract(1, 'weeks').startOf('week'),
            moment().subtract(1, 'weeks').endOf('week')
        ],
        "Last Month": [
            moment().subtract(1, 'months').startOf('month'),
            moment().subtract(1, 'months').endOf('month')
        ],
        "Last Year": [
            moment().subtract(1, 'years').startOf('year'),
            moment().subtract(1, 'years').endOf('year')
        ]
    };

    $(document).ready(function () {

        // Part cost ////////////////////////////////////////////

        var $daterange = $('#date_range_selector'),
            $service_areas = $('#service_areas'),
            $units = $('#units'),
            $service_types = $('#service_types'),
            $go_units_parts = $('#go_units_parts'),
            $form = $('#unit_area_type');

        $daterange.val(ranges['This Year'][0].format('DD MMM YYYY') + ' - ' + ranges['This Year'][1].format('DD MMM YYYY'));

        $daterange.daterangepicker({
            autoUpdateInput: false,
            "ranges": ranges,
            "showDropdowns": true,
            "linkedCalendars": false,
            "locale": date_range_locale
        }, function (start_date, end_date) {
            $(this.element).val(start_date.format('DD MMM YYYY') + ' - ' + end_date.format('DD MMM YYYY'));
        }).on('apply.daterangepicker', function (ev, picker) {
            $(picker.element).val(picker.startDate.format('DD MMM YYYY') + ' - ' + picker.endDate.format('DD MMM YYYY'));
            if (!picker.startDate.isSame(picker.oldStartDate) || !picker.endDate.isSame(picker.oldEndDate)) {
                $(this).trigger('keyup');
            }
        }).on('cancel.daterangepicker', function (ev, picker) {
            $(this).val('');
            $(this).trigger('keyup');
            picker.startDate = moment();
            picker.endDate = moment();
        });

        function generate_sa_result(res) {
            return res.text;
        }
        function generate_sa_selection(res, container) {
            var $label = $('<span>' + res.text + '</span>');
            return $label;
        }
        $service_areas.felter({
            mainDivClass: 'col-md-4',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            // choiceDivClass: 'row',
            label: 'Service Areas',
            initially_displayed: true,
            selectAll: true,
            selectNone: true,
            height: 350,
            slimscroll: true
        });

        $units.felter({
            mainDivClass: 'col-md-4',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            label: 'Units',
            initially_displayed: true,
            selectAll: true,
            selectNone: true,
            height: 350,
            slimscroll: true,
            filters: {
                showInactiveUnits: {
                    selected: false,
                    run_filter_when_selected: false,   // No, run filter when not selected
                    label: 'Show Inactive Units',
                    filter: function(obj_data) {
                        return $(obj_data.$option).attr('data-active') === 'True';
                    }
                }
            }
        });

        $service_types.felter({
            mainDivClass: 'col-md-4',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            // choiceDivClass: 'row',
            label: 'Service Types',
            initially_displayed: true,
            selectAll: true,
            selectNone: true,
            height: 350,
            slimscroll: true
        });

        // $go_units_parts.click(function() {
            // $go_units_parts.prop('disabled', true).text('Working...');
            // $.ajax({
            //     data: {
            //         date_range: $daterange.val(),
            //         units: $units.val().join(','),
            //         service_areas: $service_areas.val().join(','),
            //         service_types: $service_types.val().join(',')
            //     },
            //     url: QAURLs.GO_UNITS_PARTS_COST,
            //     success: function(res) {
            //         var name = 'qatrack_parts_units_cost.csv';
            //         var csvContent = "data:text/csv;charset=utf-8,";
            //         csvContent += res;
            //         var encodedUri = encodeURI(csvContent);
            //         var link = document.createElement("a");
            //         link.setAttribute("href", encodedUri);
            //         link.setAttribute("download", name);
            //         document.body.appendChild(link); // Required for FF
            //         link.click();
            //         $go_units_parts.prop('disabled', false).text('Generate Summary Report');
            //     }
            // })
        // });

    });

});