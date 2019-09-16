require(['jquery', 'moment', 'lodash', 'felter'], function ($, moment, _) {
    function unit_container_id(option) {
        return $(option).val();
    }

    var all_unit_boxes = {};

    function filter_units() {
        var units_to_show;

        units_to_show = _.map($("#unit-filter option:selected"), unit_container_id);

        $.each(all_unit_boxes, function(k, v) {
            v['show'] = _.includes(units_to_show, k);
        });
        add_unit_boxes();
    }

    function add_unit_boxes() {
        var sections = $('.unit-box-section');
        var counters = [0, 0, 0];

        $.each(all_unit_boxes, function(k, v) {
            if (v['show']) {
                var add_to = _.indexOf(counters, _.min(counters));
                $(sections[add_to]).append(v['box']);
                counters[add_to] += $(v['box']).height();
            }
            else {
                $('#box-' + k).remove();
            }
        });
    }

    function create_utc_link(ti_name, ti) {
        return $('<a>', {
            href: ti.url,
            title: 'View history of ' + ti_name,
            text: ti_name
        });
    }

    function create_due_date(ti) {
        var status = ti.due_status,
            date = ti.due_date;
        if (date) date = moment(ti.due_date).format(siteConfig.MOMENT_DATE_FMT);
        else date = 'No Due Date';
        return $('<span>', {
            class: 'label due-status ' + status,
            text: date
        });
    }

    function create_status(last_instance_status) {
        if (last_instance_status == 'New List') {
            return $('<span></span>');
        }
        var label_group = $('<span></span>').addClass('label-group');
        for (var lis in last_instance_status) {
            label_group.append($('<span>', {
                title: last_instance_status[lis] + ' ' + lis,
                class: "badge " + lis,
                text: last_instance_status[lis]
            }));
        }
        return label_group;
    }

    function setup_units(unit_lists) {

        var unit_filter = $('#unit-filter');
        $.each(unit_lists, function(k1, unit) {

            var unit_slug = unit.unit_name.replace(/ /g, '_');
            var unit_name = unit.unit_name;

            var unit_div = $($('#unit-template').html().replace(/__UNITNAME__/g, unit_name).replace(/__UNITNUMBER__/g, k1));
            var freq_container = unit_div.find('tbody');
            var add_it = false;

            $.each(unit.unit_freqs, function(k2, freq) {

                if (!_.isEmpty(freq)) {
                    freq_container.append($('<tr>').append($('<td colspan="3"><b>' + k2 + '</b></td>')));
                    // rows_added++;

                    $.each(freq, function(k3, ti) {
                        freq_container.append($('<tr class="testlist-row"></tr>')
                            .append($('<td>', {class: 'testlist-link'}).append(create_utc_link(k3, ti)))
                            .append($('<td>', {class: 'testlist-due-date'}).append(create_due_date(ti)))
                            .append($('<td>', {class: 'testlist-last-status'}).append(create_status(ti.last_instance_status)))
                        );
                    });
                    add_it = true;
                }
            });

            if (add_it) {

                unit_filter.append($('<option>', {
                    value: k1,
                    text: unit_name,
                    selected: 'selected',
                    class: 'unit-option'
                }));

                all_unit_boxes[k1] = {
                    'show': true,
                    'box': unit_div[0]
                }
            }
        });

        add_unit_boxes();
        unit_filter.felter({
            mainDivClass: 'col-md-12',
            selectAllClass: 'btn btn-flat btn-xs btn-default',
            // choiceDivClass: 'row',
            label: 'Visible Units',
            initially_displayed: true,
            selectAll: true,
            selectNone: true,
            height: 250,
            slimscroll: true
        })
    }

    function set_counts(due_counts) {
        $('#due-count-ndd h3').text(due_counts.no_tol);
        $('#due-count-nd h3').text(due_counts.ok);
        $('#due-count-d h3').text(due_counts.tolerance);
        $('#due-count-od h3').text(due_counts.action);
    }

    /**************************************************************************/
    $(document).ready(function () {
        $("#unit-filter").change(filter_units);

        $.ajax({
            type: "GET",
            url: QAURLs.OVERVIEW_OBJECTS,
            contentType: "application/json",
            dataType: "json",
            data: {user: window.location.href.indexOf('overview-user') > -1},
            success: function (response) {
                set_counts(response.due_counts);
                setup_units(response.unit_lists);
                $('body').removeClass("loading");
            },
            error: function () {
                console.log('erRoR');
            }
        });

    });

});
