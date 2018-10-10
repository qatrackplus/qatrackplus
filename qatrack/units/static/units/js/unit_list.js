require(['jquery'], function ($) {
    $(document).ready(function () {

        var $pucs = $('#parts_units_cost_summary'),
            $ucat = $('#units_change_available_time'),
            $udt = $('#units_down_time');

        function get_filters() {
            var filters = {
                number: $('input.text_filter[rel=1]:not(.search_init)').val(),
                name: $('input.text_filter[rel=2]:not(.search_init)').val(),
                serial_number: $('input.text_filter[rel=3]:not(.search_init)').val(),
                active: $('select.select_filter[rel=4]').val(),
                // restricted: $('select.select_filter[rel=5]').val(),
                site: $('select.select_filter[rel=5]').val(),
                type__unit_class: $('select.select_filter[rel=6]').val(),
                type: $('select.select_filter[rel=7]').val(),
                type__vendor: $('select.select_filter[rel=8]').val()
            };
            var f = [];
            for (var filt in filters) {
                if (!(typeof filters[filt] === 'undefined') && filters[filt] !== null && filters[filt] !== '') {
                    f.push(filt + '=' + filters[filt]);
                }
            }
            return f.join('&');
        }

        $pucs.click(function () {
            var f = get_filters();
            window.location = QAURLs.PARTS_UNITS_COST + '?' + f + ';';
        });
        $ucat.click(function () {
            var f = get_filters();
            window.location = QAURLs.UNIT_AVAIL_TIME + '?' + f + ';';
        });

        $udt.click(function () {
            var f = get_filters();
            window.location = QAURLs.UNIT_DOWN_TIMES + '?' + f + ';';
        })

    });
});
