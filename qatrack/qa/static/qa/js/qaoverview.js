require(['jquery', 'moment', 'lodash', 'felter'], function ($, moment, _) {
    function unit_container_id(option) {
        return $(option).val();
    }

    var all_unit_boxes = {};

    function filter_units() {
        var units_to_show;

        if ($("#all-option").is(":selected")) {
            units_to_show = _.map($(".unit-option"), unit_container_id);
        } else {
            units_to_show = _.map($("#unit-filter option:selected"), unit_container_id);
        }

        for (var aub in all_unit_boxes) {
            all_unit_boxes[aub]['show'] = _.includes(units_to_show, aub);
        }
        add_unit_boxes();
    }

    function add_unit_boxes() {
        var sections = $('.unit-box-section');
        // $('.unit-box-section').html('');
        var counters = [0, 0, 0];

        for (var ub in all_unit_boxes) {
            if (all_unit_boxes[ub]['show']) {
                var add_to = _.indexOf(counters, _.min(counters));
                $(sections[add_to]).append(all_unit_boxes[ub]['box']);
                counters[add_to] += $(all_unit_boxes[ub]['box']).height();
            }
            else {
                $('#box-' + ub).remove();
            }
        }
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
        if (date) date = moment(ti.due_date).format("D MMM YYYY");
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
        // var added_boxes = [];
        // var counters = [0, 0, 0];
        for (var unit in unit_lists) {
            
            var unit_slug = unit.replace(/ /g, '_');
            // var rows_added = 3;
            var unit_div = $($('#unit-template').html().replace(/__UNITDISPLAYNAME__/g, unit).replace(/__UNITNAME__/g, unit_slug));
            var freq_container = unit_div.find('tbody');
            var add_it = false;

            for (var freq in unit_lists[unit]) {

                if (!_.isEmpty(unit_lists[unit][freq])) {
                    freq_container.append($('<tr>').append($('<td colspan="3"><b>' + freq + '</b></td>')));
                    // rows_added++;

                    for (var ti in unit_lists[unit][freq]) {
                        freq_container.append($('<tr class="testlist-row"></tr>')
                            .append($('<td>', {class: 'testlist-link'}).append(create_utc_link(ti, unit_lists[unit][freq][ti])))
                            .append($('<td>', {class: 'testlist-due-date'}).append(create_due_date(unit_lists[unit][freq][ti])))
                            .append($('<td>', {class: 'testlist-last-status'}).append(create_status(unit_lists[unit][freq][ti].last_instance_status)))
                        );
                        // rows_added++;
                    }
                    add_it = true;
                }
            }

            if (add_it) {

                unit_filter.append($('<option>', {
                    value: unit_slug,
                    text: unit,
                    selected: 'selected',
                    class: 'unit-option'
                }));

                all_unit_boxes[unit_slug] = {
                    'show': true,
                    'box': unit_div[0]
                }
            }
        }

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
            slimscroll: true,
            // filters: {
            //     showInactiveUnits: {
            //         selected: false,
            //         run_filter_when_selected: false,   // No, run filter when not selected
            //         label: 'Show Inactive Units',
            //         filter: function(obj_data) {
            //             return $(obj_data.$option).attr('data-active') === 'True';
            //         }
            //     }
            // }
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