require(['jquery', 'moment'], function ($, moment) {
    $(document).ready(function () {

        var $go_down_time = $('#go_down_time');

        function get_filters() {

            var units = $('select.select_filter[rel=2]').val(),
                daterange = $('input.text_filter[rel=1]').val(),
                service_area = $('select.select_filter[rel=5]').val(),
                unit_type = $('select.select_filter[rel=3]').val(),
                active = $('select.select_filter[rel=4]').val(),
                problem_description = $('input.text_filter[rel=6]:not(.search_init)').val();

            var inputs = [];

            if (daterange) {
                inputs.push('daterange=' + daterange);
            }

            $.each(units, function (i, v) {
                inputs.push('unit=' + v);
            });

            $.each(service_area, function (i, v) {
                inputs.push('service_area=' + v);
            });

            $.each(unit_type, function (i, v) {
                inputs.push('unit__type=' + v);
            });

            if (active) {
                inputs.push('unit__active=' + active);
            }

            if (problem_description) {
                inputs.push('problem_description=' + problem_description);
            }

            return inputs.join('&');
        }

        $go_down_time.click(function () {

            var f = get_filters();
            window.location = QAURLs.HANDLE_UNIT_DOWN_TIME + '?' + f;

        });

    });
});
