require(['jquery', 'moment', 'd3', 'daterangepicker', 'select2', 'felter', 'sl_utils', 'inputmask', 'json2'], function ($, moment, d3) {

    var csrftoken = $("[name=csrfmiddlewaretoken]").val();
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    var _ctrl_pressed = false,
        _shift_pressed = false;

    $(document).keydown(function(event){
        if (event.which == '17')
            _ctrl_pressed = true;
        else if (event.which == '16')
            _shift_pressed = true;
    });

    $(document).keyup(function(){
        if (event.which == '17')
            _ctrl_pressed = false;
        else if (event.which == '16')
            _shift_pressed = false;
    });

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


        var $units = $('#units'),
            $year = $('#id_year_select'),
            $month = $('#id_month_select'),
            $next_month = $('#next-month'),
            $prev_month = $('#prev-month'),
            $svg_container = $('#svg-container'),
            $set_edits = $('#set_edits'),
            $set_uat = $('#set_uat'),
            $submit_edit = $('#submit_edit'),
            $submit_insert = $('#submit_insert'),
            $name_input = $('#name_input'),
            $edit_input = $('#edit_input');

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

        var chart_height = 600,
            chart_width = $svg_container.width() - 15;

        var color_scale = d3.scaleOrdinal(d3['schemeCategory20']);
        var unit_colours = {};
        $.each($units.find('option'), function(i, v) {
            unit_colours[$(v).val()] = color_scale(i);
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

        $submit_edit.click(function() {
            var days = [];
            $.each(selected_days, function(i, v) {
                days.push(v.valueOf());
            });
            var data = {
                units: selected_units,
                days: days,
                hours_mins: $edit_input.val(),
                name: $name_input.val()
            };

            $.ajax({
                type: 'POST',
                data: data,
                url: QAURLs.HANDLE_UNIT_AVAILABLE_TIME_EDIT,
                success: function(res) {
                    unit_available_time_data = res.unit_available_time_data;
                    day_by_day_unit_hours = null;
                    $('#available_edits_modal').modal('hide');
                    update_calendar();
                },
                error: function(res) {
                    console.log(res);
                    $('#edit_error').html('Server error.')
                }
            })
        });

        $submit_insert.click(function() {
            var day = selected_days[0].valueOf();

            var data = {
                units: selected_units,
                day: day
            };

            $.each($('.duration.weekday-duration'), function(i, v) {
                data[$(v).attr('name')] = $(v).val();
            });

            $.ajax({
                type: 'POST',
                data: data,
                url: QAURLs.HANDLE_UNIT_AVAILABLE_TIME,
                success: function(res) {
                    unit_available_time_data = res.unit_available_time_data;
                    day_by_day_unit_hours = null;
                    $('#available_modal').modal('hide');
                    update_calendar();
                },
                error: function(res) {
                    console.log(res);
                    $('#uat_error').html('Server error.')
                }
            })

        });

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
                    var labels = [];
                    var days_unit_hours = [];
                    $.each($units.find('option'), function (i, v) {
                        var unit_id = $(v).val();

                        var uat_data = unit_available_time_data[unit_id].available_times;
                        var uate_data = unit_available_time_data[unit_id].available_time_edits;
                        var unit_avail_time_today = 0;
                        var day_str = day.format('YYYY-MM-DD');
                        if (day_str in uate_data) {
                            var day_edit_name = uate_data[day_str].name;
                            if (labels.indexOf(day_edit_name) === -1) {
                                labels.push(uate_data[day_str].name);
                            }
                            unit_avail_time_today = duration_minutes(uate_data[day.format('YYYY-MM-DD')].hours);
                        } else {
                            // search through available time objects which should be ordered most recent to oldest
                            for (var j = 0; j < uat_data.length; j++) {

                                if (moment(uat_data[j].date_changed, 'YYYY-MM-DD').subtract(1, 'days').isBefore(day)) {
                                    unit_avail_time_today = duration_minutes(
                                        uat_data[j]['hours_' + day.format('dddd').toLocaleLowerCase()]
                                    );
                                    break;
                                }
                            }
                        }
                        days_unit_hours.push({
                            'val': unit_avail_time_today,
                            'id': unit_id
                        });

                    });

                    var day_diff = day.diff(first_day_displayed, 'days');
                    day_by_day_unit_hours.push({
                        'day_inx': day_diff,
                        'day_moment': day.clone(),
                        'hours_data': days_unit_hours,
                        'x_inx': day_diff % 7,
                        'y_inx': Math.floor(day_diff / 7),
                        'labels': labels
                    });

                    day.add(1, 'days');

                }
            }
        }

        var margin = {top: 0, right: 0, bottom: 0, left: 0},
            day_heading_height = 15,
            width = chart_width - margin.left - margin.right,
            height = chart_height - margin.top - margin.bottom,
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

        function get_unit_at_data() {
            $.ajax({
                url: QAURLs.UNIT_AT_DATA,
                success: function(res) {
                    unit_available_time_data = res.unit_available_time_data;
                    update_calendar();
                    // update_calendar();  // Can't figure put why this needs to be called twice on load.
                    set_calendar_days(current_day)
                },
                error: function(res) {
                    console.log(res);
                }
            })
        }

        function is_current_month(_moment) {
            return _moment.year() === day_view.year() && _moment.month() === day_view.month();
        }

        function is_selected_day(_moment) {
            return selected_days.some(function(m) {
                return m.isSame(_moment, 'day')
            });
        }

        function disable_uat_btns() {
            $set_edits.prop('disabled', selected_days.length === 0 || selected_units.length === 0);
            $set_uat.prop('disabled', selected_units.length === 0 || selected_days.length !== 1);
        }

        function update_calendar() {

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
                    .data(function(d) { return d.labels; });

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

                var bar_rect_selection = bars_selection.selectAll('rect.bar-rect')
                    .data(function (d) {
                        return d.hours_data.filter(function (f) {
                            return selected_units.indexOf(f.id) !== -1 && f.val > 0;
                        });
                    });

                bar_rect_selection.enter().append('rect')
                        .attr('x', function (d, i, s) {
                            return day_bar_buffer + selected_units.indexOf(d.id) * day_bar_space / selected_units.length;
                        })
                        .attr('y', day_height)
                        .attr('class', 'bar-rect enter')
                        .attr('width', day_bar_space / selected_units.length)
                        .attr('height', function (d) {
                            return day_height * d.val / max_val
                        })
                        .style('fill', function(d) { return unit_colours[d.id]})
                        .style('opacity', 1e-6)
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

                bar_rect_selection.attr('class', 'bar-rect update')
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
            }
        }

        get_unit_at_data();

    });
});