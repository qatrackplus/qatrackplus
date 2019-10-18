
require(['jquery', 'moment', 'autosize', 'daterangepicker', 'select2', 'felter', 'sl_utils', 'inputmask', 'json2'], function ($, moment, autosize) {

    var date_range_locale = {
        "format": siteConfig.DATERANGEPICKER_DATE_FMT,
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

        $daterange.val(ranges['This Year'][0].format(siteConfig.MOMENT_DATE_FMT) + ' - ' + ranges['This Year'][1].format(siteConfig.MOMENT_DATE_FMT));

        $daterange.daterangepicker({
            autoUpdateInput: false,
            "ranges": ranges,
            "showDropdowns": true,
            "linkedCalendars": false,
            "locale": date_range_locale
        }, function (start_date, end_date) {
            $(this.element).val(start_date.format(siteConfig.MOMENT_DATE_FMT) + ' - ' + end_date.format(siteConfig.MOMENT_DATE_FMT));
        }).on('apply.daterangepicker', function (ev, picker) {
            $(picker.element).val(picker.startDate.format(siteConfig.MOMENT_DATE_FMT) + ' - ' + picker.endDate.format(siteConfig.MOMENT_DATE_FMT));
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

    });

});
