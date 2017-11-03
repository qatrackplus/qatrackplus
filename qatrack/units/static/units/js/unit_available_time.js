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


        var $date_changed = $('#id_date_changed'),
            $unit_avail_time_go = $('#unit_avail_time_go'),
            $avail_time_form = $('#avail_time_form'),
            $units_avail = $('#id_units'),
            $units = $('#units'),
            $units_errors = $('#units-errors'),
            $date_errors = $('#date-errors'),
            $hours_errors = $('#hours-errors'),
            $avail_time_edit_form = $('#avail_time_edit_form'),
            $units_edit_avail = $('#id_edit_units'),
            $date = $('#id_date'),
            $unit_avail_time_edit_go = $('#unit_avail_time_edit_go');

        $units.felter({
            mainDivClass: 'col-md-12 form-control',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            // choiceDivClass: 'row',
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

        $('.duration').inputmask('99:99', {numericInput: true, removeMaskOnSubmit: true});

        $date_changed.daterangepicker({
            singleDatePicker: true,
            autoClose: true,
            autoApply: true,
            keyboardNavigation: false,
            locale: {"format": "DD-MM-YYYY"}
        });

        $date.daterangepicker({
            singleDatePicker: true,
            autoClose: true,
            autoApply: true,
            keyboardNavigation: false,
            locale: {"format": "DD-MM-YYYY"}
        });

        function update_hidden_units() {
            var units_selected = $units.val();
            $.each($units_avail.find('option'), function(i, v){
                $units_avail.find('option[value="' + $(this).val() + '"]').prop("selected", $.inArray($(this).val(), units_selected) !== -1);
            });
            $.each($units_edit_avail.find('option'), function(i, v){
                $units_edit_avail.find('option[value="' + $(this).val() + '"]').prop("selected", $.inArray($(this).val(), units_selected) !== -1);
            });
        }
        update_hidden_units();

        $units.on('change', function() {
            update_hidden_units();
        });

        $unit_avail_time_go.click(function() {
            $('.weekday-duration').addClass('no-error');
            $('.has-error').removeClass('has-error');
            $hours_errors.html('');
            $.ajax({
                url: QAURLs.HANDLE_UNIT_AVAILABLE_TIME,
                data: $avail_time_form.serialize(),
                type: 'POST',
                success: function(res) {
                    if (res.errors) {
                        place_errors(res.errors);
                    }
                }
            })
        });

        $unit_avail_time_edit_go.click(function() {
            $('.has-error').removeClass('has-error');
            $.ajax({
                url: QAURLs.HANDLE_UNIT_AVAILABLE_TIME_EDIT,
                data: $avail_time_edit_form.serialize(),
                type: 'POST',
                success: function(res) {
                    if (res.errors) {
                        place_errors(res.errors);
                    }
                }
            })
        });

        function place_errors(errors) {

            var hours_errors = [];

            $('.ajax-errors').html('');

            $.each(errors, function(k, v) {

                var $elem = $('#id_' + k);
                if (k.indexOf('hours') !== -1 && k !== 'hours') {
                    $hours_errors.parent().addClass('has-error');
                    $elem.removeClass('no-error');

                    $.each(v, function(k, v) {
                        if (hours_errors.indexOf('- ' + v) === -1) {
                            hours_errors.push('- ' + v);
                        }
                    });

                } else if (k === 'units') {
                    $.each(v, function(i, v) {
                        $units_errors.append('<div>- ' + v + '</div>');
                    });
                    $units_errors.parent().addClass('has-error');
                } else {

                    var $err_div = $elem.parent().siblings('.ajax-errors');
                    $.each(v, function(i, v) {
                        $err_div.append('<div>- ' + v + '</div>');
                    });
                    $err_div.parent().addClass('has-error');
                }
            });

            $.each(hours_errors, function(i, v) {
                $hours_errors.append('<div>' + v + '</div>');
            })
        }

    });
});