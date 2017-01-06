
require(['jquery', 'lodash', 'd3', 'moment', 'qautils', 'daterangepicker'], function ($, _, d3, moment) {

    var waiting_timeout = null;

    $(document).ready(function () {

        initialize_charts();

        var test_filters = ["#test-list-container .checkbox-container", "#test-container", "#frequency-container"];
        _.each(test_filters, function (container) {
            hide_all_inputs(container);
        });

        $("#date-range").daterangepicker({
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
            startDate: moment().subtract(365, 'days'),
            endDate: moment(),
            linkedCalendars: false,
            locale: {
                format: 'DD-MM-YYYY'
            }
        });

        $("#control-chart-container, #instructions").hide();

        $("#chart-type").change(switch_chart_type);

        // $("#toggle-instructions").click(toggle_instructions);

        $("#unit-container input, #frequency-container input, #test-list-container input").change(update_tests);

        $("#gen-chart").click(update_chart);

        $("#data-table-wrapper").on('click', "#csv-export", export_csv);


        set_chart_options();
        set_options_from_url();

    });

    function initialize_charts() {
        //TODO d3 charts:
        // create_chart([{name:"",data:[[new Date().getTime(),0,0]]}]);
    }

    function hide_all_inputs(container) {
        $(container + " input").parent().hide();
    }

    function show_all_inputs(container) {
        $(container + " input").parent().show();
    }

    function switch_chart_type() {
        set_chart_options();
        $("#chart-container, #control-chart-container").toggle();
    }

    function set_chart_options() {
        if (basic_chart_selected()) {
            $("#basic-chart-options").show();
            $("#cc-chart-options").hide();
        } else {
            $("#basic-chart-options").hide();
            $("#cc-chart-options").show();
            $("#relative-diff").attr("checked", false)
        }
    }

    function update_tests() {
        set_frequencies();
        set_test_lists(function () {
            set_tests();
        });
    }

    function set_frequencies() {
        var units = QAUtils.get_checked("#unit-container");
        var frequencies = [];
        _.each(units, function (unit) {
            frequencies = _.union(frequencies, QACharts.unit_frequencies[unit]);
        });

        filter_container("#frequency-container", frequencies);
    }

    function set_test_lists(callback) {
        var units = QAUtils.get_checked("#unit-container");
        var frequencies = QAUtils.get_checked("#frequency-container");

        var inactive = $("#include_inactive").is(":checked");
        var data_filters = {units: units, frequencies: frequencies, inactive: inactive};

        if (units.length > 0 && frequencies.length > 0) {

            $.ajax({
                type: "get",
                url: QAURLs.CHART_DATA_URL + "testlists/",
                data: data_filters,
                contentType: "application/json",
                dataType: "json",
                success: function (result, status, jqXHR) {
                    filter_container("#test-list-container .checkbox-container", result.test_lists);
                    if (callback) {
                        callback();
                    }
                },
                error: function (error) {

                    finished_chart_update();
                    if (typeof console != "undefined") {
                        console.log(error)
                    }
                }
            });
        }
        else {
            filter_container("#test-list-container .checkbox-container", []);
            filter_container("#test-container", []);
        }
    }

    function set_tests(callback) {

        var test_lists = QAUtils.get_checked("#test-list-container .checkbox-container");

        var inactive = $("#include_inactive").is(":checked");
        var data_filters = {"test_lists": test_lists, inactive: inactive};

        if (test_lists.length > 0) {

            $.ajax({
                type: "get",
                url: QAURLs.CHART_DATA_URL + "tests/",
                data: data_filters,
                contentType: "application/json",
                dataType: "json",
                success: function (result, status, jqXHR) {
                    filter_container("#test-container", result.tests);
                    if (callback) {
                        callback();
                    }
                },
                error: function (error) {

                    finished_chart_update();
                    if (typeof console != "undefined") {
                        console.log(error)
                    }
                    ;
                }
            });

        } else {
            filter_container("#test-container", []);
        }
    }

    function filter_container(container, visible) {
        visible = _.map(visible, function (x) {
            return parseInt(x);
        });
        $(container + " input").each(function (i, option) {
            var pk = parseInt($(this).val());
            if (visible.indexOf(pk) >= 0) {
                $(this).parent().show();
            } else {
                $(this).attr("checked", false)
                $(this).parent().hide();
            }
        });
    }

    function update_chart() {
        //TODO d3 charts:
        start_chart_update();
        set_chart_url();
        if (basic_chart_selected()) {
            create_basic_chart();
        } else {
            create_control_chart();
        }
    }

    function start_chart_update() {
        $("#gen-chart").button("loading");
    }

    function finished_chart_update() {
        $("#gen-chart").button("reset");
    }

    function set_chart_url() {

        var filters = get_data_filters();

        var options = [];

        $.each(filters, function (key, values) {
            if (_.isArray(values)) {
                $.each(values, function (idx, value) {
                    options.push(key + QAUtils.OPTION_DELIM + value)
                });
            } else if (!_.isEmpty(values)) {
                options.push(key + QAUtils.OPTION_DELIM + values)
            }
        });

        var loc = window.location.protocol + "//" + window.location.hostname;
        if (window.location.port !== "") {
            loc += ":" + window.location.port;
        }

        loc += window.location.pathname;

        $("#chart-url").val(loc + "#" + options.join(QAUtils.OPTION_SEP));
    }

    function get_data_filters() {
        var filters = {
            units: QAUtils.get_checked("#unit-container"),
            statuses: QAUtils.get_checked("#status-container"),
            date_range: $('#date-range').val(),
            tests: QAUtils.get_checked("#test-container"),
            test_lists: QAUtils.get_checked("#test-list-container .checkbox-container"),
            inactive: $("#include_inactive").is(":checked"),
            frequencies: QAUtils.get_checked("#frequency-container"),
            n_baseline_subgroups: $("#n-baseline-subgroups").val(),
            subgroup_size: $("#subgroup-size").val(),
            fit_data: $("#include-fit").is(":checked"),
            combine_data: $("#combine-data").is(":checked"),
            relative: $("#relative-diff").is(":checked")
        };

        return filters;
    }

    function get_date(date_id) {
        return $(date_id).val();
    }

    function basic_chart_selected() {
        return $("#chart-type").val() === "basic";
    }

    function create_basic_chart() {
        retrieve_data(plot_data);
    }

    function retrieve_data(callback, error) {
        var data_filters = get_data_filters();
        if (data_filters.tests.length === 0) {
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
                finished_chart_update();
                callback(result);
            },
            error: function (error) {
                finished_chart_update();
                if (typeof console != "undefined") {
                    console.log(error)
                }
            }
        });

    }

    function plot_data(data) {
        //TODO d3 charts:
        var data_to_plot = convert_data_to_chart_series(data.data);
        d3.select("svg").remove();
        create_chart(data_to_plot);
        update_data_table(data);
    }

    function convert_data_to_chart_series(data) {
        /**
         * Format data in the following pattern:
         *
         * series = ]
         *      {
         *          test_name: name_of_test,
         *          line_data_test_results: [{x: date, y: value }],
         *          line_data_reference: [{x: date, y: reference }],
         *          area_data_ok: [{x: date, y_high: tol_high, y_low: tol_low}],
         *          area_data_upper_tol: [{x: date, y_high: act_high, y_low: tol_high}],
         *          area_data_lower_tol: [{x: date, y_high: tol_low, y_low: act_low}]
         *      }
         * ]
         */

        var series = [];

        var colors = ['#001F3F', '#A47D7C', '#444444', '#ff851b', '#39CCCC', '#605ca8', '#00a65a', '#D81B60', '#3c8dbc'];

        d3.map(data).each(function (v, k, m) {

            var line_data_test_results = [],
                line_data_reference = [],
                area_data_ok = [],
                area_data_upper_tol = [],
                area_data_lower_tol = [],
                visible = true,
                ref_tol_visible = true;

            d3.map(v).each(function (val) {
                if (_.isNull(val.value)) {
                    return;
                }
                var x = moment(val.date).valueOf();

                line_data_test_results.push({x: x, y: val.value});

                if (val.reference) {
                    line_data_reference.push({x: x, y: val.reference});
                    area_data_ok.push({x: x, y_high: val.tol_high, y_low: val.tol_low});
                    area_data_upper_tol.push({x: x, y_high: val.act_high, y_low: val.tol_high});
                    area_data_lower_tol.push({x: x, y_high: val.tol_low, y_low: val.act_low});
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
                ref_tol_visible: ref_tol_visible
            });
        });

        return series;
    }

    function create_chart(series_data) {

        var ntests = QAUtils.get_checked("#test-container").length;

        // var allEmpty = _.every(_.map(series_data, function (o) {
        //     return o.data.length === 0
        // }));
        // if (allEmpty) {
        //     return;
        // }
        var range = $('#date-range');
        var from = range.val().split(' - ')[0];
        var to = range.val().split(' - ')[1];

        ///////////////////////// CHART
        var chart_height = 700,
            chart_width = $('#chart').width(),
            xAxisHeight = 20;

        var circle_radius = 2,
            circle_radius_highlight = 3,
            line_width = 1.5,
            line_width_highlight = 2.5;

        var margin = {top: 20, right: 30, bottom: 140, left: 30},
            margin2 = {top: chart_height - margin.bottom, right: 10, bottom: 20, left: 30},
            legend_collapse_width = 50,
            width = chart_width - margin.left - margin.right - legend_collapse_width,
            height = chart_height - margin.top - margin.bottom,
            height2 = margin.bottom - 2 * xAxisHeight - 10 - margin2.bottom,
            legend_width = legend_collapse_width;

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
            .x(function(d) { return xScale(d.x); })
            .y(function(d) { return yScale(d.y); })
            .defined(function(d) { return d.y != null; });

        var line2 = d3.line()
            .curve(d3.curveLinear)
            .x(function(d) { return xScale2(d.x); })
            .y(function(d) { return yScale2(d.y); })
            .defined(function(d) { return d.y != null; });

        var area = d3.area()
            .x(function(d) { return xScale(d.x); })
            .y0(function(d) { return yScale(d.y_low); })
            .y1(function(d) { return yScale(d.y_high); })
            .defined(function(d) { return d.y_high - d.y_low > 0; });

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

        ///////////// Create invisible rect for mouse tracking
        var mouse_tracker = svg.append("rect")
            .attr("width", width)
            .attr("height", height)
            .attr("id", "mouse-tracker")
            .style("fill", 'transparent');

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

        xScale.domain([moment(from, "DD-MM-YYYY").valueOf(), moment(to, "DD-MM-YYYY").valueOf()]);
        var maxY = findMaxY(series_data, xScale.domain());
        var minY = findMinY(series_data, xScale.domain());
        
        yScale.domain(yBuff(minY, maxY));
        yScale2.domain([minY, maxY]);
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
                .data(series_data)
            .enter().append("path")
                .attr("class", "line context-path")
                .attr("d",  function(d) { return line2(d.line_data_test_results); })
                .style('stroke-width', line_width)
                .style("stroke", function(d) { return d.color; })
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
                .data(series_data)
            .enter()
                .append("g")
                    .attr("class", "test");
        
        // Draw ok area:
        var test_ok = test.append('g')
            .attr('class', 'test-ok');

        test_ok.append('path')
            .attr('class', 'area ok')
            .style("pointer-events", "none")
            .attr("id", function(d) {
                return "area_ok_" + d.test_name.replace(/\W+/g, "_")
            })
            .attr("d", function(d) {
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
            .attr("id", function(d) {
                return "area_upper_tol_" + d.test_name.replace(/\W+/g, "_")
            })
            .attr("d", function(d) {
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
            .attr("id", function(d) {
                return "area_lower_tol_" + d.test_name.replace(/\W+/g, "_")
            })
            .attr("d", function(d) {
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
            .attr("id", function(d) {
                return "line_result_" + d.test_name.replace(/\W+/g, "_");
            })
            .attr("d", function(d) {
                return d.visible ? line(d.line_data_test_results) : null; // If array key "visible" = true then draw line, if not then don't
            })
            .attr("clip-path", "url(#clip)")//use clip path to make irrelevant part invisible
            .attr('stroke-width', line_width)
            .style("stroke", function(d) { return d.color; });

        test_result.selectAll("circle")
            .data(function(d) {
                return d.line_data_test_results; })
            .enter().append('circle')
                // .style("pointer-events", "none") // Stop line interferring with cursor
                .attr("clip-path", "url(#clip)")
                .attr("stroke-width", 1)
                .attr("stroke", function(d, i, s) { return s[i].parentNode.__data__.color; })
                .attr("cx", function (d) { return xScale(d.x); })
                .attr("cy", function (d) { return yScale(d.y); })
                .attr("r", circle_radius)
                .attr("fill", "white").attr("fill-opacity", .5)

                .on('mousemove', mousemove);

        var test_reference = test.append('g')
            .attr('class', 'test-reference');

        test_reference.append('path')
            .attr("class", "line results")
            .style("pointer-events", "none") // Stop line interferring with cursor
            .style("stroke-dasharray", ("3, 3"))
            .attr("id", function(d) {
                return "line_reference_" + d.test_name.replace(/\W+/g, "_");
            })
            .attr("d", function(d) {
                return d.visible && d.ref_tol_visible ? line(d.line_data_reference) : null; // If array key "visible" = true then draw line, if not then don't
            })
            .attr("clip-path", "url(#clip)")
            .style("stroke", function(d) { return d.color; })
            .style('stroke-width', line_width)
            .style('opacity', 0.7);
        
        ////////////////////// legend
        var legendRowHeight = 25;

        var legend = svg.append('g')
                .attr("clip-path", "url(#clip-legend)")
            .append('g')
                .attr('transform', 'translate(' + width + ', 0)')
                .attr('class', 'legend');

            // .attr('transform', 'translate(' + (width - 50) + ', 0)');

        legend.append('rect')
            .attr("height", legendRowHeight * series_data.length + 30)
            .attr('width', 10)
            .attr('id', 'legend-rect')
            .style('fill', 'rgba(244, 244, 244, 0.5')
            .style('stroke', '#ddd')
            .style('stroke-width', 1);

        var legend_entry = legend.selectAll('.legend-row')
                .data(series_data)
            .enter().append("g")
                .attr("transform", function(d, i) { return "translate(0," + ((i + 1) * legendRowHeight - 8) + ")"; })
                .attr('class', 'legend-row');

        legend_entry.append("rect")
            .attr("width", 10)
            .attr("height", 10)
            .attr("x", 10)
            .attr("fill", function (d) { return d.visible ? d.color : "#F1F1F2"; })
            .attr('id', function(d, i) { return 'tsb_' + i })
            .attr("class", "toggle-series-box")

            .on("click", function (d, i, s) {

                d.visible = !d.visible;

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
                                .style("fill", 'rgba(0, 166, 90, 0.3')
                                .attr('stroke-width', 0.5);
                    }
                }
                redrawMainContent();
            })

            .on("mouseover", function (d) {

                if (!d.visible) {
                    d3.select(this)
                        .transition()
                        .attr("fill", function (d) {
                            return d.color;
                        });
                }

                if (d.visible) {
                    d3.select('#line_result_' + d.test_name.replace(/\W+/g, "_"))
                        .transition()
                        .attr("stroke-width", line_width_highlight);
                }
            })

            .on("mouseout", function (d) {

                if (!d.visible) {
                    d3.select(this)
                        .transition()
                        .attr("fill", "#ddd");
                }

                if (d.visible) {
                    d3.select('#line_result_' + d.test_name.replace(/\W+/g, "_"))
                        .transition()
                        .attr("stroke-width", line_width);
                }

            });

        legend_entry.append('rect')
            .attr("width", 10)
            .attr("height", 10)
            .attr("x", 30)
            .style('fill', 'rgba(0, 166, 90, 0.3')
            .style('stroke', function (d) { return d.color; })
            .style("stroke-dasharray", ("2, 2"))
            .attr('stroke-width', function (d) { return d.ref_tol_visible ? 0.5 : 0; })
            .attr("class", "toggle-ref-tol-box")
            .attr('id', function(d, i) { return 'trtb_' + i })

            .on("click", function (d, i, s) {
                d.ref_tol_visible = !d.ref_tol_visible;
                redrawMainContent();
            })

            .on("mouseover", function (d) {

                if (!d.ref_tol_visible && d.visible) {
                    d3.select(this)
                        .transition()
                        .style("fill", 'rgba(0, 166, 90, 0.3')
                        .attr('stroke-width', 0.5);
                }

                if (d.visible) {

                    d3.selectAll(
                            '#area_ok_' + d.test_name.replace(/\W+/g, "_") +
                            ',#area_upper_tol_' + d.test_name.replace(/\W+/g, "_") +
                            ',#area_lower_tol_' + d.test_name.replace(/\W+/g, "_")
                        )
                        .transition()
                        .attr('opacity', 0.3);
                }

            })

            .on("mouseout", function (d) {

                if (!d.ref_tol_visible && d.visible) {
                    d3.select(this)
                        .transition()
                        .attr('stroke-width', 0)
                        .style('fill', '#ddd');
                }

                if (d.visible) {

                    if (d.ref_tol_visible) {
                        d3.selectAll(
                                '#area_ok_' + d.test_name.replace(/\W+/g, "_") +
                                ',#area_upper_tol_' + d.test_name.replace(/\W+/g, "_") +
                                ',#area_lower_tol_' + d.test_name.replace(/\W+/g, "_")
                            )
                            .transition()
                            .attr('opacity', 0.1);
                    }
                }

            });

        legend_entry.append("text")
            .attr("x", 50)
            .attr('y', 8)
            // .attr('clip-path', 'url(#clip)')
            .text(function(d) { return d.test_name; })
            .style('font-size', 12);

        // resize legend box
        var largest_entry = 0;
        legend_entry.each(function() {
            largest_entry = d3.max([largest_entry, d3.select(this).select('text').node().getBBox().width]);
        });
        var legend_expand_width = largest_entry + 60;
        legend.select('#legend-rect').attr('width', legend_expand_width);

        var legend_toggle = legend.selectAll('.legend-toggle')
                .data([{ expanded: false }])
            .enter().append('rect')
                .attr('id', 'legend-toggle')
                .attr('class', 'legend-toggle btn btn-primary btn-flat')
                .attr('width', 40)
                .attr('height', 14)
                .attr('x', 5)
                .attr('y', legendRowHeight * series_data.length + 10)
                .style('fill', '#3c8dbc')
                .style('cursor', 'pointer')
                .style('stroke', '#367fa9')
                .style('stroke-width', '0.9px');

        legend_toggle.on('click', function(d, i, s) {
                d.expanded = !d.expanded;
                toggleLegend(d.expanded);
            })
            .on('mouseover', function() {
                d3.select(this).style('fill', '#367fa9').style('stroke', '#204d74');
            })
            .on('mouseout', function() {
                d3.select(this).style('fill', '#3c8dbc').style('stroke', '#367fa9');
            });

        var toogle_text = legend.append('text')
            .attr('width', 30)
            .attr('height', 10)
            .attr("x", 8)
            .attr("y", legendRowHeight * series_data.length + 20)
            .style("pointer-events", "none")
            .style('font', '10px sans-serif')
            .style('fill', '#fff')
            .text('\u25C0 show');

        var cheatLine = svg.append('line')
            .attr('x2', width + legend_collapse_width)
            .attr('y2', 0)
            .attr('x1', width + legend_collapse_width)
            .attr('y1', legendRowHeight * series_data.length + 30)
            .style('stroke', '#ddd');

        ///////////////// Date display
        var hoverDate = hoverLineGroup
            .append('text')
                .attr("class", "hover-text")
                .attr("y", 20)
                .attr("x", width - 170);

        // Add mouseover events for hover line.
        var old_x_closest,
            format = d3.timeFormat('%a, %b %e, %Y at %H:%M');

        d3.select("#mouse-tracker")
            .on("mousemove", mousemove)
            .on("mouseout", function () {
                hoverDate.text(null);

                d3.select("#hover-line")
                    .style("opacity", 0);

                d3.select('#context-hover-line')
                    .style('opacity', 0);

                d3.selectAll('circle[r="' + circle_radius_highlight + '"]')
                    .attr('r', circle_radius)
                    .attr('stroke-width', 1);

                old_x_closest = null;
            });

        // lower y axis behind #mouse-tracker to prevent mouse interactions on gridlines.
        d3.select('.y.axis').lower();

        // resize everything on window resize
        d3.select(window).on('resize', function() {

            chart_width = $('#chart').width();
            width = chart_width - margin.left - margin.right - legend_width;

            d3.select("svg").transition().attr("width", chart_width);
            svg.transition().attr('width', chart_width - margin.left);

            legend.transition().attr('transform', 'translate(' + width + ', 0)');
            legendClip.transition().attr("width", width + legend_collapse_width);
            cheatLine.transition()
                .attr('x1', width + legend_collapse_width)
                .attr('x2', width + legend_collapse_width);

            redrawMainXAxis();
            redrawMainContent();
            redrawContextXAxis();
        });

        function toggleLegend(expanded) {

            legend_width = expanded ? legend_expand_width : legend_collapse_width;
            width = chart_width - margin.left - margin.right - legend_width;

            legend.transition()
                .attr('transform', 'translate(' + width + ', 0)');

            if (expanded) toogle_text.text('hide \u25B6');
            else toogle_text.text('\u25C0 show');

            redrawMainXAxis();
            redrawMainContent();

        }

        function yBuff(minY, maxY) {
            var y_buff = (maxY - minY) * 0.1;
            return [minY - y_buff, maxY + y_buff];
        }

        /**
         * redraw axis along x. Used for legend collapse and expand
         */
        function redrawMainXAxis() {

            xScale.range([0, width]);

            mouse_tracker.transition().attr('width', width);
            mainClip.transition().attr('width', width);
            x_axis_elem.transition().call(xAxis);
            yAxis.tickSizeInner(-width);
            hoverDate.transition().attr("x", width - 170);

        }

        function redrawContextXAxis() {

            var east_bound_date = xScale.invert(width),
                west_bound_date = xScale.invert(0),
                east_selection_bound = xScale2(east_bound_date),
                west_selection_bound = xScale2(west_bound_date),
                context_width = width + legend_width - legend_collapse_width;

            xScale2.range([0, context_width]);

            x_axis2_elem.transition().call(xAxis2);
            context_path.transition().attr("d",  function(d) { return line2(d.line_data_test_results); });
            brush.extent([[0, 0], [context_width, height2]]);
            brush_elem.call(brush);

            // TODO resize/move selection and move handles

        }
        
        /**
         *  redraw everything (x axis not included here, see brushed())
         */
        function redrawMainContent() {

            maxY = findMaxY(series_data, xScale.domain());
            minY = findMinY(series_data, xScale.domain());
            yScale.domain(yBuff(minY, maxY));

            svg.select(".y.axis")
                .transition()
                .call(yAxis);

            // main line
            test_result.selectAll('path')
                .transition()
                .attr("d", function (d) {
                    return d.visible ? line(d.line_data_test_results) : null;
                });

            // markers
            test_result.filter(function(d) { return d.visible; }).selectAll("circle")
                .transition()
                    .attr("cy", function (d) { return yScale(d.y); })
                    .attr("cx", function (d) { return xScale(d.x); })
                    .on("end", function() {
                        d3.select(this).attr('visibility', 'visible');
                    });
            test_result.filter(function(d) { return !d.visible; }).selectAll("circle")
                .transition()
                    .attr("cy", function (d) { return yScale(d.y); })
                    .attr("cx", function (d) { return xScale(d.x); })
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
                .attr('d', function(d) {
                    return d.visible && d.ref_tol_visible ? area(d.area_data_ok) : null;
                });
            test_upper_tol.selectAll('path')
                .transition()
                .attr('d', function(d) {
                    return d.visible && d.ref_tol_visible ? area(d.area_data_upper_tol) : null;
                });
            test_lower_tol.selectAll('path')
                .transition()
                .attr('d', function(d) {
                    return d.visible && d.ref_tol_visible ? area(d.area_data_lower_tol) : null;
                });

            // Context path update
            context_path
                .transition()
                .style('opacity', function(d) { return d.visible ? 1 : 0.2; })
        }

        function mousemove() {

            var mouse_x = d3.mouse(this)[0]; // Finding mouse x position on rect

            var x0 = xScale.invert(mouse_x);
            var x_closest = findClosestX(x0);

            if (x_closest != old_x_closest) {

                old_x_closest = x_closest;
                
                hoverDate.text(format(x_closest)); // scale mouse position to xScale date and format it to show month and year

                d3.selectAll('circle[r="' + circle_radius_highlight + '"]')
                    .attr('r', circle_radius)
                    .attr('stroke-width', 1);

                d3.selectAll('circle')
                    .filter(function (d) { return d.x == x_closest; })
                    .attr('r', circle_radius_highlight)
                    .attr('stroke-width', 2);

                d3.select("#hover-line") // select hover-line and changing attributes to mouse position
                    .attr("x1", xScale(x_closest))
                    .attr("x2", xScale(x_closest))
                    .style("opacity", 1); // Making line visible

                d3.select('#context-hover-line')
                    .attr('x1', xScale2(x_closest))
                    .attr('x2', xScale2(x_closest))
                    .style('opacity', 0.3)

            }
        }

        //for brusher of the slider bar at the bottom
        function brushed() {

            var selection = d3.event.selection;
            var date_range = selection.map(xScale2.invert, xScale2);
            xScale.domain(date_range);

            x_axis_elem.transition().call(xAxis);

            redrawMainContent();
        }

        function findMaxY(data, range){  // Define function "findMaxY"
            var maxYValues = data.map(function(d) {
                if (d.visible){

                    var maxY = null;
                    if (d.ref_tol_visible) {

                        var y, series_array = [d.line_data_test_results, d.line_data_reference, d.area_data_ok, d.area_data_upper_tol, d.area_data_lower_tol];
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
                        maxY = d3.max(d.line_data_test_results, function(value) {
                            if (value.x > range[0].valueOf() && value.x < range[1].valueOf()) {
                                return value.y;
                            }
                            else {
                                return null;
                            }
                        })
                    }
                    return maxY;
                }
            });

            return d3.max(maxYValues) || 0;
        }

        function findMinY(data, range){  // Define function "findMaxY"
            var minYValues = data.map(function(d) {
                if (d.visible){

                    var minY = null;
                    if (d.ref_tol_visible) {

                        var y, series_array = [d.line_data_test_results, d.line_data_reference, d.area_data_ok, d.area_data_upper_tol, d.area_data_lower_tol];
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
                        minY = d3.min(d.line_data_test_results, function(value) {
                            if (value.x > range[0].valueOf() && value.x < range[1].valueOf()) {
                                return value.y;
                            }
                            else {
                                return Infinity;
                            }
                        })
                    }
                    return minY;
                }
            });

            var to_return = d3.min(minYValues) || 0;
            return to_return == Infinity ? 0 : to_return;
        }

        function findClosestX (x) {

            var best_x = 0, best_dist = Infinity,
                bi_left = d3.bisector(function(d) { return d.x }).left;

            d3.map(series_data).each(function(val) {

                if (val.visible) {
                    var v = val.line_data_test_results,
                        i = bi_left(v, x),
                        d1,
                        d2;

                    if (i == 0) {
                        d1 = Infinity;
                    }
                    else {
                        d1 = x - v[i - 1].x;
                    }
                    if (i == v.length) {
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
        }
    }

    function get_legend_options() {
        var legend = {};
        if ($("#show-legend").is(":checked")) {
            legend = {
                align: "right",
                layout: "vertical",
                enabled: true,
                verticalAlign: "middle"
            }
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
        $("#control-chart-container").find("img, div.please-wait, div.cc-error").remove();
        $("#control-chart-container").append("<img/>");
        $("#control-chart-container img").error(control_chart_error);
        $("#control-chart-container").append('<div class="please-wait"><em>Please wait for control chart to be generated...this could take a few minutes.</em></div>');

        waiting_timeout = setInterval("check_cc_loaded()", 250);
        var chart_src_url = get_control_chart_url();
        $("#control-chart-container img").attr("src", chart_src_url);
    }

    function check_cc_loaded() {

        if ($("#control-chart-container img").height() > 100) {
            control_chart_finished();
        }
    }

    function control_chart_error() {
        control_chart_finished();
        $("#control-chart-container img").remove();
        $("#control-chart-container").append('<div class="cc-error">Something went wrong while generating your control chart</div>');
    }

    function control_chart_finished() {
        $("#control-chart-container div.please-wait").remove();
        $("#data-table-wrapper").html("");
        clearInterval(waiting_timeout);
        retrieve_data(update_data_table);
    }

    function get_control_chart_url() {
        var filters = get_data_filters();

        var props = [
            "width=" + $("#chart-container").width(),
            "height=" + $("#chart").height(),
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
        var unit_ids, test_ids, freq_ids, test_list_ids;

        var options = QAURLs.options_from_url_hash(document.location.hash);

        var units = get_filtered_option_values("units", options);
        var tests = get_filtered_option_values("tests", options);
        var test_lists = get_filtered_option_values("test_lists", options);

        if ((units.length === 0) || (tests.length === 0)) {
            return;
        }

        unit_ids = _.map(units, function (pk) {
            return "#unit-" + pk;
        });
        test_ids = _.map(tests, function (pk) {
            return "#test-" + pk;
        });
        test_list_ids = _.map(test_lists, function (pk) {
            return "#test-list-" + pk;
        });

        var filters = ["#unit-container", "#frequency-container", "#test-list-container .checkbox-container"];

        _.map(filters, show_all_inputs);

        QAUtils.set_checked_state(unit_ids, true);

        set_frequencies();
        set_test_lists(function () {
            QAUtils.set_checked_state(test_list_ids, true);
            set_tests(function () {
                QAUtils.set_checked_state(test_ids, true);
                update_chart();
            });
        });
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

});