
require(['jquery', 'autosize', 'select2'], function ($, autosize) {

    $(document).ready(function() {

        var $submit_delete = $('#submit-delete'),
            $id_reason = $('#id_reason'),
            $delete_form = $('#service-event-delete-form');

        $id_reason.select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        autosize($('textarea.autosize'));

        $submit_delete.one('click', function (event) {
            event.preventDefault();
            $delete_form.submit();
            $(this).prop('disabled', true);
        });

    });
});