require(['jquery', 'lodash', 'moment', 'autosize', 'select2', 'daterangepicker', 'sl_utils', 'jquery.inputmask'], function ($, _, moment, autosize) {
    
    $(document).ready(function() {

        var $units = $('#id_unit_field'),
            $service_areas = $('#id_service_area_field'),
            $related_se = $('#id_service_event_related'),
            $service_status = $('#id_service_status');

        autosize($('textarea.autosize'));

        $('.select2:visible').select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        $service_status.select2({
            templateResult: function(status) {
                var colour = status_colours_dict[status.id];
                return $('<span><span class="label" style="background-color: ' + colour + '">&nbsp;</span>&nbsp;' + status.text + '</span>');
            },
            templateSelection: function(tag, container) {
                var colour = status_colours_dict[tag.id];
                var $label = $('<span class="label" style="background-color: ' + colour + '">' + tag.text + '</span>');
                $label.css('background-color', colour);
                $label.css('border-color', colour);
                if (isTooBright(rgbaStringToArray(colour))) {
                    $label.css('color', 'black').children().css('color', 'black');
                }
                return $label;
            },
            minimumResultsForSearch: 10,
            width: '100%'
        });

        $related_se.select2({
            templateSelection: function(tag, container) {
                var colour = se_colours_dict[tag.id];
                console.log(colour);
                $(container).css('background-color', colour);
                $(container).css('border-color', colour);
                if (isTooBright(rgbaStringToArray(colour))) {
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
            console.log('changing   ');
            var unit_id = $('#id_unit_field').val();

            if (unit_id) {
                var data = {
                    'unit_id': unit_id
                };

                $.ajax({
                    type: "GET",
                    url: QAURLs.UNIT_SA_UTC,
                    data: $.param(data),
                    dataType: "json",
                    success: function (response) {

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

                        var $utcs = $('.followup-utc');
                        $utcs.find('option:not(:first)').remove();
                        var utcs = response.utcs;
                        if (utcs.length > 0) {
                            for (var utc in utcs) {
                                console.log(utcs[utc]);
                                $utcs.append('<option value=' + utcs[utc].id + '>' + utcs[utc].name + '</option>');
                            }
                        }
                        else {
                            $utcs.append('<option value>No test lists found for unit</option>');
                        }
                        $utcs.prop('disabled', false);
                        
                    },
                    traditional: true,
                    error: function (e, data) {
                        console.log('ErROr');
                    }
                });
            }
            else {
                $service_areas.prop('disabled', true).find('option:not(:first)').remove();
                var $utcs = $('.followup-utc');
                $utcs.prop('disabled', true).find('option:not(:first)').remove();
            }

        });

        // if ($units.val()) {
        //     console.log($units.val());
        //     $units.change();
        // }

        $('.inputmask').inputmask('99:99', {numericInput: true, placeholder: "_", removeMaskOnSubmit: true});

        $('#add-hours').click(function() {

            var empty_hours_form = $('#empty-hours-form').html(),
                $hours_index = $('#id_hours-TOTAL_FORMS'),
                hours_index = $hours_index.val();

            $('#hours-tbody').append(empty_hours_form.replace(/__prefix__/g, hours_index));

            $('#id_hours-' + hours_index + '-user_or_thirdparty').select2({
                minimumResultsForSearch: 10,
                width: '100%'
            });
            $('#id_hours-' + hours_index + '-time').inputmask('99:99', {numericInput: true, placeholder: "_", removeMaskOnSubmit: true});

            $hours_index.val(parseInt(hours_index) + 1);
        });

        $('#add-followup').click(function() {

            var empty_followup_form = $('#empty-followup-form').html(),
                $followup_index = $('#id_followup-TOTAL_FORMS'),
                followup_index = $followup_index.val();

            $('#followup-tbody').append(empty_followup_form.replace(/__prefix__/g, followup_index));

            $('#id_followup-' + followup_index + '-unit_test_collection').select2({
                minimumResultsForSearch: 10,
                width: '100%'
            });

            $followup_index.val(parseInt(followup_index) + 1);
        });

    });

});