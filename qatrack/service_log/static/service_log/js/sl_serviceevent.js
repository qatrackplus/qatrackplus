require(['jquery', 'lodash', 'moment', 'autosize', 'select2', 'daterangepicker'], function ($, _, moment, autosize) {

    $(document).ready(function() {

        var $units = $('#id_unit_field'),
            $service_areas = $('#id_service_area_field'),
            $related_se = $('#id_service_event_related');

        autosize($('textarea.autosize'));

        $('.select2').select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        $related_se.select2({
            templateSelection: function(tag, container) {
                $(container).css('background-color', colours_dict[tag.id]);
                return tag.text;
            },
            minimumResultsForSearch: 10,
            width: '100%'
        });
        
        $('.daterangepicker-input').daterangepicker({
            singleDatePicker: true,
            autoClose: true,
            autoApply: true,
            keyboardNavigation: false,
            timePicker: true,
            timePicker24Hour: true,
            locale: {"format": "DD-MM-YYYY HH:mm"},
            startDate: moment(),
            endDate: moment()
        });

        $units.change(function() {

            var unit_id = $('#id_unit_field').val();

            if (unit_id) {
                var data = {
                    'unit_id': unit_id
                };

                $.ajax({
                    type: "GET",
                    url: QAURLs.UNIT_SERVICE_AREAS,
                    data: $.param(data),
                    dataType: "json",
                    success: function (response) {
                        console.log(response);
                        $service_areas.prop('disabled', false); 
                    },
                    traditional: true,
                    error: function (e, data) {
                        console.log('ErROr');
                    }
                });
            }

        });


    });

});