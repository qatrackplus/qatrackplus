require(['jquery', 'moment', 'autosize', 'select2', 'site_base'], function ($, _) {

    $(document).ready(function() {

        let $se_template_create = $('#create_template'),
            $se_template_btn = $('.se-template-btn'),
            $se_template_form = $('#template_form'),
            $se_template_modal = $('#template-modal'),
            $template_unit = $('#template_unit'),
            $template_unit_fake = $template_unit.clone(true),
            $template_service_area = $('#template_service_area'),
            $template_service_type = $('#template_service_type'),
            $template_is_review_required = $('#template_is_review_required'),
            $template_problem_description = $('#template_problem_description'),
            $template_work_description = $('#template_work_description'),
            $template_utcs = $('#template_return_to_service_utcs'),
            $unit_message = $(
                // '<div class="row" style="display: none;">' +
                '<div class="col-lg-5"></div>' +
                '<div class="help-block col-lg-7">' +
                'Cannot change unit while service area or return to service selected.' +
                '</div>'
            );
        $template_unit_fake.prop('id', 'fake_units').prop('name', 'fake_units');
        $template_unit.parents('.form-group').append($unit_message);
        $template_unit_fake.insertAfter($template_unit);
        $template_unit.hide();


        $('.select2:visible').select2({
            minimumResultsForSearch: 10,
            width: '100%',
            templateSelection: function(a) {
                if (($(a.element).parent().prop('required') && a.id === '') || ($(a.element).parent().attr('id') === 'id_unit_field_fake' && a.id === '')) {
                    return $('<span class="required-option">required</span>');
                }
                return a.text;
            }
        });


        $template_unit_fake.change(function() {
            var unit_id = $template_unit_fake.val();
            $template_unit.val(unit_id);

            if ($(this).data('previous_val') === $(this).val()){
                return;
            }

            $(this).data('previous_val', $(this).val());

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

                        $template_service_area.find('option:not(:first)').remove();

                        var service_areas = response.service_areas;
                        if (service_areas.length > 0) {
                            for (var sa in service_areas) {
                                $template_service_area.append('<option value=' + service_areas[sa].id + '>' + service_areas[sa].name + '</option>');
                            }
                        }
                        else {
                            $template_service_area.append('<option value>No service areas found for unit</option>');
                        }
                        $template_service_area.prop('disabled', false);

                        $template_utcs.find('option:not(:first)').remove();

                        var utcs = response.utcs;
                        if (utcs.length > 0) {

                            $.each(response.utcs, function(i, v) {
                                $template_utcs.append('<option value=' + v.id + '>' + v.name + '</option>');
                            });
                        }
                        else {
                            $template_utcs.append('<option value>No test lists found for unit</option>');
                        }
                        $template_utcs.prop('disabled', false);
                    },
                    traditional: true,
                    error: function (e, data) {
                        console.log('ErrOr');
                    }
                });
            }
            else {
                $template_service_area.prop('disabled', true).find('option:not(:first)').remove();
                $template_utcs.prop('disabled', true).find('option:not(:first)').remove();
            }
        });

        let disable_units = function (force) {

            let disable = false;
            if (force) {
                disable = true;
            } else {
                $template_utcs.each(function () {
                    if ($(this).val()) {
                        disable = true;
                        return false;
                    }
                });
                if ($template_service_area.val()) {
                    disable = true;
                }
            }
            $template_unit_fake.prop('disabled', disable);
            disable ? $unit_message.slideDown('fast') : $unit_message.slideUp('fast');

        };

        $template_service_area.change(function() {
            disable_units();
        });

        $template_utcs.change(function () {
            disable_units();
        });

        disable_units();

    });
});
