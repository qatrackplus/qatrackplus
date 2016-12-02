

require(['jquery', 'lodash', 'moment', 'autosize', 'select2', 'daterangepicker', 'sl_utils', 'jquery.inputmask'], function ($, _, moment, autosize) {
    
    $(document).ready(function() {

        var $units = $('#id_unit_field'),
            $service_areas = $('#id_service_area_field'),
            $related_se = $('#id_service_event_related_field'),
            $service_status = $('#id_service_status'),
            $problem_type = $('#id_problem_type'),
            $service_type = $('#id_service_type'),
            $approval_required = $('#id_is_approval_required');

        // General fields ------------------------------------------------------------------------------
        autosize($('textarea.autosize'));

        $('.select2:visible').select2({
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
        
        $('.inputmask').inputmask('99:99', {numericInput: true, placeholder: "_", removeMaskOnSubmit: true});
        
        // Service Event status -----------------------------------------------------------------
        function generate_status_label(status) {
            if (status.id) {
                var colour = status_colours_dict[status.id];
                var $label = $('<span class="label" style="background-color: ' + colour + '">' + status.text + '</span>');
                $label.css('background-color', colour);
                $label.css('border-color', colour);
                if (isTooBright(rgbaStringToArray(colour))) {
                    $label.css('color', 'black').children().css('color', 'black');
                }
                return $label;
            }
            return status.text;
        }
        $service_status.select2({
            templateResult: generate_status_label,
            templateSelection: generate_status_label,
            minimumResultsForSearch: 10,
            width: '100%'
        });

        // Service Type and Approval Required --------------------------------------------------------------
        $service_type.change(function() {
            $approval_required.prop('disabled', se_types_approval[$service_type.val()]);
            $approval_required.prop('checked', se_types_approval[$service_type.val()]);
        });
        
        // Service Events Related ------------------------------------------------------------------------------
        function generate_related_result(res) {
            if (res.loading) { return res.text; }
            var colour = status_colours_dict[se_statuses[res.id]];
            var $div = $('<div class="select2-result-repository clearfix">' + res.text + '<div class="label pull-right" style="background-color: ' + colour + ';">&nbsp;</div></div>');
            return $div;
        }
        function generate_related_selection(res, container) {
            var colour = status_colours_dict[se_statuses[res.id]];
            $(container).css('background-color', colour);
            $(container).css('border-color', colour);
            if (isTooBright(rgbaStringToArray(colour))) {
                $(container).css('color', 'black').children().css('color', 'black');
            }
            var $label = $('<span>' + res.text + '<i class="fa fa-square fa-lg pull-right" style="color: ' + colour + ';"></i></span>');
            return $label;
        }
        function process_related_results(data, params) {
            // console.log(data);
            // console.log(params);
            var results = [];
            for (var i in data.colour_ids) {
                var se_id = data.colour_ids[i][0],
                    s_id = data.colour_ids[i][1],
                    se_srn = data.colour_ids[i][2];
                results.push({id: se_id, text: 'id: ' + se_id + ' srn: ' + se_srn})
                se_statuses[se_id] = s_id;
            }
            params.page = params.page || 1;
            return {
                results: results,
                pagination: {
                    more: (params.page * 30) < data.total_count
                }
            };
        }
        $related_se.select2({

            ajax: {
                url: QAURLs.SE_SEARCHER,
                dataType: 'json',
                delay: '500',
                data: function (params) {
                    return {
                        q: params.term, // search term
                        page: params.page
                    }
                },
                processResults: process_related_results,
                cache: true
            },
            escapeMarkup: function (markup) { return markup; },
            minimumInputLength: 1,
            templateResult: generate_related_result,
            templateSelection: generate_related_selection,
            width: '100%'
        });

        // Problem Type --------------------------------------------------------------------------------------------
        $problem_type.select2({
            tags: true,
            placeholder: 'Enter new or search for problem type',
            allowClear: true,
            createTag: function (params) {
                return {
                    id: params.term,
                    text: params.term,
                    newOption: true
                }
            },
            templateResult: function (data) {
                var $result = $("<span></span>");
                $result.text(data.text);
                if (data.newOption) {
                    $result.append(" <em>(new)</em>");
                }
                return $result;
            },
            // minimumResultsForSearch: 10,
            width: '100%'
        });
        
        // Unit -----------------------------------------------------------------------------------------------
        $units.change(function() {
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
        
        // Hours Formset --------------------------------------------------------------------------------------
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

        // Qafollowup Formset --------------------------------------------------------------------------------
        var $select_tli = $('.select-tli');
        $select_tli.click(function(event) {
            var w = window.open($(this).attr('data-link'), '_blank', 'scrollbars=no,menubar=no,height=900,width=1200,resizable=yes,toolbar=yes,status=no');
            w.focus();
        });
        displayTLI = function(prefix, data) {
            var $label_group = $('<span class="label-group"></span>');
            for (var status in data['pass_fail']) {
                if (data['pass_fail'][status] > 0 && status != 'no_tol') {
                    var $label = $('<span class="label ' + status + '" title="' + data['pass_fail'][status] + ' ' + status + '"></span>');
                    if (status == 'ok') {
                        $label.append('<i class="fa fa-check-circle-o" aria-hidden="true"></i>');
                    } else if (status == 'action') {
                        $label.append('<i class="fa fa-ban" aria-hidden="true"></i>');
                    } else if (status == 'tolerance') {
                        $label.append('<i class="fa fa-exclamation-circle" aria-hidden="true"></i>');
                    } else if (status == 'not_done') {
                        $label.append('<i class="fa fa-circle-o" aria-hidden="true"></i>');
                    }
                    $label.append(' ' + data['pass_fail'][status]);
                    $label_group.append($label);
                }
            }
            $('#pass-fail-' + prefix).html($label_group);
            $label_group = $('<span class="label-group"></span>');
            for (status in data['review']) {
                var label_class = 'label',
                    icon = '';
                if (!data['review'][status]['valid']) {
                    label_class += ' label-important';
                    icon = '<i class="icon-minus-sign"></i>';
                } else if (data['review'][status]['reqs_approval']) {
                    label_class += ' label-warning';
                    icon = '<i class="icon-question-sign"></i>';
                } else {
                    label_class += ' label-success';
                }
                $label_group.append('<span class="' + label_class + '">' + icon + ' ' + data["review"][status]["num"] + ' ' + status + '</span>');
            }
            $('#review-' + prefix).html($label_group);
        };
        setSearchResult = function(followup_form, returnValue){
            // TODO
            window.focus();
            $('#id_' + followup_form + '-test_list_instance').val(returnValue);
            $.ajax({
                url: QAURLs.TLI_STATUSES,
                data: {'tli_id': returnValue},
                success: function(res) {
                    displayTLI(followup_form, res);
                }
            })
        };
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