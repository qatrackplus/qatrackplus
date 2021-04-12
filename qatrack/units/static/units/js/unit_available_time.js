require(['jquery', 'moment_timezone', 'd3', 'flatpickr', 'daterangepicker', 'select2', 'felter', 'sl_utils', 'inputmask', 'json2'], function ($, moment, d3) {

    var tz = moment.tz.guess();

    var _ctrl_pressed = false,
        _shift_pressed = false;

    $(document).keydown(function(event){
        if (event.which == '17')
            _ctrl_pressed = true;
        else if (event.which == '16')
            _shift_pressed = true;
    });

    $(document).keyup(function(event){
        if (event.which == '17')
            _ctrl_pressed = false;
        else if (event.which == '16')
            _shift_pressed = false;
    });

    var date_range_locale = {
        "format": siteConfig.MOMENT_DATE_FMT,
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

        var $units = $('#units'),
            $year = $('#id_year_select'),
            $month = $('#id_month_select'),
            $next_month = $('#next-month'),
            $prev_month = $('#prev-month'),
            $svg_container = $('#svg-container'),
            $open_edit_modal = $('#open_edit_modal'),
            $open_uat_modal = $('#open_uat_modal'),
            $open_delete_modal = $('#open_delete_modal'),
            $insert_change_uat = $('#insert_change_uat'),
            $insert_change_edit = $('#insert_change_edit'),
            $delete_go = $('#delete_go'),
            $delete_cancel = $('#delete_cancel'),
            $name_input = $('#name_input'),
            $edit_input = $('#edit_input'),
            $effective_date = $('#effective_date'),
            $hours_sunday = $('#id_hours_sunday'),
            $hours_monday = $('#id_hours_monday'),
            $hours_tuesday = $('#id_hours_tuesday'),
            $hours_wednesday = $('#id_hours_wednesday'),
            $hours_thursday = $('#id_hours_thursday'),
            $hours_friday = $('#id_hours_friday'),
            $hours_saturday = $('#id_hours_saturday'),
            $num_days_selected = $('.num-days-selected');

        var unit_available_time_data = {},
            day_by_day_unit_hours,
            selected_units = [],
            selected_days = [],
            recent_day_selected,
            current_day = moment(),
            day_view = current_day.clone(),
            first_day_displayed,
            last_day_displayed,
            days = [];

        var chart_height = 650,
            chart_width = $svg_container.width() - 15;

        var color_scale = d3.scaleOrdinal(d3['schemeCategory20']);
        var unit_colours = {};
        $.each($units.find('option'), function(i, v) {
            unit_colours[$(v).val()] = color_scale(i);
        });

        $effective_date.flatpickr({
            allowInput: true,
            dateFormat: 'd M Y'
        });

        $year.select2({
            minimumResultsForSearch: 50,
            width: '100px'
        }).change(function() {
            $month.change();
        });

        $month.select2({
            minimumResultsForSearch: 15,
            width: '120px'
        }).change(function() {
            day_by_day_unit_hours = null;
            day_view.month($(this).val());
            day_view.year($year.val());

            set_calendar_days();
        });

        $next_month.click(function() {
            if ($month.val() == 11) {
                $year.val(parseInt($year.val()) + 1);
                $month.val('0');
                $year.change();
            } else {
                $month.val(parseInt($month.val()) + 1);
                $month.change();
            }
        });

        $prev_month.click(function() {
            if ($month.val() == 0) {
                $year.val(parseInt($year.val()) - 1);
                $month.val('11');
                $year.change();
            } else {
                $month.val(parseInt($month.val()) - 1);
                $month.change();
            }
        });

        $insert_change_edit.click(function() {

            $('body').addClass('loading');
            $('#available_edits_modal').modal('hide');

            var days = [];
            $.each(selected_days, function(i, v) {
                days.push(v.valueOf());
            });
            var data = {
                units: selected_units,
                days: days,
                hours_mins: $edit_input.val(),
                name: $name_input.val(),
                tz: tz
            };

            $.ajax({
                type: 'POST',
                data: data,
                url: QAURLs.HANDLE_UNIT_AVAILABLE_TIME_EDIT,
                success: function(res) {
                    unit_available_time_data = res.unit_available_time_data;
                    day_by_day_unit_hours = null;
                    $('#edit_error').html('');
                    update_calendar();
                    reset_fields();
                },
                error: function(res) {
                    console.log(res);
                    $('#edit_error').html('Server error.');
                }
            });
        });

        $delete_go.click(function() {

            $('body').addClass('loading');

            var days = [];
            $.each(selected_days, function(i, v) {
                days.push(v.valueOf());
            });
            var data = {
                units: selected_units,
                days: days,
                tz: tz
            };

            $.ajax({
                type: 'POST',
                data: data,
                url: QAURLs.DELETE_SCHEDULES,
                success: function(res) {
                    $('#delete_modal').modal('hide');
                    unit_available_time_data = res.unit_available_time_data;
                    day_by_day_unit_hours = null;
                    $('#delete_error').html('');
                    update_calendar();
                    reset_fields();
                },
                error: function(res) {
                    console.log(res);
                    $('#delete_error').html('Server error.').slideDown('fast');
                    $('body').removeClass('loading');
                }
            })
        });

        $delete_cancel.click(function() {
            $('#delete_modal').modal('hide');
        });

        $insert_change_uat.click(function() {

            $('body').addClass('loading');
            $('#available_modal').modal('hide');

            var day = moment($effective_date.val(), siteConfig.MOMENT_DATE_FMT).valueOf();

            $.ajax({
                type: 'POST',
                url: QAURLs.HANDLE_UNIT_AVAILABLE_TIME,
                data: {
                    units: selected_units,
                    day: day,
                    'delete': false,
                    hours_sunday: $hours_sunday.val(),
                    hours_monday: $hours_monday.val(),
                    hours_tuesday: $hours_tuesday.val(),
                    hours_wednesday: $hours_wednesday.val(),
                    hours_thursday: $hours_thursday.val(),
                    hours_friday: $hours_friday.val(),
                    hours_saturday: $hours_saturday.val(),
                    tz: tz
                },
                success: function(res) {
                    unit_available_time_data = res.unit_available_time_data;
                    day_by_day_unit_hours = null;
                    reset_fields();
                    update_calendar();
                },
                error: function(res) {
                    console.log(res);
                }
            })
        });

        $units.felter({
            mainDivClass: 'col-md-12 form-control',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            // choiceDivClass: 'row',
            label: 'Serviceable Units',
            initially_displayed: true,
            selectAll: true,
            selectNone: true,
            height: 350,
            slimscroll: true,
            renderOption: function(opt_data) {
                var id_attr = 'felter-option-div-' + opt_data.value;
                var class_attr = 'felter-option' + (opt_data.selected ? ' felter-selected' : '');
                var title_attr = $(opt_data.$option).attr('title');
                var style_color_attr = unit_colours[opt_data.value];
                return $(
                    '<div ' +
                    'id="' + id_attr + '" ' +
                    'class="' + class_attr + '" ' +
                    'title="' + title_attr + '">' +
                    '    ' + opt_data.text + '' +
                    '    <i class="fa fa-cube pull-right" style="color: ' + style_color_attr + '"></i>' +
                    '</div>'
                );
            },
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
        $edit_input.inputmask('99:99', {numericInput: true, removeMaskOnSubmit: true});

        $units.change(function () {
            selected_units = $(this).val() || [];
            disable_uat_btns();
            update_calendar();
        });

        var day = current_day.clone().startOf('week');
        while (day.isBefore(current_day.clone().endOf('week'))) {
            days.push(day.format('dddd'));
            day.add(1, 'days');
        }

        function reset_fields() {
            var days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
            $.each(days, function(i, v) {
                $('#id_hours_' + v).val(v === 'sunday' || v === 'saturday' ? '0000' : '0800');
            });

            $('#edit_input').val('');
            $('#name_input').val('');
        }

        function set_calendar_days(_moment) {
            // day_view = _moment;
            first_day_displayed = day_view.clone().startOf('month').startOf('week');
            last_day_displayed = first_day_displayed.clone().add(7 * 6 - 1, 'days').endOf('day');
            update_calendar();
        }
        set_calendar_days(current_day);

        function create_day_objects() {

            if (!$.isEmptyObject(unit_available_time_data)) {
                day_by_day_unit_hours = [];

                day = first_day_displayed.clone();
                while (day.isBefore(last_day_displayed)) {
                    // var labels = [];
                    var days_unit_hours = [];
                    $.each($units.find('option'), function (i, v) {
                        var unit_id = $(v).val();

                        var uat_data = unit_available_time_data[unit_id].available_times,
                            uate_data = unit_available_time_data[unit_id].available_time_edits,
                            date_acceptance = unit_available_time_data[unit_id].date_acceptance,
                            unit_avail_time_today = 0,
                            day_str = day.format(siteConfig.MOMENT_DATE_FMT),
                            day_str_data = day.format(siteConfig.MOMEN_DATE_DATA_FMT),
                            day_edit_name = null,
                            available_time_changed,
                            unit_name = unit_available_time_data[unit_id].name;

                        if (uat_data.map(function(v) {return v.date_changed}).indexOf(day_str_data) !== -1) {
                            available_time_changed = true;
                            var uat_details = $.grep(uat_data, function(v){ return v.date_changed === day_str_data; })[0];
                        } else {
                            available_time_changed = false;
                        }
                        if (day_str in uate_data) {
                            day_edit_name = uate_data[day_str].name;
                            unit_avail_time_today = duration_minutes(uate_data[day.format(siteConfig.MOMENT_DATE_FMT)].hours);
                        } else {
                            // search through available time objects which should be ordered most recent to oldest
                            for (var j = 0; j < uat_data.length; j++) {

                                if (moment(uat_data[j].date_changed, siteConfig.MOMENT_DATE_DATA_FMT).subtract(1, 'days').isBefore(day)) {
                                    unit_avail_time_today = duration_minutes(
                                        uat_data[j]['hours_' + day.format('dddd').toLocaleLowerCase()]
                                    );
                                    break;
                                }
                            }
                        }
                        var day_details = {
                            'val': unit_avail_time_today,
                            'id': unit_id,
                            'unit_name': unit_name,
                            'date_acceptance': date_acceptance,
                            'day_edit_name': day_edit_name,
                            'available_time_changed': available_time_changed,
                            'unit_id': unit_id
                        };
                        if (available_time_changed) {
                            day_details['uat_details'] = uat_details;
                        }

                        days_unit_hours.push(day_details);

                    });

                    var day_diff = day.diff(first_day_displayed, 'days');
                    day_by_day_unit_hours.push({
                        'day_inx': day_diff,
                        'day_moment': day.clone(),
                        'hours_data': days_unit_hours,
                        'x_inx': day_diff % 7,
                        'y_inx': Math.floor(day_diff / 7),
                        // 'labels': labels
                    });

                    day.add(1, 'days');

                }
            }
        }

        var margin = {top: 0, right: 0, bottom: 0, left: 0},
            day_heading_height = 15,
            width = chart_width - margin.left - margin.right,
            height = chart_height - margin.top - margin.bottom,
            acceptance_icon_width = 12,
            day_space_height = height - day_heading_height,
            day_width = width / 7,
            day_height = day_space_height / 6,
            day_bar_buffer = 10,
            day_bar_space = day_width - 2 * day_bar_buffer,
            max_val = 1440,
            day_label_height = 12;

        var svg = d3.select('#svg-container').append('svg')
            .attr('width', chart_width)
            .attr('height', chart_height)
        .append('g')
            .attr('width', chart_width - margin.left)
            .attr('height', chart_height - margin.top)
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

        var day_heading_container = svg.append('g')
            .attr('class', 'day_heading_container');

        var day_container = svg.append('g')
            .attr('class', 'unit_bar_container')
            .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');

        for (var d in days) {
            day_heading_container.append('text')
                .attr('class', 'day-heading')
                .attr('x', d * day_width + 20)
                .attr('y', day_heading_height - 3)
                .text(days[d]);
        }

        function duration_minutes(duration_string) {
            if (duration_string.indexOf('1D') !== -1) {
                return max_val;
            }
            var split = duration_string.split('H');
            var hours = split[0].slice(-2);
            var min = split[1].substring(0, 2);

            return parseInt(hours) * 60 + parseInt(min);
        }

        function duration_readable(_int) {
            return Math.floor(_int / 60).toString() + ':' + (_int % 60).toString();
        }

        function duration_hours_minutes(duration_string) {
            if (duration_string.indexOf('1D') !== -1) {
                return max_val;
            }
            var split = duration_string.split('H');
            var hours = split[0].slice(-2);
            var min = split[1].substring(0, 2);

            return hours + min;
        }

        function get_unit_at_data() {
            $.ajax({
                url: QAURLs.UNIT_AT_DATA,
                success: function(res) {
                    unit_available_time_data = res.unit_available_time_data;
                    update_calendar();
                    // update_calendar();  // Can't figure put why this needs to be called twice on load.
                    set_calendar_days(current_day);
                },
                error: function(res) {
                    console.log(res);
                }
            });
        }

        function is_current_month(_moment) {
            return _moment.year() === day_view.year() && _moment.month() === day_view.month();
        }

        function is_selected_day(_moment) {
            return selected_days.some(function(m) {
                return m.isSame(_moment, 'day')
            });
        }

        function display_num_selected_days() {
            $num_days_selected.html(
                'Currently ' + selected_days.length + ' day' + (selected_days.length === 1 ? '' : 's') + ' selected for ' + selected_units.length + ' unit' + (selected_units.length === 1 ? '' : 's')
            );
        }
        $open_edit_modal.click(display_num_selected_days);
        $open_delete_modal.click(display_num_selected_days);

        function disable_uat_btns() {
            $open_edit_modal.prop('disabled', selected_days.length === 0 || selected_units.length === 0);
            $open_uat_modal.prop('disabled', selected_units.length === 0 || selected_days.length === 0);
            $open_delete_modal.prop('disabled', selected_units.length === 0 || selected_days.length === 0);
        }

        function update_calendar() {

            $('body').addClass('loading');

            if (!day_by_day_unit_hours) {
                create_day_objects();
            }

            if (day_by_day_unit_hours) {

                // TODO update day and month changes
                var day_selection = day_container.selectAll('g.day-g')
                    .data(day_by_day_unit_hours);

                var day_g = day_selection.enter().append('g')
                    .attr('class', function(d) {
                        var current_month = is_current_month(d.day_moment) ? ' current-month' : '';
                        var selected_day = is_selected_day(d.day_moment) ? ' selected-day' : '';
                        return 'day-g enter' + current_month + selected_day;
                    })
                    .attr('id', function(d) {return 'day-' + d.x_inx + '_' + d.y_inx})
                    .attr('transform', function(d) {
                        return 'translate(' + (d.x_inx * day_width)  + ',' + (d.y_inx * day_height + day_heading_height) + ')';
                    });

                day_selection
                    .attr('class', function(d) {
                        var current_month = is_current_month(d.day_moment) ? ' current-month' : '';
                        var selected_day = is_selected_day(d.day_moment) ? ' selected-day' : '';
                        return 'day-g update' + current_month + selected_day;
                    })
                    .attr('transform', function(d) {
                        return 'translate(' + (d.x_inx * day_width)  + ',' + (d.y_inx * day_height + day_heading_height) + ')';
                    });

                // day_g.attr('class', function(d) {
                //         var current_month = is_current_month(d.day_moment) ? ' current-month' : '';
                //         var selected_day = selected_days.indexOf(d.day_inx) !== -1 ? ' selected-day' : '';
                //         return 'day-g update' + current_month + selected_day;
                //     })
                //     .style('opacity', 1);

                var day_rect_select = day_selection.selectAll('.day-rect')
                        .data(function(d) { return [d];})

                var day_rect = day_rect_select.enter().append('rect')
                    .attr('class', 'day-rect ')
                    .attr('width', day_width)
                    .attr('height', day_height);

                day_rect.on('click', function(e) {

                    var day_data = d3.select(this).data()[0];

                    if (!_ctrl_pressed && !_shift_pressed) {
                        $('.selected-day').removeClass('selected-day');
                        if (is_selected_day(day_data.day_moment) && selected_days.length < 1) {
                            selected_days = [];
                        } else {
                            selected_days = [day_data.day_moment];
                            recent_day_selected = day_data.day_moment;
                        }
                    } else if (_shift_pressed && !_ctrl_pressed) {

                        $('.selected-day').removeClass('selected-day');
                        if (recent_day_selected) {
                            if (!recent_day_selected.isSame(day_data.day_moment, 'day')) {

                                var m = recent_day_selected.clone();
                                selected_days = [];

                                while (m.isBefore(day_data.day_moment)) {
                                    selected_days.push(m.clone());
                                    m.add(1, 'days');
                                }

                                while (m.isAfter(day_data.day_moment)) {
                                    selected_days.push(m.clone());
                                    m.subtract(1, 'days');
                                }
                                selected_days.push(day_data.day_moment);
                            }
                        } else {
                            selected_days.push(day_data.day_moment);
                            recent_day_selected = day_data.day_moment;
                        }
                    } else if (!_shift_pressed && _ctrl_pressed) {

                        if (is_selected_day(day_data.day_moment)) {
                            selected_days = selected_days.filter(function(v) {
                                return !day_data.day_moment.isSame(v, 'day');
                            });
                            $('.selected-day').removeClass('selected-day');
                        } else {
                            selected_days.push(day_data.day_moment);
                            recent_day_selected = day_data.day_moment;
                        }

                    } else {  // Behaviour when shift and ctrl are both pressed TODO tweak this. okay for now
                        $('.selected-day').removeClass('selected-day');
                        if (recent_day_selected) {
                            if (!recent_day_selected.isSame(day_data.day_moment, 'day')) {

                                var m = recent_day_selected.clone();

                                while (m.isBefore(day_data.day_moment)) {
                                    if (!is_selected_day(m)) {
                                        selected_days.push(m.clone());
                                    }
                                    m.add(1, 'days');
                                }

                                while (m.isAfter(day_data.day_moment)) {
                                    if (!is_selected_day(m)) {
                                        selected_days.push(m.clone());
                                    }
                                    m.subtract(1, 'days');
                                }
                                selected_days.push(day_data.day_moment);
                            }
                        } else {
                            selected_days.push(day_data.day_moment);
                            recent_day_selected = day_data.day_moment;
                        }
                    }

                    disable_uat_btns();

                    $effective_date.val(
                        selected_days.length > 0 ? selected_days.sort(function(a, b) { return a - b; })[0].format(siteConfig.MOMENT_DATE_FMT) : ''
                    );

                    d3.selectAll('g.day-g')
                        .attr('class', function(d) {
                            var _class = d3.select(this).attr('class');
                            if (is_selected_day(d.day_moment)) {
                                _class += ' selected-day';
                            }
                            return _class;
                        })

                });

                // var bars_g = day_g.append('g')
                //     .attr('class', 'bars-g');
                var bars_selection = day_selection.selectAll('.bars-g')
                    .data(function(d) { return [d];});

                bars_selection.enter().append('g')
                    .attr('class', 'bars-g');

                var day_of_month = day_selection.selectAll('.day-num')
                    .data(function(d) { return [d.day_moment.format('DD')];});

                day_of_month.enter().append('text')
                    .attr('class', 'day-num')
                    .attr('x', 5)
                    .attr('y', 20)
                    .text(function(d) { return d; });

                day_of_month.transition().text(function(d) { return d; });

                var day_labels = day_selection.selectAll('.day-label')
                    .data(function(d) {
                        return d.hours_data.filter(function(v) {
                            return v.day_edit_name && selected_units.indexOf(v.id) !== -1;
                        }).map(function(v) {return v.day_edit_name; }).filter(function(v, i, self) {
                            return self.indexOf(v) === i;
                        });
                    });

                day_labels.enter().append('text')
                        .attr('class', 'day-label')
                        .attr('x', 25)
                        .attr('y', day_label_height)
                        .text(function(d) { return '- ' + d; })
                        .attr('title', function(d) { return d; })
                    .transition()
                        .attr('y', function(d, i, s) { return day_label_height * (i + 1); });

                day_labels.transition()
                    .text(function(d) { return '- ' + d; })
                    .attr('title', function(d) { return d; })
                    .attr('y', function(d, i, s) { return day_label_height * (i + 1); });

                day_labels.exit()
                    .transition()
                        .style('opacity', 1e-6)
                        .remove();

                var acceptance_icons = day_selection.selectAll('text.acceptance-icon')
                    .data(function(d) {
                        return d.hours_data.filter(function (f) {
                            return selected_units.indexOf(f.id) !== -1 && moment(f.date_acceptance, siteConfig.MOMENT_DATE_FMT).isSame(d.day_moment);
                        });
                    });

                acceptance_icons.enter().append('text')
                        .attr('class', 'icon-label acceptance-icon')
                        .attr('x', function(d, i) { return i * acceptance_icon_width + 25; })
                        .attr('y', 25)
                        .attr('fill', function(d) { return unit_colours[d.id]; })
                        .attr('opacity', 0)
                        .text('A')
                        .on('mouseover', function(d, i, s) {
                            acceptance_icon_tooltip.transition()
                                .duration(200)
                                .style('opacity', .9);
                            acceptance_icon_tooltip	.html(d.unit_name + ' accepted on <br/>'  + d.date_acceptance)
                                .style('left', (d3.event.pageX - 50) + 'px')
                                .style('top', (d3.event.pageY - 50) + 'px');
                            })
                        .on('mouseout', function() {
                            acceptance_icon_tooltip.transition()
                                .duration(200)
                                .style('opacity', 0);
                        })
                    .transition()
                        .attr('opacity', 1);

                acceptance_icons.attr('fill', function(d) { return unit_colours[d.id]; });

                acceptance_icons.exit()
                        .attr('class', 'acceptance-icon exit')
                    .transition()
                        .style('opacity', 1e-6)
                        .remove();

                var bar_rect_selection = bars_selection.selectAll('rect.bar-rect')
                    .data(function (d) {
                        return d.hours_data.filter(function (f) {
                            return selected_units.indexOf(f.id) !== -1 && f.val > 0;
                        });
                    });

                var div = d3.select('body').append('div')
                    .attr('class', 'tooltip hours-tooltip')
                    .style('opacity', 0);

                var acceptance_icon_tooltip = d3.select('body').append('div')
                    .attr('class', 'tooltip acceptance-icon-tooltip')
                    .style('opacity', 0);

                bar_rect_selection.enter().append('rect')
                        .attr('x', function (d, i, s) {
                            return day_bar_buffer + selected_units.indexOf(d.id) * day_bar_space / selected_units.length;
                        })
                        .attr('y', day_height)
                        .attr('class', function(d) { return d.available_time_changed ? 'bar-rect changed' : 'bar-rect'})
                        // .attr('class', 'bar-rect')
                        .attr('width', day_bar_space / selected_units.length)
                        .attr('height', function (d) {
                            return day_height * d.val / max_val
                        })
                        .style('fill', function(d) { return unit_colours[d.id]})
                        .style('opacity', 1e-6)
                        .on('mouseover', function(d, i, s) {
                            div.transition()
                                .duration(200)
                                .style('opacity', .9);
                            div	.html(d.unit_name + '<br/>'  + duration_readable(d.val) + (d.available_time_changed ? '<br/>Schedule changed' : ''))
                                .style('left', function() {
                                    var rect = $(s[s.length - 1]);
                                    return rect[0].getBoundingClientRect().left + 'px';
                                })
                                .style('top', (d3.event.pageY - 50) + 'px');
                            })
                        .on('mouseout', function() {
                            div.transition()
                                .duration(200)
                                .style('opacity', 0);
                        })
                    .transition()
                        .attr('y', function (d) {
                            return day_height * (1 - d.val / max_val);
                        })
                        .style('opacity', 1);

                bar_rect_selection.exit()
                        .attr('class', 'bar-rect exit')
                    .transition()
                        .style('opacity', 1e-6)
                        .remove();

                bar_rect_selection
                        .attr('class', function(d) { return d.available_time_changed ? 'bar-rect changed' : 'bar-rect'})
                        // .attr('class', 'bar-rect')
                        .style('fill', function(d) { return unit_colours[d.id]})
                    .transition()
                        .attr('x', function (d, i, s) {
                            return day_bar_buffer + selected_units.indexOf(d.id) * day_bar_space / selected_units.length;
                        })
                        .attr('y', function (d) {
                            return day_height * (1 - d.val / max_val);
                        })
                        .attr('height', function (d) {
                            return day_height * d.val / max_val
                        })
                        .attr('width', day_bar_space / selected_units.length);

                var uat_change_icons = bars_selection.selectAll('text.uat-change-icon')
                    .data(function(d) {
                        return d.hours_data.filter(function (f) {
                            return selected_units.indexOf(f.id) !== -1 && f.available_time_changed;
                        });
                    });

                uat_change_icons.enter().append('text')
                        .attr('class', 'icon-label uat-change-icon')
                        .attr('x', function (d, i, s) {
                            return day_bar_buffer + selected_units.indexOf(d.id) * day_bar_space / selected_units.length + ((day_bar_space / selected_units.length) / 2) - 5;
                        })
                        .attr('y', day_height - 5)
                        // .attr('fill', function(d) { return unit_colours[d.id]; })
                        .attr('opacity', 0)
                        .text('C')
                    .transition()
                        .attr('opacity', 1);

                uat_change_icons.transition()
                    .attr('x', function (d, i, s) {
                        return day_bar_buffer + selected_units.indexOf(d.id) * day_bar_space / selected_units.length + ((day_bar_space / selected_units.length) / 2) - 5;
                    });

                uat_change_icons.exit()
                        .attr('class', 'acceptance-icon exit')
                    .transition()
                        .style('opacity', 1e-6)
                        .remove();


            }
            $('body').removeClass('loading');
        }

        get_unit_at_data();

    });
});
