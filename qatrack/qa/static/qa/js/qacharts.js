require(['jquery', 'lodash', 'd3', 'moment', 'saveSvgAsPng', 'slimscroll', 'qautils', 'daterangepicker', 'felter', 'select2'], function ($, _, d3, moment, saveSvgAsPng) {

    var waiting_timeout = null;
    // var test_list_names;

    $(document).ready(function () {

        var $sites = $("#sites"),
            $units = $('#units'),
            $frequencies = $('#frequencies'),
            $test_lists = $('#test-lists'),
            $tests = $('#tests'),
            $show_events = $('#show_events'),
            $service_log_box = $('#service-log-box'),
            $cc_chart_options = $("#cc-chart-options"),
            $status_selector = $('#status-selector'),
            $service_type_selector = $('#service-type-selector'),
            $gen_chart = $('#gen-chart'),
            d3_filter_box = d3.select('#filter-box'),
            $filter_box = $('#filter-box'),
            $filter_resizer = d3.select('#filter-resizer'),
            $chart_options = $('#chart-options'),
            d3chart_resizer = d3.select('#chart-resizer'),
            $date_range = $('#date-range'),
            $chart_type = $('#chart-type'),
            $subgroup_size = $('#subgroup-size'),
            $n_baseline_subgroups = $('#n-baseline-subgroups'),
            $include_fit = $('#include-fit'),
            $combine_data = $('#combine-data'),
            $relative_diff = $('#relative-diff'),
            $highlight_flags = $('#highlight-flags'),
            $highlight_comments = $('#highlight-comments'),
            $control_chart_container = $("#control-chart-container"),
            $review_required = $('#review-required');

        var date_format = siteConfig.MOMENT_DATE_FMT;

        var default_service_type_ids = $service_type_selector.val();

        var set_chart_height;

        $sites.felter({
            mainDivClass: 'col-sm-1',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            height: 350,
            label: 'Sites',
            slimscroll: true,
            selectAll: true,
            selectNone: true,
            initially_displayed: true,
            renderOption: function(opt_data){
                var div_id = 'felter-option-site-div-' + opt_data.value;
                return $('<div id="' + div_id + '" class="felter-option' + (opt_data.selected ? ' felter-selected' : '') + '" title="' + $(opt_data.$option).attr('title') + '">'  + opt_data.text + '</div>');
            }
        });
        $units.felter({
            mainDivClass: 'col-sm-2',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            height: 350,
            label: 'Units',
            slimscroll: true,
            selectAll: true,
            selectNone: true,
            initially_displayed: true,
            filters: {
                showInactiveUnits: {
                    selected: false,
                    run_filter_when_selected: false,   // No, run filter when not selected
                    label: 'Show Inactive Units',
                    filter: function (obj_data) {
                        return $(obj_data.$option).attr('data-active') === 'True';
                    },
                    refresh_on_dependent_changes: false
                }
            },
            dependent_on_filters: [
                {
                    element: $sites,
                    filter: function () {
                        var sites = $sites.val();
                        if (_.isNull(sites)){
                            return [];
                        }
                        var units = [];
                        _.each($units.find("option"), function(opt){
                            var $opt = $(opt);
                            if (sites.indexOf(opt.dataset.site) >= 0){
                                units.push(parseInt($opt.val()));
                            }
                        });
                        return units;
                    },
                    is_ajax: false
                }
            ],
            renderOption: function(opt_data){
                var div_id = 'felter-option-unit-div-' + opt_data.value;
                return $('<div id="' + div_id + '" class="felter-option' + (opt_data.selected ? ' felter-selected' : '') + '" title="' + $(opt_data.$option).attr('title') + '">'  + opt_data.text + '</div>');
            }
        });

        $frequencies.felter({
            mainDivClass: 'col-sm-2',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            height: 350,
            slimscroll: true,
            label: 'Frequencies',
            selectAll: true,
            selectNone: true,
            initially_displayed: false,
            dependent_on_filters: [
                {
                    element: $units,
                    filter: function () {
                        var units = $units.val();
                        var frequencies = [];
                        _.each(units, function (unit) {
                            frequencies = _.union(frequencies, window.QACharts.unit_frequencies[unit]);
                        });
                        return frequencies;
                    },
                    is_ajax: false
                }
            ],
            renderOption: function(opt_data){
                var div_id = 'felter-option-freq-div-' + opt_data.value;
                return $('<div id="' + div_id + '" class="felter-option' + (opt_data.selected ? ' felter-selected' : '') + '" title="' + $(opt_data.$option).attr('title') + '">'  + opt_data.text + '</div>');
            }
        });

        $test_lists.felter({
            mainDivClass: 'col-sm-3',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            height: 350,
            slimscroll: true,
            label: 'Test Lists',
            selectAll: true,
            selectNone: true,
            initially_displayed: false,
            filters: {
                showInactiveTestLists: {
                    selected: false,
                    run_filter_when_selected: false,   // No, run filter when not selected
                    label: 'Show Inactive Test Lists',
                    filter: function (obj_data) {
                        var show_self = false;
                        $.each($units.val(), function(i, v) {
                            if ($.inArray(parseInt(obj_data.value), QACharts.unit_testlist_active[v]) !== -1) {
                                show_self = true;
                            }
                        });
                        return show_self;
                    },
                    refresh_on_dependent_changes: true
                }
            },
            dependent_on_filters: [
                {
                    element: $units,
                    filter: function (callback) {
                        var frequencies = $frequencies.val();
                        var units = $units.val();

                        if (!units || !frequencies || units.length === 0 || frequencies.length === 0) {
                            return callback([]);
                        }

                        var data_filters = {units: units, frequencies: frequencies};

                        $.ajax({
                            type: "get",
                            url: QAURLs.CHART_DATA_URL + "testlists/",
                            data: data_filters,
                            contentType: "application/json",
                            dataType: "json",
                            success: function (result, status, jqXHR) {
                                if (callback) {
                                    callback(result.test_lists);
                                }
                            },
                            error: function (error) {

                                finished_chart_update();
                                if (typeof console != "undefined") {
                                    console.log(error);
                                }
                            }
                        });

                    },
                    is_ajax: true
                },
                {
                    element: $frequencies,
                    filter: function (callback) {
                        var units = $units.val();
                        var frequencies = $frequencies.val();

                        if (!units || !frequencies || units.length === 0 || frequencies.length === 0) {
                            return callback([]);
                        }

                        var data_filters = {units: units, frequencies: frequencies};

                        $.ajax({
                            type: "get",
                            url: QAURLs.CHART_DATA_URL + "testlists/",
                            data: data_filters,
                            contentType: "application/json",
                            dataType: "json",
                            success: function (result, status, jqXHR) {
                                if (callback) {
                                    callback(result.test_lists);
                                }
                            },
                            error: function (error) {

                                finished_chart_update();
                                if (typeof console != "undefined") {
                                    console.log(error);
                                }
                            }
                        });

                    },
                    is_ajax: true
                }
            ],
            renderOption: function(opt_data){
                var div_id = 'felter-option-tl-div-' + opt_data.value;
                return $('<div id="' + div_id + '" class="felter-option' + (opt_data.selected ? ' felter-selected' : '') + '" title="' + $(opt_data.$option).attr('title') + '">'  + opt_data.text + '</div>');
            }
        });

        $tests.felter({
            mainDivClass: 'col-sm-4',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            height: 350,
            label: 'Tests',
            slimscroll: true,
            selectAll: true,
            selectNone: true,
            initially_displayed: false,
            dependent_on_filters: [
                {
                    element: $test_lists,
                    filter: function(callback) {

                        var test_lists = $test_lists.val();
                        if (!test_lists || test_lists.length === 0) {
                            return callback([]);
                        }

                        var data_filters = {"test_lists": test_lists};

                        $.ajax({
                            type: "get",
                            url: QAURLs.CHART_DATA_URL + "tests/",
                            data: data_filters,
                            contentType: "application/json",
                            dataType: "json",
                            success: function (result, status, jqXHR) {
                                if (callback) {
                                    callback(result.tests);
                                }
                            },
                            error: function (error) {
                                console.log(error);
                            }
                        });

                    },
                    is_ajax: true
                }
            ],
            renderOption: function(opt_data){
                var div_id = 'felter-option-test-div-' + opt_data.value;
                return $('<div id="' + div_id + '" class="felter-option' + (opt_data.selected ? ' felter-selected' : '') + '" title="' + $(opt_data.$option).attr('title') + '">'  + opt_data.text + '</div>');
            }
        });

        $tests.change(function() {
            $gen_chart.prop('disabled', !$(this).val());
        });

        $status_selector.select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });
        $service_type_selector.select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        var y;
        var max_y_resize = 425;
        var is_max = true;
        var dragResize = d3.drag()
            .on('start', function() {
                y = d3.mouse(this)[1];
                remove_tooltip_outter();
            }).on('drag', function() {
                var h = d3_filter_box.node().offsetHeight;
                // Determine resizer position relative to resizable (parent)
                var dy = d3.mouse(this)[1] - y;

                // Avoid negative or really small widths
                var new_h = d3.max([50, d3.min([max_y_resize, h + dy])]);
                is_max = new_h >= max_y_resize;

                d3_filter_box.style('height', new_h + 'px');
            });

        $filter_resizer.call(dragResize);

        initialize_charts();

        /*var test_filters = ["#test-list-container .checkbox-container", "#test-container", "#frequency-container"];
         _.each(test_filters, function (container) {
         hide_all_inputs(container);
         });*/


        $date_range.daterangepicker({
            ranges: {
                "Last 7 Days": [
                    moment().subtract(7, 'days'),
                    moment()
                ],
                "Last 14 Days": [
                    moment().subtract(14, 'days'),
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
                ],
                "Week To Date": [
                    moment().startOf('week'),
                    moment()
                ],
                "Month To Date": [
                    moment().startOf('month'),
                    moment()
                ],
                "Year To Date": [
                    moment().startOf('year'),
                    moment()
                ]
            },

            showDropdowns: true,
            startDate: moment().subtract(365, 'days'),
            endDate: moment(),
            linkedCalendars: false,
            opens: 'left',
            locale: {
                format: siteConfig.DATERANGEPICKER_DATE_FMT
            }
        });

        $("#control-chart-container, #instructions").hide();

        $chart_type.change(set_chart_options);

        $("#gen-chart").click(update_chart);

        $("#save-image").click(function(){
            var svg = $("svg");
            if (svg.length === 0 && $control_chart_container.find('img').length === 0){
                return;
            }

            if ($chart_type.val() === 'basic') {
                // Get the d3js SVG element and save using saveSvgAsPng.js
                saveSvgAsPng.saveSvgAsPng(svg.get(0), "plot.png", {scale: 1, backgroundColor: "#FFFFFF", canvg: window.canvg});
            } else {
                var a = $("<a>")
                    .attr("href", $control_chart_container.find('img').attr('src'))
                    .attr("download", "control_plot.png")
                    .appendTo("body");
                a[0].click();
                a.remove();
            }
        });

        $("#data-table-wrapper").on('click', "#csv-export", export_csv);

        function set_filter_height() {
            max_y_resize = 425;
            if (is_max) {
                d3_filter_box.transition().style('height', max_y_resize + 'px');
                remove_tooltip_outter();
            }
        }

        set_chart_options();
        set_options_from_url();


        function initialize_charts() {
            //TODO d3 charts:
            // create_chart([{name:"",data:[[new Date().getTime(),0,0]]}]);
        }

        // function switch_chart_type() {
        //     set_chart_options();
        //     if ($chart_type.val() === 'control') {
        //         $service_event_container.slideUp('fast');
        //     } else {
        //         $service_event_container.slideDown('fast');
        //     }
        //     $("#chart-container, #control-chart-container").toggle();
        // }

        function set_chart_options() {
            if (basic_chart_selected()) {
                $cc_chart_options.slideUp('fast');
                $service_log_box.slideDown('fast');
            } else {
                $cc_chart_options.slideDown('fast');
                $service_log_box.slideUp('fast');
                $relative_diff.attr("checked", false);
            }
            set_filter_height();
        }

        function update_chart() {

            $control_chart_container.slideUp('fast');
            if ($chart_type.val() === 'control') {
                $('#chart > svg').remove();
            }
            start_chart_update();
            set_chart_url();
            if (basic_chart_selected()) {
                create_basic_chart();
            } else {
                create_control_chart();
            }
        }

        function start_chart_update() {
            $("#gen-chart").text("loading");
        }

        function finished_chart_update() {
            $("#gen-chart").text("Generate Chart");
        }

        function set_chart_url() {

            var filters = get_data_filters();

            var options = [];

            $.each(filters, function (key, values) {
                if (_.isArray(values)) {
                    $.each(values, function (idx, value) {
                        options.push(key + QAUtils.OPTION_DELIM + value);
                    });
                } else if (!_.isEmpty(values) || values === true) {
                    options.push(key + QAUtils.OPTION_DELIM + values);
                }
            });

            var loc = window.location.protocol + "//" + window.location.hostname;
            if (window.location.port !== "") {
                loc += ":" + window.location.port;
            }

            loc += window.location.pathname;

            $("#chart-url").val(loc + "?" + options.join(QAUtils.OPTION_SEP));
        }

        function get_data_filters() {

            return {
                units: $units.val(),
                statuses: $status_selector.val(),
                date_range: $date_range.val().replace(/ /g, '%20'),
                tests: $tests.val(),
                test_lists: $test_lists.val(),
                frequencies: $frequencies.val(),
                n_baseline_subgroups: $n_baseline_subgroups.val(),
                subgroup_size: $subgroup_size.val(),
                fit_data: $include_fit.is(":checked"),
                combine_data: $combine_data.is(":checked"),
                relative: $relative_diff.is(":checked"),
                highlight_comments: $highlight_comments.is(":checked"),
                highlight_flags: $highlight_flags.is(":checked"),
                show_events: $show_events.is(':checked'),
                service_types: $service_type_selector.val(),
                chart_type: $chart_type.val(),
                inactive_units: $units.data('felter').isFiltered('showInactiveUnits'),
                inactive_test_lists: $test_lists.data('felter').isFiltered('showInactiveTestLists')
            };
        }

        function get_date(date_id) {
            return $(date_id).val();
        }

        function basic_chart_selected() {
            return $chart_type.val() === "basic";
        }

        function create_basic_chart() {
            retrieve_data(plot_data);
        }

        function retrieve_data(callback, error) {
            var data_filters = get_data_filters();
            if (!data_filters.tests || data_filters.tests.length === 0) {
                initialize_charts();
                finished_chart_update();
                return;
            }

            $.ajax({
                type: "get",
                url: QAURLs.CHART_DATA_URL,
                data: data_filters,
                contentType: "application/json",
                dataType: "json",
                success: function (result, status, jqXHR) {
                    if (!result.success) {
                        console.log(result.error_type);
                        if (result.error_type === 'too_many_parameters') {
                            displayChartError('Error generating results, query too large. Try fewer units, deselecting service events, smaller date range etc.');
                        } else {
                            displayChartError('Error generating results.');
                        }
                        console.log(result.error);
                    } else {
                        finished_chart_update();
                        callback(result);
                    }
                },
                error: function (error) {
                    finished_chart_update();
                    if (typeof console != "undefined") {
                        console.log(error);
                        displayChartError('Error generating results.');

                    }
                }
            });

        }

        function plot_data(data) {
            var data_to_plot = convert_data_to_chart_series(data);
            d3.select("svg").remove();
            create_chart(data_to_plot);
            update_data_table(data);
        }

        function displayChartError(error_msg) {

            d3.select("svg").remove();

            var chart_width = $('#chart').width() - 15,
                chart_height = 40,
                margin = {top: 20, right: 30, bottom: 140, left: 30};

            var svg = d3.select("#chart")
                .append("svg")
                .attr("width", chart_width)
                .attr("height", chart_height) //height + margin.top + margin.bottom
                .style('border', 'solid 1px #bbb')
                .style("background-color", "white")
                .append("g")
                .attr("width", chart_width - margin.left)
                .attr("height", chart_height - margin.top)
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            svg.append("text")
                .style('fill', 'red')
                .text(error_msg);

            update_data_table({'table': ''});
            $("#chart-url").val('');
        }

        function convert_data_to_chart_series(data) {
            /**
             * Format data in the following pattern:
             *
             * data = {
         *     series = [
         *          {
         *              test_name: name_of_test,
         *              line_data_test_results: [{x: date, y: value }],
         *              line_data_reference: [{x: date, y: reference }],
         *              area_data_ok: [{x: date, y_high: tol_high, y_low: tol_low}],
         *              area_data_upper_tol: [{x: date, y_high: act_high, y_low: tol_high}],
         *              area_data_lower_tol: [{x: date, y_high: tol_low, y_low: act_low}]
         *          }
         *      ],
         *      events = {}
         * ]
         */

            var _data = {},
                series = [],
                events = [];

            var colors = ['#001F3F', '#3c8dbc', '#A47D7C', '#444444', '#ff851b', '#39CCCC', '#605ca8', '#00a65a', '#D81B60'];

            // test_list_names = data.plot_data.test_list_names;

            d3.map(data.plot_data.series).each(function (v, k, m) {

                var line_data_test_results = [],
                    line_data_reference = [],
                    area_data_ok = [],
                    area_data_upper_tol = [],
                    area_data_lower_tol = [],
                    visible = true,
                    lines_visible = true,
                    ref_tol_visible = true;

                d3.map(v.series_data).each(function (val) {
                    if (_.isNull(val.value)) {
                        return;
                    }
                    var x = moment(val.date).valueOf(),
                        tol_low,
                        tol_high;

                    line_data_test_results.push({
                        x: x,
                        y: val.value,
                        test_instance_id: val.test_instance_id,
                        test_list_instance_id: val.test_list_instance.id,
                        test_instance_comment: val.test_instance_comment,
                        display: val.display,
                        flagged: val.test_list_instance.flagged
                    });

                    if (val.reference !== null) {
                        line_data_reference.push({x: x, y: val.reference});

                        var have_ok_reg = !_.isNull(val.tol_low) || !_.isNull(val.tol_high) || !_.isNull(val.act_high) || !_.isNull(val.act_low);
                        if (have_ok_reg){
                            if (!_.isNull(val.tol_low)){
                                tol_low = val.tol_low;
                            }else if (!_.isNull(val.act_low)){
                                tol_low = val.act_low;
                            }else {
                                tol_low = val.reference;
                            }

                            if (!_.isNull(val.tol_high)){
                                tol_high = val.tol_high;
                            }else if (!_.isNull(val.act_high)){
                                tol_high = val.act_high;
                            }else {
                                tol_high = val.reference;
                            }

                            area_data_ok.push({x: x, y_high: tol_high, y_low: tol_low});
                        }else{
                            area_data_ok.push({x: x, y_high: val.reference, y_low: val.reference});
                        }

                        var have_lower_tol_reg = !_.isNull(val.tol_low);
                        if (have_lower_tol_reg){
                            if (!_.isNull(val.act_low)){
                                area_data_lower_tol.push({x: x, y_high: val.tol_low, y_low: val.act_low});
                            }else{
                                area_data_lower_tol.push({x: x, y_high: val.tol_low, y_low: val.tol_low});
                            }
                        }else{
                            area_data_lower_tol.push({x: x, y_high: val.reference, y_low: val.reference});
                        }

                        var have_upper_tol_reg = !_.isNull(val.tol_high);
                        if (have_upper_tol_reg){
                            if (!_.isNull(val.act_high)){
                                area_data_upper_tol.push({x: x, y_high: val.act_high, y_low: val.tol_high});
                            }else{
                                area_data_upper_tol.push({x: x, y_high: val.tol_high, y_low: val.tol_high});
                            }
                        }else{
                            area_data_upper_tol.push({x: x, y_high: val.reference, y_low: val.reference});
                        }


                    }
                });

                series.push({
                    test_name: k,
                    line_data_test_results: line_data_test_results,
                    line_data_reference: line_data_reference,
                    area_data_ok: area_data_ok,
                    area_data_upper_tol: area_data_upper_tol,
                    area_data_lower_tol: area_data_lower_tol,
                    color: colors.pop(),
                    visible: visible,
                    lines_visible: lines_visible,
                    ref_tol_visible: ref_tol_visible,
                    unit: v.unit,
                    test_list: v.test_list
                });
            });

            d3.map(data.plot_data.events).each(function (v, k, m) {

                var e_data = v;
                e_data.x = moment(v.date).valueOf();
                e_data.visible = true;
                events.push(e_data);
            });

            _data._series = series;
            _data._events = events;

            return _data;
        }

        function remove_tooltip_outter() {}


        function circleRadius(dat, idx, series){
            // Use larger circle radius for ti's with comments
            var showComment = $highlight_comments.is(":checked") && dat.test_instance_comment;
            var showFlag = $highlight_flags.is(":checked") && dat.flagged;
            if (showComment || showFlag){
                return 5;
            }
            return 4;
        }

        function circleStroke(d, i, s) {
            var showComment = $highlight_comments.is(":checked") && d.test_instance_comment;
            var showFlag = $highlight_flags.is(":checked") && d.flagged;
            if (showComment){
                return "rgb(60, 141, 188)";
            }else if (showFlag){
                return "rgb(243, 156, 18)";
            }
            return s[i].parentNode.__data__.color;
        }

        function circleStrokeWidth(d, i, s) {
            var showComment = $highlight_comments.is(":checked") && d.test_instance_comment;
            var showFlag = $highlight_flags.is(":checked") && d.flagged;
            if (showComment || showFlag){
                return 4;
            }
            return 2;
        }

        function create_chart(_data) {

            // var allEmpty = _.every(_.map(series_data, function (o) {
            //     return o.data.length === 0
            // }));
            // if (allEmpty) {
            //     return;
            // }

            var from = $date_range.val().split(' - ')[0];
            var to = $date_range.val().split(' - ')[1];
            var num_tests = _data._series.length;

            var tracker_locked = false;

            ///////////////////////// CHART

            var chart_width = $('#chart').width() - 15,
                xAxisHeight = 20;

            if (!set_chart_height) {
                set_chart_height = $(window).height() - 50;
            }
            var chart_height = set_chart_height;


            var circle_radius = 3,
                circle_radius_highlight = 4,
                line_width = 1.5,
                line_width_highlight = 3;

            var margin = {top: 20, right: 30, bottom: 140, left: 30},
                margin2 = {top: chart_height - margin.bottom, right: 10, bottom: 20, left: 30},
                legend_collapse_width = 50,
                width = chart_width - margin.left - margin.right - legend_collapse_width,
                height = chart_height - margin.top - margin.bottom,
                height2 = margin.bottom - 2 * xAxisHeight - 10 - margin2.bottom,
                legend_width = legend_collapse_width,
                legend_overhang = 0;

            var event_group_height = 10;

            var tooltip_height = 105,
                tooltip_width = 250,
                tooltip_padding = 7;

            var parseDate = d3.timeFormat("%Y%m%d").parse;

            var xScale = d3.scaleTime()
                    .range([0, width]),

                xScale2 = d3.scaleTime()
                    .range([0, width]); // Duplicate xScale for brushing ref later

            var yScale = d3.scaleLinear()
                    .range([height, 0]),

                yScale2 = d3.scaleLinear()
                    .range([height2, 0]);

            var xAxis = d3.axisBottom(xScale),
                xAxis2 = d3.axisBottom(xScale2),
                yAxis = d3.axisLeft(yScale);

            yAxis.tickSizeInner(-width).tickSizeOuter(0);

            var line = d3.line()
                .curve(d3.curveLinear)
                .x(function (d) {
                    return xScale(d.x);
                })
                .y(function (d) {
                    return yScale(d.y);
                })
                .defined(function (d) {
                    return d.y !== null;
                });

            var line2 = d3.line()
                .curve(d3.curveLinear)
                .x(function (d) {
                    return xScale2(d.x);
                })
                .y(function (d) {
                    return yScale2(d.y);
                })
                .defined(function (d) {
                    return d.y !== null;
                });

            var area = d3.area()
                .x(function (d) {
                    return xScale(d.x);
                })
                .y0(function (d) {
                    return yScale(d.y_low);
                })
                .y1(function (d) {
                    return yScale(d.y_high);
                })
                .defined(function (d) {
                    return d.y_high - d.y_low > 0;
                });

            var svg = d3.select("#chart")
                .append("svg")
                .attr("width", chart_width)
                .attr("height", chart_height) //height + margin.top + margin.bottom
                .style('border', 'solid 1px #bbb')
                .style("background-color", "white")
                .append("g")
                .attr("width", chart_width - margin.left)
                .attr("height", chart_height - margin.top)
                // .attr('class')
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            //append clip path for lines plotted, hiding those part out of bounds
            var mainClip = svg.append("defs")
                .append("clipPath")
                .attr("id", "clip")
                .append("rect")
                .attr("width", width)
                .attr("height", height);

            var legendClip = d3.select('defs')
                .append("clipPath")
                .attr("id", "clip-legend")
                .append('rect')
                .attr("width", width + legend_collapse_width)
                .attr("height", height);

            // find min and max X within date range
            xScale.domain([moment(from, date_format).valueOf(), moment(to, date_format).endOf('day').valueOf()]);
            var maxY = findMaxY(_data._series, xScale.domain());
            var minY = findMinY(_data._series, xScale.domain());

            var maxX = findMaxX(_data._series);
            var minX = findMinX(_data._series);
            if (maxX === minX) {
                minX = moment(minX).subtract(1, 'days').valueOf();
                maxX = moment(maxX).add(1, 'days').valueOf();
            }

            yScale.domain(yBuff(minY, maxY));
            yScale2.domain(yBuff(minY, maxY));
            xScale2.domain(xScale.domain());

            ////////////////////// for slider
            var context = svg.append("g")
                .attr("transform", "translate(" + 0 + "," + (margin2.top + 10) + ")")
                .attr("class", "context");

            var brush = d3.brushX()
                .extent([[0, 0], [width, height2]])
                .on("brush", brushed);

            var x_axis2_elem = context.append("g")
                .attr("class", "x axis1")
                .attr("transform", "translate(0," + height2 + ")")
                .call(xAxis2);

            // plot at the bottom
            var context_path = context.append('g')
                .attr('class', 'context-path-group')
                .selectAll('.context-path')
                .data(_data._series)
                .enter().append("path")
                .attr("class", "line context-path")
                .attr("d", function (d) {
                    return line2(d.line_data_test_results);
                })
                .style('stroke-width', line_width)
                .style("stroke", function (d) {
                    return d.color;
                })
                .style('opacity', 1);

            // append the brush for the selection of subsection
            var brush_elem = context.append("g")
                .attr("class", "x brush")
                .call(brush);

            var brush_rect = brush_elem.selectAll("rect")
                .attr("height", height2);

            var context_hover_line = context.append('line')
                .attr("id", "context-hover-line")
                .attr("x1", 10).attr("x2", 10)
                .attr("y1", 0).attr("y2", height2)
                .style("pointer-events", "none")
                .style('stroke', '#000')
                .style('stroke-width', '2px')
                .style("opacity", 0);

            ///////////////////// draw line graph
            var x_axis_elem = svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + height + ")")
                .call(xAxis);

            var y_axis_elem = svg.append("g")
                .attr("class", "y axis")
                // .attr("transform", "translate(" + 0 + "," + 0 + ")")
                .call(yAxis);

            y_axis_elem.append("text")
                .attr("transform", "rotate(-90)")
                .attr("y", 6)
                .attr("x", -10)
                .attr("dy", ".71em")
                .style("text-anchor", "end")
                .text("Issues Rating");

            // Hover line
            var hoverLineGroup = svg.append("g")
                .attr("class", "hover-line");

            var hoverLine = hoverLineGroup // Create line with basic attributes
                .append("line")
                .attr("id", "hover-line")
                .attr("x1", 10).attr("x2", 10)
                .attr("y1", 0).attr("y2", height)
                .style("pointer-events", "none") // Stop line interferring with cursor
                .style("opacity", 1e-6); // Set opacity to zero

            var test = svg.selectAll(".test")
                .data(_data._series)
                .enter()
                .append("g")
                .attr("class", "test");

            // Draw ok area:
            var test_ok = test.append('g')
                .attr('class', 'test-ok');

            test_ok.append('path')
                .attr('class', 'area ok')
                .style("pointer-events", "none")
                .attr("id", function (d) {
                    return "area_ok_" + d.test_name.replace(/\W+/g, "_");
                })
                .attr("d", function (d) {
                    return d.visible && d.ref_tol_visible ? area(d.area_data_ok) : null; // If array key "visible" = true then draw line, if not then don't
                })
                .attr("clip-path", "url(#clip)")
                .attr('opacity', 0.1);

            // Draw upper tol area:
            var test_upper_tol = test.append('g')
                .attr('class', 'test-tol-upper');

            test_upper_tol.append('path')
                .attr('class', 'area tol')
                .style("pointer-events", "none")
                .attr("id", function (d) {
                    return "area_upper_tol_" + d.test_name.replace(/\W+/g, "_");
                })
                .attr("d", function (d) {
                    return d.visible && d.ref_tol_visible ? area(d.area_data_upper_tol) : null; // If array key "visible" = true then draw line, if not then don't
                })
                .attr("clip-path", "url(#clip)")
                .attr('opacity', 0.1);

            // Draw lower tol area:
            var test_lower_tol = test.append('g')
                .attr('class', 'test-tol-lower');

            test_lower_tol.append('path')
                .attr('class', 'area tol')
                .style("pointer-events", "none")
                .attr("id", function (d) {
                    return "area_lower_tol_" + d.test_name.replace(/\W+/g, "_");
                })
                .attr("d", function (d) {
                    return d.visible && d.ref_tol_visible ? area(d.area_data_lower_tol) : null; // If array key "visible" = true then draw line, if not then don't
                })
                .attr("clip-path", "url(#clip)")
                .attr('opacity', 0.1);

            // Draw test results:
            var test_result = test.append("g")
                .attr("class", "test-result");

            test_result.append("path")
                .attr("class", "line results")
                .style("pointer-events", "none") // Stop line interferring with cursor
                .attr("id", function (d) {
                    return "line_result_" + d.test_name.replace(/\W+/g, "_");
                })
                .attr("d", function (d) {
                    return d.visible && d.lines_visible ? line(d.line_data_test_results) : null; // If array key "visible" = true then draw line, if not then don't
                })
                .attr("clip-path", "url(#clip)")//use clip path to make irrelevant part invisible
                .attr('stroke-width', line_width)
                .style("stroke", function (d) {
                    return d.color;
                });

            test_result.selectAll("circle")
                .data(function (d) {
                    return d.line_data_test_results;
                })
                .enter().append('circle')
                .attr('id', function (d) {
                    return 'ti_' + d.test_instance_id;
                })
                .attr('class', function (d, i, s) {
                    return 'tli_' + d.test_list_instance_id + ' tl_' + s[i].parentNode.__data__.test_list.id;
                })
                .attr("clip-path", "url(#clip)")
                .attr("stroke-width", circleStrokeWidth)
                .attr("stroke-opacity", 1)
                .attr("stroke", circleStroke)
                .attr("cx", function (d) {
                    return xScale(d.x);
                })
                .attr("cy", function (d) {
                    return yScale(d.y);
                })
                .attr("r", circleRadius)
                .attr("fill", "white")
                .attr("fill-opacity", 1)
                .on('mousemove', mousemove);

            var test_reference = test.append('g')
                .attr('class', 'test-reference');

            test_reference.append('path')
                .attr("class", "line results")
                .style("pointer-events", "none") // Stop line interferring with cursor
                .style("stroke-dasharray", ("3, 3"))
                .attr("id", function (d) {
                    return "line_reference_" + d.test_name.replace(/\W+/g, "_");
                })
                .attr("d", function (d) {
                    return d.visible && d.ref_tol_visible ? line(d.line_data_reference) : null; // If array key "visible" = true then draw line, if not then don't
                })
                .attr("clip-path", "url(#clip)")
                .style("stroke", function (d) {
                    return d.color;
                })
                .style('stroke-width', line_width)
                .style('opacity', 0.7);

            var event_group = svg.append('g')
                .attr("clip-path", "url(#clip)")
                .attr('transform', 'translate(0, ' + (height - event_group_height - 1) + ')')
                .attr('class', 'event-group');

            var event = event_group.selectAll('.service-marker')
                .data(_data._events)
                .enter().append('g')
                .attr('id', function (d, i, s) {
                    return 'se_' + d.id;
                })
                .attr('class', 'service-marker')
                .attr('transform', function (d) {
                    return 'translate(' + (xScale(d.x) - event_group_height / 2) + ',' + 0 + ')';
                });

            var event_marker_points = '0,' + event_group_height + ' ' + event_group_height / 2 + ',0 ' + event_group_height + ',' + event_group_height;
            event.append('polygon')
                .attr('stroke', function (d) {
                    // return d.rtsqas.length === 0 ? 'grey' : '#00c0ef'
                    return d.rtsqas.some(function(d2) {
                        return _data._series.some(function(d3) {
                            return d3.test_list.id === d2.test_list;
                        });
                    }) ? '#00c0ef' : 'grey';
                })
                .attr('fill', function (d) {

                    if (d.initiated_by === '') {
                        return 'none';
                    } else if (_data._series.some(function(d2) { return d2.test_list.id === d.initiated_by.test_list_id; })) {
                        return '#3c8dbc';
                    }
                    return 'none';
                })
                .attr('stroke-width', 1)
                .attr('class', 'service-marker-icon')
                .attr('points', event_marker_points);

            ///////////// Create invisible rect for mouse tracking
            var mouse_tracker = svg.append("rect")
                .attr("width", width)
                .attr("height", height)
                .attr("id", "mouse-tracker")
                .style("fill", 'transparent')
                .on("mousemove", mousemove)
                .on('click', toggleLock);

            ////////////////////// legend
            var legendRowHeight = 25,
                legend_expanded = false;

            var legend = svg.append('g')
                .attr("clip-path", "url(#clip-legend)")
                .append('g')
                .attr('transform', 'translate(' + width + ', 0)')
                .attr('class', 'legend');

            legend.append('rect')
                .attr("height", legendRowHeight * num_tests + (_data._events.length > 0 ? legendRowHeight * 3 : 0) + 35)
                .attr('width', 10)
                .attr('id', 'legend-rect')
                .style('fill', 'rgba(244, 244, 244, 0.8)')
                // .style('background-color', 'rgba(244, 244, 244, 0.8)')
                .style('stroke', '#ddd')
                .style('stroke-width', 1);

            var legend_entry = legend.selectAll('.legend-row')
                .data(_data._series)
                .enter().append('g')
                .attr('transform', function (d, i) {
                    return 'translate(0,' + ((i + 1) * legendRowHeight - 8) + ')';
                })
                .attr('class', 'legend-row');
            if (_data._events.length > 0) {
                var legend_se_types = legend.selectAll('.legend-set-row')
                    .data([
                        {'name': 'Service Event', 'id': 0},
                        {'name': 'Service Event with Initiating QC', 'id': 1},
                        {'name': 'Service Event with Return To Service', 'id': 2}
                    ])
                    .enter().append('g')
                    .attr('transform', function (d, i) {
                        return 'translate(0,' + ((_data._series.length + i + 1) * legendRowHeight - 8) + ')';
                    })
                    .attr('class', 'legend-set-row');

                legend_se_types.append('polygon')
                    .attr('stroke', function (d) {
                        return d.id === 2 ? '#00c0ef' : 'grey';
                    })
                    .attr('fill', function (d) {
                        return d.id === 1 ? '#3c8dbc' : 'transparent';
                    })
                    .attr('stroke-width', 1)
                    .attr('class', 'service-marker-icon')
                    .attr('transform', 'translate(30, 0)')
                    .attr('points', event_marker_points);

                legend_se_types.append('text')
                    .attr('x', 50)
                    .attr('y', 12)
                    // .attr('clip-path', 'url(#clip)')
                    .text(function (d) {
                        return d.name;
                    })
                    .style('font-size', 12);

                legend_se_types.append('title').text(function(d) {
                    switch(d.id) {
                        case 0: return 'Service Event';
                        case 1: return 'Service Event with Initiating QC';
                        case 2: return 'Service Event with Return To Service';
                    }
                });
            }

            // Legend series toggle
            var legend_entry_toggle = legend_entry.append('rect')
                .attr('width', 12)
                .attr('height', 12)
                .attr('x', 10)
                .attr('y', 1.5)
                .attr('fill', function (d) {
                    return d.visible ? d.color : '#F1F1F2';
                })
                .attr('id', function (d, i) {
                    return 'tsb_' + i;
                })
                .attr('class', 'toggle-series-box')
                .attr('stroke', function (d) {
                    return d.lines_visible ? d.color : null;
                })
                .attr('stroke-width', 4)

                .on('click', function (d, i, s) {

                    if (d.visible && d.lines_visible) d.lines_visible = false;
                    else if (d.visible) d.visible = false;
                    else {
                        d.visible = true;
                        d.lines_visible = true;
                    }

                    if (d.ref_tol_visible) {
                        if (!d.visible) {

                            d3.select(s[i].parentNode.childNodes[1])
                                .transition()
                                .attr('stroke-width', 0)
                                .style('fill', '#ddd');
                        }
                        else {
                            d3.select(s[i].parentNode.childNodes[1])
                                .transition()
                                .style('fill', 'rgba(0, 166, 90, 0.3)')
                                .attr('stroke-width', 0.5);
                        }
                    }

                    d3.select(this)
                        .transition()
                        .attr('fill', function (d) {
                            return d.visible ? d.color : '#ddd';
                        })
                        .attr('stroke', function (d) {
                            return d.visible && d.lines_visible ? d.color : '#ddd';
                        });

                    redrawMainContent();
                })

                .on('mouseover', function (d) {

                    if (d.visible) {
                        d3.select('#line_result_' + d.test_name.replace(/\W+/g, '_'))
                            .transition()
                            .attr('stroke-width', line_width_highlight);
                    }
                })

                .on('mouseout', function (d) {

                    if (d.visible) {
                        d3.select('#line_result_' + d.test_name.replace(/\W+/g, '_'))
                            .transition()
                            .attr('stroke-width', line_width);
                    }

                });
            legend_entry_toggle.append('title').text('Toggle on/off line, symbols and plot​');

            // Legend ref/tol toggle
            var legend_rt_rect = legend_entry.append('rect')
                .attr('width', 15)
                .attr('height', 15)
                .attr('x', 30)
                .style('fill', 'rgba(0, 166, 90, 0.3)')
                .style('stroke', function (d) {
                    return d.color;
                })
                .style('stroke-dasharray', ('2, 2'))
                .attr('stroke-width', function (d) {
                    return d.ref_tol_visible ? 0.5 : 0;
                })
                .attr('class', 'toggle-ref-tol-box')
                .attr('id', function (d, i) {
                    return 'trtb_' + i;
                })

                .on('click', function (d, i, s) {
                    d.ref_tol_visible = !d.ref_tol_visible;
                    d3.select(this).classed('hidden-toggle', !d.ref_tol_visible);
                    redrawMainContent();
                })

                .on('mouseover', function (d) {

                    if (d.visible) {

                        d3.selectAll(
                            '#area_ok_' + d.test_name.replace(/\W+/g, '_') +
                            ',#area_upper_tol_' + d.test_name.replace(/\W+/g, '_') +
                            ',#area_lower_tol_' + d.test_name.replace(/\W+/g, '_')
                        )
                            .transition()
                            .attr('opacity', 0.3);
                    }

                })

                .on('mouseout', function (d) {

                    if (d.visible) {

                        if (d.ref_tol_visible) {
                            d3.selectAll(
                                '#area_ok_' + d.test_name.replace(/\W+/g, '_') +
                                ',#area_upper_tol_' + d.test_name.replace(/\W+/g, '_') +
                                ',#area_lower_tol_' + d.test_name.replace(/\W+/g, '_')
                            )
                                .transition()
                                .attr('opacity', 0.1);
                        }
                    }

                });
            legend_rt_rect.append('title').text('Toggle on/off tolerances, references​');

            legend_entry.append('text')
                .attr('x', 50)
                .attr('y', 12)
                // .attr('clip-path', 'url(#clip)')
                .text(function (d) {
                    return d.test_name;
                })
                .style('font-size', 12);

            // resize legend box
            var largest_entry = 0;
            legend_entry.each(function () {
                largest_entry = d3.max([largest_entry, d3.select(this).select('text').node().getBBox().width]);
            });
            var legend_expand_width = largest_entry + 60;
            legend.select('#legend-rect').attr('width', legend_expand_width);

            var legend_toggle = legend.append('rect')
                .attr('id', 'legend-toggle')
                .attr('class', 'legend-toggle btn btn-primary btn-flat')
                .attr('width', 40)
                .attr('height', 14)
                .attr('x', 5)
                .attr('y', legendRowHeight * (num_tests + (_data._events.length > 0 ? 3 : 0)) + 15)
                .style('fill', '#3c8dbc')
                .style('cursor', 'pointer')
                .style('stroke', '#367fa9')
                .style('stroke-width', '0.9px');

            legend_toggle.on('click', function (d, i, s) {
                legend_expanded = !legend_expanded;
                toggleLegend();
            })
                .on('mouseover', function () {
                    d3.select(this).style('fill', '#367fa9').style('stroke', '#204d74');
                })
                .on('mouseout', function () {
                    d3.select(this).style('fill', '#3c8dbc').style('stroke', '#367fa9');
                });

            var toogle_text = legend.append('text')
                .attr('width', 30)
                .attr('height', 10)
                .attr("x", 8)
                .attr("y", legendRowHeight * (num_tests + (_data._events.length > 0 ? 3 : 0)) + 25)
                .style("pointer-events", "none")
                .style('font', '10px sans-serif')
                .style('fill', '#fff')
                .text('\u25C0 show');
            var legend_height = legendRowHeight * (num_tests + (_data._events.length > 0 ? 3 : 0)) + 35;
            var cheatLine = svg.append('line')
                .attr('x2', width + legend_collapse_width)
                .attr('y2', 0)
                .attr('x1', width + legend_collapse_width)
                .attr('y1', legend_height)
                .style('stroke', '#ddd');

            // Add mouseover events for hover line.
            var old_x_closest,
                format = d3.timeFormat('%a, %d %b %Y at %H:%M');

            var highlighted_event;

            d3.select(window).on('resize', function () {

                chart_width = $('#chart').width();
                width = chart_width - margin.left - margin.right - legend_collapse_width;

                d3.select("svg").transition().attr("width", chart_width);
                svg.transition().attr('width', chart_width - margin.left);

                legend.transition().attr('transform', 'translate(' + (width - legend_overhang) + ', 0)');
                legendClip.transition().attr("width", width + legend_collapse_width);
                cheatLine.transition()
                    .attr('x1', width + legend_collapse_width)
                    .attr('x2', width + legend_collapse_width);

                redrawMainXAxis();
                redrawMainContent();
                redrawContextXAxis();
            });
            var y, h;
            var dragChartResize = d3.drag()
                .on('start', function() {
                    // y = d3.mouse(this)[1];
                    y = d3.event.sourceEvent.clientY;
                    h = chart_height;
                    remove_tooltip_outter();
                }).on('drag', function() {
                    // Determine resizer position relative to resizable (parent)

                    // var dy = d3.mouse(this)[1] - y;
                    var dy = d3.event.sourceEvent.clientY - y;

                    // Avoid negative or really small widths
                    chart_height = d3.max([50, h + dy]);
                    set_chart_height = chart_height;

                    xAxisHeight = 0.028 * chart_height;
                    margin2.top = chart_height - margin.bottom;
                    height = chart_height - margin.top - margin.bottom;
                    height2 = margin.bottom - 2 * xAxisHeight - 10 - margin2.bottom;

                    d3.select("svg").transition().attr('height', chart_height);
                    svg.transition().attr('height', chart_height);

                    redrawMainYAxis();
                    redrawMainContent();
                });
            d3chart_resizer.call(dragChartResize);

            function toggleLegend() {

                legend_overhang = legend_expanded ? legend_expand_width - legend_collapse_width : 0;

                legend.transition()
                    .attr('transform', 'translate(' + (width - legend_overhang) + ', 0)');

                if (legend_expanded) toogle_text.text('hide \u25B6');
                else toogle_text.text('\u25C0 show');

            }

            function yBuff(minY, maxY) {
                var y_buff;
                if (minY === maxY) {
                    y_buff = maxY === 0 ? 2 : minY * 0.1;
                } else {
                    y_buff = (maxY - minY) * 0.1;
                }
                return [minY - y_buff, maxY + y_buff];
            }

            /**
             * redraw axis along x.
             */
            function redrawMainXAxis() {

                xScale.range([0, width]);

                mouse_tracker.transition().attr('width', width);
                mainClip.transition().attr('width', width);
                x_axis_elem.transition().call(xAxis);
                yAxis.tickSizeInner(-width);

            }
            /**
             * redraw axis along y.
             */
            function redrawMainYAxis() {

                yScale.range([height, 0]);
                x_axis_elem.transition().attr("transform", "translate(0," + height + ")");
                context.transition().attr("transform", "translate(0," + (margin2.top + 10) + ")");
                event_group.transition().attr('transform', 'translate(0, ' + (height - event_group_height - 1) + ')');

                mouse_tracker.transition().attr('height', height);
                mainClip.transition().attr('height', height);
                hoverLine.transition().attr("y2", height);
            }

            function redrawContextXAxis() {

                xScale2.range([0, width]);

                x_axis2_elem.transition().call(xAxis2);
                context_path.transition().attr("d", function (d) {
                    return line2(d.line_data_test_results);
                });
                brush.extent([[0, 0], [width, height2]]);
                brush_elem.call(brush);
            }

            /**
             *  redraw everything (x axis not included here, see brushed())
             */
            function redrawMainContent() {

                removeTooltip();

                maxY = findMaxY(_data._series, xScale.domain());
                minY = findMinY(_data._series, xScale.domain());
                yScale.domain(yBuff(minY, maxY));

                svg.select(".y.axis")
                    .transition()
                    .call(yAxis);

                // main line
                test_result.selectAll('path')
                    .transition()
                    .attr("d", function (d) {
                        return d.visible && d.lines_visible ? line(d.line_data_test_results) : null;
                    });

                // circles
                test_result.filter(function (d) {
                    return d.visible;
                }).selectAll("circle")
                    .transition()
                    .attr("cy", function (d) {
                        return yScale(d.y);
                    })
                    .attr("cx", function (d) {
                        return xScale(d.x);
                    })
                    .on("end", function () {
                        d3.select(this).attr('visibility', 'visible');
                    });
                test_result.filter(function (d) {
                    return !d.visible;
                }).selectAll("circle")
                    .transition()
                    .attr("cy", function (d) {
                        return yScale(d.y);
                    })
                    .attr("cx", function (d) {
                        return xScale(d.x);
                    })
                    .attr('visibility', 'hidden');

                // dotted reference line
                test_reference.selectAll('path')
                    .transition()
                    .attr("d", function (d) {
                        return d.visible && d.ref_tol_visible ? line(d.line_data_reference) : null;
                    });

                // ok and tol areas
                test_ok.selectAll('path')
                    .transition()
                    .attr('d', function (d) {
                        return d.visible && d.ref_tol_visible ? area(d.area_data_ok) : null;
                    });
                test_upper_tol.selectAll('path')
                    .transition()
                    .attr('d', function (d) {
                        return d.visible && d.ref_tol_visible ? area(d.area_data_upper_tol) : null;
                    });
                test_lower_tol.selectAll('path')
                    .transition()
                    .attr('d', function (d) {
                        return d.visible && d.ref_tol_visible ? area(d.area_data_lower_tol) : null;
                    });

                // service markers
                if ($show_events.is(':checked')) {
                    event_group.selectAll('.service-marker')
                        .transition()
                        .attr('transform', function (d) {
                            return 'translate(' + (xScale(d.x) - event_group_height / 2) + ',' + 0 + ')';
                        });
                }

                // Context path update
                context_path
                    .transition()
                    .style('opacity', function (d) {
                        return d.visible ? 1 : 0.2;
                    });
            }

            function mousemove() {

                if (!tracker_locked) {
                    var mouse_x = d3.mouse(this)[0], // Finding mouse x position on rect
                        mouse_y = d3.mouse(this)[1];

                    var x0 = xScale.invert(mouse_x),
                        x_closest;

                    if ($show_events.is(':checked') && mouse_y > d3.select(this).attr('height') * 0.91) {

                        x_closest = findClosestEvent(x0);

                        if (x_closest != old_x_closest) {
                            old_x_closest = x_closest;
                            highlightEvent(x_closest);
                        }

                    } else {
                        x_closest = findClosestX(x0);

                        if (x_closest != old_x_closest) {
                            old_x_closest = x_closest;
                            highlightCircles(x_closest);
                        }
                    }
                    moveHoverLine(x_closest);
                }
            }

            function removeHighlights() {

                d3.selectAll('circle[r="' + circle_radius_highlight + '"]')
                    .attr('r', circleRadius)
                    .attr('stroke-width', circleStrokeWidth);

                d3.selectAll('.service-marker-icon')
                    .attr('stroke-width', 1);

                d3.selectAll('.service-marker-icon')
                    .attr('stroke-width', 1);

                d3.select("#hover-line")
                    .style("opacity", 0);

                d3.select('#context-hover-line')
                    .style('opacity', 0);

            }

            function removeTooltip() {

                svg.selectAll('.tli_line').remove();

                d3.selectAll('circle[r="' + circle_radius_highlight + '"]')
                    .attr('r', circleRadius)
                    .attr('stroke-width', 1);

                d3.selectAll('.tooltip')
                    .transition()
                    .style('opacity', 0)
                    .on('end', function () {
                        $(this).remove();
                    });

                tracker_locked = false;
            }
            remove_tooltip_outter = removeTooltip;

            function toggleLock() {
                tracker_locked = !tracker_locked;
                d3.selectAll('.tooltip').each(function () {
                    var c = d3.color(d3.select(this).style('background-color'));
                    c.opacity = tracker_locked ? c.opacity + 0.3 : c.opacity - 0.3;
                    d3.select(this).style('background-color', c);
                });
            }

            function highlightEvent(x) {
                removeHighlights();
                removeTooltip();

                var h_event = d3.selectAll('.service-marker-icon')
                    .filter(function (d) {
                        return d.x == x;
                    })
                    .attr('stroke-width', 2);

                var event_tooltip = d3.select("body")
                    .append("div")
                    .attr('id', 'event_tooltip')
                    .attr('class', 'tooltip')
                    .style("position", "absolute")
                    .style("z-index", "10")
                    .style('width', tooltip_width + 'px')
                    .style('height', tooltip_height + 'px')
                    .style('padding', tooltip_padding + 'px')
                    .style('background-color', 'rgba(100, 100, 100, 0.2)')
                    .attr("opacity", 0)
                    .text("a simple tooltip")
                    .on('click', toggleLock);

                h_event.each(function (d) {
                    var event_data = d;

                    var top = window.pageYOffset + this.getBoundingClientRect().top - tooltip_height,
                        left = window.pageXOffset + this.getBoundingClientRect().left - tooltip_width / 2 + event_group_height / 2;
                    highlighted_event = event_data.id;

                    event_tooltip
                        .style('left', left + 'px')
                        .style('top', top + 'px')
                        .html(
                            $('#se-tooltip-template').html()
                                .replace(/__se-id__/g, event_data.id)
                                .replace(/__se-date__/g, format(event_data.x))
                                .replace(/__se-wd__/g, event_data.work_description.replace(/"/g, "'"))
                                .replace(/__se-pd__/g, event_data.problem_description.replace(/"/g, "'"))
                                .replace(/__se-u__/g, event_data.unit.name)
                                .replace(/__se-sa__/g, event_data.service_area.name)
                                .replace(/__se-type__/g, event_data.type.name)
                        )
                        .transition()
                        .style('opacity', 1);

                    var tli_coords = [],
                        y_buffer = 20;

                    if (event_data.initiated_by !== '') {

                        var initiated_circles = d3.selectAll('.tli_' + event_data.initiated_by.id);

                        if (initiated_circles.size() > 0) {
                            initiated_circles
                                .attr('r', circle_radius_highlight)
                                .attr('stroke-width', 2);

                            var initiated_test_list_data, initiated_x = 0, initiated_name;
                            initiated_circles.each(function (d, i, s) {
                                initiated_test_list_data = s[i].parentNode.__data__;
                                initiated_x = xScale(d.x);
                                return false;
                            });
                            initiated_name = event_data.unit.name + ' - ' + initiated_test_list_data.test_list.name;

                            var initiated_data = initiated_circles.data(),
                                x_pos,
                                y_pos = window.pageYOffset + this.getBoundingClientRect().top - height + event_group_height + y_buffer,
                                x_buffer = 0,
                                num_rtsqas = event_data.rtsqas.length,
                                chart_div_offset = mouse_tracker.node().getBoundingClientRect().left;

                            var line_from_right = true;
                            if (initiated_x > tooltip_width + 2 * x_buffer) {
                                x_pos = initiated_x + chart_div_offset - tooltip_width - x_buffer;
                                x_pos = d3.min([chart_div_offset + width - tooltip_width - x_buffer, x_pos]);
                                line_from_right = false;
                            } else {
                                x_pos = initiated_x + chart_div_offset + x_buffer;
                                x_pos = d3.max([x_buffer + chart_div_offset, x_pos]);
                            }

                            if (x_pos > width - legend_expand_width + margin.right) {
                                y_pos += legend_height + y_buffer;
                            }

                            tli_coords.push({x: initiated_x, color: 'rgba(60, 141, 188, 0.6)'});

                            var comments = initiated_data[0].test_instance_comment || "";
                            if (comments){
                                comments = '<i class="fa fa-commenting" style="color: rgb(60, 141, 188)" data-toggle="popover" title="Comments" data-content="' + comments + '"></i>';
                            }
                            if (initiated_data[0].flagged){
                                comments += '<i class="fa fa-flag" style="color: rgb(243, 156, 18)" title="Flagged as Important"></i>';
                            }


                            var tli_initiated_tooltip = d3.select("body")
                                .append("div")
                                .attr('id', 'tli-' + initiated_data[0].test_list_instance_id + '_tooltip')
                                .attr('class', 'tli_tooltip tooltip')
                                .style("position", "absolute")
                                .style("z-index", "10")
                                .style('width', tooltip_width + 'px')
                                .style('height', tooltip_height + 'px')
                                .style('padding', tooltip_padding + 'px')
                                .style('background-color', 'rgba(60, 141, 188, 0.2)')
                                .attr("opacity", 0)
                                .style('left', x_pos + 'px')
                                .style('top', y_pos + 'px')
                                .html($('#tli-tooltip-template').html()
                                    .replace(/__tli-id__/g, initiated_data[0].test_list_instance_id)
                                    .replace(/__tli-date__/g, moment(initiated_data[0].x).format('ddd, ' + siteConfig.MOMENT_DATETIME_FMT))
                                    .replace(/__tli-tl-name__/g, initiated_name)
                                    .replace(/__tli-kind__/g, 'Initiating QC')
                                    .replace(/__tli-comments__/g, comments)
                                    .replace(/__tli-ti-value-display__/g, initiated_data[0].display)
                                    .replace(/__show-in__/g, 'style="display: none"')
                                );

                            tli_initiated_tooltip
                                .transition()
                                .style('opacity', 1);
                        }
                    }

                    var _i = 0;
                    for (var i in event_data.rtsqas) {
                        var f = event_data.rtsqas[i];

                        var rtsqa_circles = d3.selectAll('.tli_' + f.test_list_instance);

                        if (rtsqa_circles.size() === 0) {
                            continue;
                        }
                        _i++;

                        rtsqa_circles
                            .attr('r', circle_radius_highlight)
                            .attr('stroke-width', 2);

                        var rtsqa_test_list_data, rtsqa_x = 0;
                        rtsqa_circles.each(function (d, i, s) {
                            rtsqa_test_list_data = s[i].parentNode.__data__;
                            rtsqa_x = xScale(d.x);
                            return false;
                        });

                        var rtsqa_name = rtsqa_test_list_data.unit.name + ' - ' + rtsqa_test_list_data.test_list.name;

                        var rtsqa_data = rtsqa_circles.data(),
                            x_pos,
                            y_pos = window.pageYOffset + this.getBoundingClientRect().top - height + event_group_height + y_buffer + _i * (y_buffer + tooltip_height),
                            x_buffer = 0,
                            num_rtsqas = event_data.rtsqas.length,
                            chart_div_offset = mouse_tracker.node().getBoundingClientRect().left;

                        var line_from_right = true;
                        if (rtsqa_x < width - tooltip_width - 2 * x_buffer) {

                            x_pos = rtsqa_x + chart_div_offset + x_buffer;
                            x_pos = d3.max([x_buffer + chart_div_offset, x_pos]);
                        } else {
                            x_pos = rtsqa_x + chart_div_offset - tooltip_width - x_buffer;
                            x_pos = d3.min([chart_div_offset + width - tooltip_width - x_buffer, x_pos]);
                            line_from_right = false;
                        }

                        tli_coords.push({x: rtsqa_x, color: 'rgba(0, 192, 239, 0.6)'});

                        var rtsqa_comments = rtsqa_data[0].test_instance_comment || "";
                        if (rtsqa_comments){
                            rtsqa_comments = '<i class="fa fa-commenting" style="color: rgb(60, 141, 188)" data-toggle="popover" title="Comments" data-content="' + rtsqa_comments + '"></i>';
                        }

                        if (rtsqa_data[0].flagged){
                            rtsqa_comments += '<i class="fa fa-flag" style="color: rgb(243, 156, 18)" title="Flagged as Important"></i>';
                        }

                        var tli_rtsqa_tooltip = d3.select("body")
                            .append("div")
                            .attr('id', 'tli-' + rtsqa_data[0].test_list_instance_id + '_tooltip')
                            .attr('class', 'tli_tooltip tooltip')
                            .style("position", "absolute")
                            .style("z-index", "10")
                            .style('width', tooltip_width + 'px')
                            .style('height', tooltip_height + 'px')
                            .style('padding', tooltip_padding + 'px')
                            .style('background-color', 'rgba(0, 192, 239, 0.2)')
                            .attr("opacity", 0)
                            .style('left', x_pos + 'px')
                            .style('top', y_pos + 'px')
                            .html($('#tli-tooltip-template').html()
                                .replace(/__tli-id__/g, rtsqa_data[0].test_list_instance_id)
                                .replace(/__tli-date__/g, moment(rtsqa_data[0].x).format('ddd, ' + siteConfig.MOMENT_DATETIME_FMT))
                                .replace(/__tli-tl-name__/g, rtsqa_name)
                                .replace(/__tli-kind__/g, 'Return To Service QC')
                                .replace(/__tli-comments__/g, rtsqa_comments)
                                .replace(/__tli-ti-value-display__/g, rtsqa_data[0].display)
                                .replace(/__show-in__/g, 'style="display: none"')
                            );

                        tli_rtsqa_tooltip
                            .transition()
                            .style('opacity', 1);
                    }

                    var tli_lines = svg.selectAll('.tli_line')
                        .data(tli_coords)
                        .enter().append('line')
                        .attr('class', 'tli_line')
                        .attr('x1', function (d) {
                            return d.x;
                        })
                        .attr('x2', function (d) {
                            return d.x;
                        })
                        .attr('y1', 0)
                        .attr('y2', height)
                        .attr('stroke-width', 1)
                        .attr('stroke', function (d) {
                            return d.color;
                        })
                        .style('opacity', 0)
                        .transition()
                        .style('opacity', 1);

                    svg.selectAll('.tli_line').exit().transition().style('opacity', 0).remove();
                });
            }

            function highlightCircles(x) {

                removeHighlights();
                removeTooltip();

                var ti_circles = d3.selectAll('circle')
                    .filter(function (d) {
                        return d.x == x;
                    })
                    .attr('r', circle_radius_highlight)
                    .attr('stroke-width', 2);

                if (ti_circles.size() === 0) {
                    return;
                }

                var test_list_data;
                ti_circles.each(function (d, i, s) {
                    test_list_data = s[i].parentNode.__data__;
                    return false;
                });
                var y_buffer = 20;

                var tli_name = test_list_data.unit.name + ' - ' + test_list_data.test_list.name;

                var tli_data = ti_circles.data(),
                    // x_c = xScale(initiated_data[0].x),
                    x_pos = xScale(x),
                    y_pos = window.pageYOffset + mouse_tracker.node().getBoundingClientRect().top + y_buffer,
                    x_buffer = 0,
                    chart_div_offset = mouse_tracker.node().getBoundingClientRect().left;

                var overlapped_by_legend = x_pos > width - legend_expand_width + margin.right;
                if (legend_expanded && overlapped_by_legend) {
                    y_pos += legend_height + y_buffer;
                }

                var line_from_right = true;
                if (x_pos > tooltip_width + 2 * x_buffer) {
                    x_pos = x_pos + chart_div_offset - tooltip_width - x_buffer;
                    x_pos = d3.min([chart_div_offset + width - tooltip_width - x_buffer, x_pos]);
                    line_from_right = false;
                } else {
                    x_pos = x_pos + chart_div_offset + x_buffer;
                    x_pos = d3.max([x_buffer + chart_div_offset, x_pos]);
                }

                var colour = 'rgba(100, 100, 100, 0.2)';

                var comments = tli_data[0].test_instance_comment || "";
                if (comments){
                    comments = '<i class="fa fa-commenting" style="color: rgb(60, 141, 188)" data-toggle="popover" title="Comments" data-content="' + comments + '"></i>';
                }
                if (tli_data[0].flagged){
                    comments += '<i class="fa fa-flag" style="color: rgb(243, 156, 18)" title="Flagged as Important"></i>';
                }

                var tli_tooltip = d3.select("body")
                    .append("div")
                    .attr('id', 'tli-' + tli_data[0].test_list_instance_id + '_tooltip')
                    .attr('class', 'tli_tooltip tooltip')
                    .style("position", "absolute")
                    .style("z-index", "10")
                    .style('width', tooltip_width + 'px')
                    .style('height', tooltip_height + 'px')
                    .style('padding', tooltip_padding + 'px')
                    .style('background-color', colour)
                    .attr("opacity", 0)
                    .style('left', x_pos + 'px')
                    .style('top', y_pos + 'px')
                    .html($('#tli-tooltip-template').html()
                        .replace(/__tli-id__/g, tli_data[0].test_list_instance_id)
                        .replace(/__tli-date__/g, moment(x).format('ddd, ' + siteConfig.MOMENT_DATETIME_FMT))
                        .replace(/__tli-tl-name__/g, tli_name)
                        .replace(/__tli-kind__/g, 'Test List')
                        .replace(/__tli-comments__/g, comments)
                        .replace(/__tli-ti-value-display__/g, tli_data[0].display)
                        .replace(/__show-in__/g, 'style="display: block"')
                    )
                    .on('click', toggleLock);

                tli_tooltip
                    .transition()
                    .style('opacity', 1);


            }

            function moveHoverLine(x) {

                d3.select("#hover-line") // select hover-line and changing attributes to mouse position
                    .attr("x1", xScale(x))
                    .attr("x2", xScale(x))
                    .style("opacity", 1); // Making line visible

                d3.select('#context-hover-line')
                    .attr('x1', xScale2(x))
                    .attr('x2', xScale2(x))
                    .style('opacity', 0.3);
            }

            //for brusher of the slider bar at the bottom
            function brushed() {

                var selection = d3.event.selection;
                var date_range = selection.map(xScale2.invert, xScale2);
                xScale.domain(date_range);

                x_axis_elem.transition().call(xAxis);

                redrawMainContent();
            }

            brush_elem.transition()
              .call(brush.move, [Math.floor(xScale2(minX)), Math.ceil(xScale2(maxX))]);

            function findMaxX(data) {
                var maxXValues = data.map(function(d) {
                    return d3.max(d.line_data_test_results, function (value) {
                        return value.x;
                    });
                });
                return d3.max(maxXValues) || 0;
            }

            function findMinX(data) {
                var minXValues = data.map(function(d) {
                    return d3.min(d.line_data_test_results, function (value) {
                        return value.x;
                    });
                });
                return d3.min(minXValues) || 0;
            }

            function findMaxY(data, range) {  // Define function "findMaxY"
                var maxYValues = data.map(function (d) {
                    if (d.visible) {

                        var maxY = null;
                        if (d.ref_tol_visible) {

                            var y,
                                series_array = [d.line_data_test_results, d.line_data_reference, d.area_data_ok, d.area_data_upper_tol, d.area_data_lower_tol];
                            for (var l in series_array) {
                                var series = series_array[l];
                                y = d3.max(series, function (value) {
                                    if (value.x > range[0].valueOf() && value.x < range[1].valueOf()) {
                                        return value.y_high ? value.y_high : value.y;
                                    }
                                    else {
                                        return null;
                                    }
                                });
                                maxY = d3.max([maxY, y]);
                            }
                        }

                        else {
                            maxY = d3.max(d.line_data_test_results, function (value) {
                                if (value.x > range[0].valueOf() && value.x < range[1].valueOf()) {
                                    return value.y;
                                }
                                else {
                                    return null;
                                }
                            });
                        }
                        return maxY;
                    }
                });

                return d3.max(maxYValues) || 0;
            }

            function findMinY(data, range) {  // Define function "findMaxY"
                var minYValues = data.map(function (d) {
                    if (d.visible) {

                        var minY = null;
                        if (d.ref_tol_visible) {

                            var y,
                                series_array = [d.line_data_test_results, d.line_data_reference, d.area_data_ok, d.area_data_upper_tol, d.area_data_lower_tol];
                            for (var l in series_array) {
                                var series = series_array[l];
                                y = d3.min(series, function (value) {
                                    if (value.x > range[0].valueOf() && value.x < range[1].valueOf()) {
                                        return value.y_low ? value.y_low : value.y;
                                    }
                                    else {
                                        return Infinity;
                                    }
                                });
                                minY = d3.min([minY, y]);
                            }
                        }

                        else {
                            minY = d3.min(d.line_data_test_results, function (value) {
                                if (value.x > range[0].valueOf() && value.x < range[1].valueOf()) {
                                    return value.y;
                                }
                                else {
                                    return Infinity;
                                }
                            });
                        }
                        return minY;
                    }
                });

                var to_return = d3.min(minYValues) || 0;
                return to_return == Infinity ? 0 : to_return;
            }

            function findClosestX(x) {

                var best_x = 0, best_dist = Infinity,
                    bi_left = d3.bisector(function (d) {
                        return d.x;
                    }).left;

                d3.map(_data._series).each(function (val) {

                    var x_min_max = xAxis.scale().domain();
                    if (val.visible) {
                        var v = val.line_data_test_results,
                            i = bi_left(v, x),
                            d1,
                            d2;

                        if (i === 0 || (v[i - 1].x < x_min_max[0])) {
                            d1 = Infinity;
                        }
                        else {
                            d1 = x - v[i - 1].x;
                        }
                        if (i === v.length || (v[i].x > x_min_max[1])) {
                            d2 = Infinity;
                        }
                        else {
                            d2 = v[i].x - x;
                        }

                        if (d1 < best_dist && d1 < d2) {
                            best_dist = d1;
                            best_x = v[i - 1].x;
                        }
                        else if (d2 < best_dist && d2 < d1) {
                            best_dist = d2;
                            best_x = v[i].x;
                        }

                    }
                });

                return best_x;

            }

            function findClosestEvent(x) {
                var best_x = 0, best_dist = Infinity;

                d3.map(_data._events).each(function (val) {
                    var x_min_max = xAxis.scale().domain();
                    if (val.visible && val.x > x_min_max[0] && val.x < x_min_max[1]) {

                        var d = Math.abs(x - val.x);

                        if (d < best_dist) {
                            best_dist = d;
                            best_x = val.x;
                        }
                    }
                });
                return best_x;
            }
        }

        function get_range_options(prev_selection) {

            return {
                buttons: [
                    {type: 'week', count: 1, text: '1w'},
                    {type: 'month', count: 1, text: '1m'},
                    {type: 'month', count: 6, text: '6m'},
                    {type: 'year', count: 1, text: '1y'},
                    {type: 'all', text: 'All'}
                ],
                selected: prev_selection || 4
            };
        }

        function get_legend_options() {
            var legend = {};
            if ($("#show-legend").is(":checked")) {
                legend = {
                    align: "right",
                    layout: "vertical",
                    enabled: true,
                    verticalAlign: "middle"
                };
            }
            return legend;
        }

        function get_line_width() {
            if ($("#show-lines").is(":checked")) {
                return 2;
            } else {
                return 0;
            }
        }

        function create_control_chart() {
            $control_chart_container.slideDown('fast');
            $control_chart_container.find("img, div.please-wait, div.cc-error").remove();
            $control_chart_container.append("<img/>");
            $control_chart_container.find('img').error(control_chart_error);
            $control_chart_container.append(
                '<div class="please-wait"><em>Please wait for control chart to be generated...this could take a few minutes.</em></div>'
            );

            waiting_timeout = setInterval(check_cc_loaded, 250);
            var chart_src_url = get_control_chart_url();
            $control_chart_container.find('img').attr("src", chart_src_url);
        }

        function check_cc_loaded() {
            if ($control_chart_container.find('img').height() > 100) {
                control_chart_finished();
            }
        }

        function control_chart_error() {
            control_chart_finished();
            $control_chart_container.find('img').remove();
            $control_chart_container.append(
                '<div class="cc-error">Something went wrong while generating your control chart</div>'
            );
        }

        function control_chart_finished() {
            $(".please-wait").remove();
            $("#data-table-wrapper").html("");
            clearInterval(waiting_timeout);
            retrieve_data(update_data_table);
        }

        function get_control_chart_url() {
            var filters = get_data_filters();
            var props = [
                "width=" + ($control_chart_container.width() - 15),
                // "height=" + $("#chart").height(),
                "height=" + 800,
                "timestamp=" + new Date().getTime()
            ];

            $.each(filters, function (k, v) {
                if ($.isArray(v)) {
                    $.each(v, function (i, vv) {
                        props.push(encodeURI(k + "[]=" + vv));
                    });
                } else {
                    props.push(encodeURI(k + "=" + v));
                }
            });

            return QAURLs.CONTROL_CHART_URL + "?" + props.join("&");
        }

        function update_data_table(data) {
            $("#data-table-wrapper").html(data.table);
        }

        //Return all test lists that contain one ore more of the input tests
        function get_test_lists_from_tests(tests) {
            var test_lists = [];
            _.each(tests, function (test) {
                _.each(QACharts.test_info.test_lists, function (e, i) {
                    if (_.contains(e, parseInt(test))) {
                        test_lists.push(i);
                    }
                });
            });

            return _.uniq(test_lists);
        }

        //set initial options based on url hash
        function set_options_from_url() {

            var options = QAURLs.options_from_url_query(document.location.search);

            var units = get_filtered_option_values("units", options);
            var freqs = get_filtered_option_values("frequencies", options);
            var tests = get_filtered_option_values("tests", options);
            var test_lists = get_filtered_option_values("test_lists", options);
            var date_range = get_filtered_option_values("date_range", options)[0];
            var statuses = get_filtered_option_values("statuses", options);
            var service_types = get_filtered_option_values("service_types", options);
            var chart_type = get_filtered_option_values("chart_type", options)[0];
            var subgroup_size = get_filtered_option_values("subgroup_size", options)[0];
            var n_baseline_subgroups = get_filtered_option_values("n_baseline_subgroups", options)[0];
            var include_fit = get_filtered_option_values("include_fit", options)[0];
            var combine_data = get_filtered_option_values("combine_data", options)[0];
            var relative_diff = get_filtered_option_values("relative_diff", options)[0];
            var highlight_flags = get_filtered_option_values("highlight_flags", options)[0];
            var highlight_comments = get_filtered_option_values("highlight_comments", options)[0];
            var show_events = get_filtered_option_values("show_events", options)[0];
            var inactive_units = get_filtered_option_values('inactive_units', options)[0];
            var inactive_test_lists = get_filtered_option_values('inactive_test_lists', options)[0];

            if ((units.length === 0) || (tests.length === 0)) {
                return;
            }

            $units.data('felter').setFilter('showInactiveUnits', inactive_units);
            $units.val(units).change();
            $frequencies.val(freqs).change();
            $test_lists.data('felter').setFilter('showInactiveTestLists', inactive_test_lists);
            $test_lists.val(test_lists).change();
            $tests.val(tests).change();

            $chart_type.val(chart_type ? chart_type : 'basic');
            if (chart_type === 'control') {
                $chart_type.change();
                $subgroup_size.val(subgroup_size);
                $n_baseline_subgroups.val(n_baseline_subgroups);
                $include_fit.prop('checked', include_fit);
            } else {
                $show_events.prop('checked', show_events);
                if ($show_events.is(':checked')) {
                    $service_type_selector.val(service_types.length === 0 ? default_service_type_ids : service_types).change();
                }
            }
            $combine_data.prop('checked', combine_data);
            $relative_diff.prop('checked', relative_diff);
            $highlight_flags.prop('checked', highlight_flags);
            $highlight_comments.prop('checked', highlight_comments);
            if (!date_range) {
                $date_range.data('daterangepicker').setStartDate(moment().subtract(1, 'years').format(siteConfig.MOMENT_DATE_FMT));
                $date_range.data('daterangepicker').setEndDate(moment().format(siteConfig.MOMENT_DATE_FMT));
            } else {
                date_range = date_range.replace(/%20/g, ' ');
                $date_range.data('daterangepicker').setStartDate(moment(date_range.split(' - ')[0], siteConfig.MOMENT_DATE_FMT).format(siteConfig.MOMENT_DATE_FMT));
                $date_range.data('daterangepicker').setEndDate(moment(date_range.split(' - ')[1], siteConfig.MOMENT_DATE_FMT).format(siteConfig.MOMENT_DATE_FMT));
            }
            $status_selector.val(statuses.length === 0 ? window.QACharts.default_statuses : statuses).change();
            $show_events.prop('checked', show_events);

            update_chart();

        }

        function get_filtered_option_values(opt_type, options) {
            var opt_value = function (opt) {
                return opt[1];
            };
            var f = function (opt) {
                return opt[0] == opt_type;
            };
            return _.map(_.filter(options, f), opt_value);
        }

        var downloadURL = function downloadURL(url) {
            var hiddenIFrameID = 'hiddenDownloader',
                iframe = document.getElementById(hiddenIFrameID);
            if (iframe === null) {
                iframe = document.createElement('iframe');
                iframe.id = hiddenIFrameID;
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
            }
            iframe.src = url;
        };

        function export_csv() {
            downloadURL("./export/csv/?" + $.param(get_data_filters()));
        }

        $('#filter-box').fadeTo(1, 1);

    });

    $("body").popover({
        selector: '[data-toggle="popover"]',
        html: true,
        placement: 'auto',
        trigger: 'hover'
    });

});
