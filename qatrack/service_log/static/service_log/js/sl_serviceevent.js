require(['jquery', 'lodash', 'moment', 'autosize', 'select2', 'daterangepicker'], function ($, _, moment, autosize) {

    function rgbStringToArray(rgba) {
        rgba = rgba.match(/^rgba\((\d+),\s*(\d+),\s*(\d+),(0(\.[0-9][0-9]?)?|1)\)$/);
        return [rgba[1], rgba[2], rgba[3], rgba[4]];
    }

    /**
     * Calculates the brightness of the rgba value assuming against a white surface. Returns true if white text would
     * not be appropriate on this colour.
     *
     * @param rgba
     * @returns {boolean}
     */
    function isTooBright(rgba) {
        var o = Math.round(((parseInt(rgba[0]) * 299) + (parseInt(rgba[1]) * 587) + (parseInt(rgba[2]) * 114)) / 1000);
        return o + (255 - o) * (1 - rgba[3]) > 125;
    }
    
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
                var colour = colours_dict[tag.id];
                $(container).css('background-color', colour);
                $(container).css('border-color', colour);
                if (isTooBright(rgbStringToArray(colour))) {
                    $(container).css('color', 'black').children().css('color', 'black');
                }
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
            // startDate: moment(),
            // endDate: moment()
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

                        $service_areas.find('option:not(:first)').remove();
                        var service_areas = response.service_areas;

                        if (service_areas.length > 0) {
                            for (var sa in service_areas) {
                                console.log(service_areas[sa]);
                                $service_areas.append('<option value=' + service_areas[sa].id + '>' + service_areas[sa].name + '</option>');
                            }
                        }
                        else {
                            $service_areas.append('<option value>No service areas found for unit</option>');
                        }

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