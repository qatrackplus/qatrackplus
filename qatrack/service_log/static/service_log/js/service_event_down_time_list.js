require(['jquery', 'moment'], function ($, moment) {
    $(document).ready(function () {

        var $go_down_time = $('#go_down_time');

        function get_filters() {
            var filters = {
                datetime_service: $('input.text_filter[rel=1]:not(.search_init)').val(),
                unit: $('select.select_filter[rel=2]').val(),
                service_area: $('select.select_filter[rel=3]').val(),
                service_type: $('select.select_filter[rel=4]').val(),
                problem_description: $('input.text_filter[rel=5]:not(.search_init)').val()
            };
            var f = [];
            for (var filt in filters) {
                console.log(filters[filt]);
                if (!(typeof filters[filt] === 'undefined') && filters[filt] !== null && filters[filt] !== '') {
                    if (filt === 'datetime_service') {
                        console.log(moment(filters[filt].split(' - ')[0]).format('DD-MM-YYYY'));
                        var date_from = moment(filters[filt].split(' - ')[0]);
                        var date_to = moment(filters[filt].split(' - ')[1]);
                        f.push(filt + '=' + date_from.format('DD-MM-YYYY') + '--' + date_to.format('DD-MM-YYYY'));
                    } else {
                        f.push(filt + '=' + filters[filt]);
                    }
                }
            }
            return f.join('&');
        }

        $go_down_time.click(function () {
            var f = get_filters();
            console.log(f);
            window.location = QAURLs.GO_SE_DOWN_TIMES + '?' + f + ';';
        });

    });
});
