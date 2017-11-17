$(document).ready(function() {

    var $test = $('#id_test'),
        $test_list = $('#id_testlist'),
        $test_list_cycle = $('#id_testlistcycle'),
        $test_instance = $('#id_testinstance'),
        $test_list_instance = $('#id_testlistinstance');

    function format_selection(res) {
        return res.name || res.text;
    }
    function format_result(res) {
        return $('<div class="select2-result-repository">(' + res.id + ') ' + res.name + '</div>');
    }
    function set_data(params) {
        return {
            q: params.term,
            page: params.page
        };
    }
    function process_results(data, params) {
        params.page = params.page || 1;
        console.log(data);
        if (data.name) {
            $.each(data.items, function (i, v) {
                v.name = v[data.name];
            });
        }
        return {
            results: data.items,
            pagination: {
                more: (params.page * 30) < data.total_count
            }
        };
    }
    $test.select2({
        ajax: {
            url: admin_urls.TEST_SEARCHER,
            data: set_data,
            processResults: process_results,
            cache: true,
            delay: 500
        },
        allowClear: true,
        placeholder: '-------',
        minimumInputLength: 1,
        templateResult: format_result,
        templateSelection: format_selection
    });
    $test_list.select2({
        ajax: {
            url: admin_urls.TEST_LIST_SEARCHER,
            data: set_data,
            processResults: process_results,
            cache: true,
            delay: 500
        },
        allowClear: true,
        placeholder: '-------',
        minimumInputLength: 1,
        templateResult: format_result,
        templateSelection: format_selection
    });
    $test_list_cycle.select2({
        ajax: {
            url: admin_urls.TEST_LIST_CYCLE_SEARCHER,
            data: set_data,
            processResults: process_results,
            cache: true,
            delay: 500
        },
        allowClear: true,
        placeholder: '-------',
        minimumInputLength: 1,
        templateResult: format_result,
        templateSelection: format_selection
    });
    $test_instance.select2({
        ajax: {
            url: admin_urls.TEST_INSTANCE_SEARCHER,
            data: set_data,
            processResults: process_results,
            cache: true,
            delay: 500
        },
        allowClear: true,
        placeholder: '-------',
        minimumInputLength: 1,
        templateResult: format_result,
        templateSelection: format_selection
    });
    $test_list_instance.select2({
        ajax: {
            url: admin_urls.TEST_LIST_INSTANCE_SEARCHER,
            data: set_data,
            processResults: process_results,
            cache: true,
            delay: 500
        },
        allowClear: true,
        placeholder: '-------',
        minimumInputLength: 1,
        templateResult: format_result,
        templateSelection: format_selection
    });

});