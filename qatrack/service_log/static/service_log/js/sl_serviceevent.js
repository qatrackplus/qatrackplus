// Regrets: Not using a more robust front end library here :(

require(['jquery', 'lodash', 'moment', 'autosize', 'select2', 'flatpickr', 'sl_utils', 'inputmask', 'site_base', 'comments', 'ping'], function ($, _, moment, autosize) {

    $(document).ready(function() {

        var $units = $('#id_unit_field'),
            $units_fake = $('#id_unit_field_fake'),
            $service_areas = $('#id_service_area_field'),
            $service_areas_fake = $('#id_service_area_field_fake'),
            $related_se = $('#id_service_event_related_field'),
            $service_status = $('#id_service_status'),
            $service_type = $('#id_service_type'),
            $service_time = $('#id_duration_service_time'),
            $review_required = $('#id_is_review_required'),
            $review_required_fake = $('#id_is_review_required_fake'),
            $problem_description = $('#id_problem_description'),
            $work_description = $('#id_work_description'),
            $utc_initiated_by = $('#id_initiated_utc_field'),
            $tli_initiated_by = $('#id_test_list_instance_initiated_by'),
            $tli_initiated_display_template = $('#tli_initiated_display_template'),
            $parts_used_parts = $('.parts-used-part:visible'),
            $parts_used_from_storage = $('.parts-used-from_storage:visible'),
            $tli_instances = $('.tli-instance'),
            $rtsqa_rows = $('.rtsqa-row'),
            $service_event_form = $('#service-event-form'),
            $service_save = $('.service-save'),
            $tli_display = $('<div class="row" style="display: none;"></div>'),
            $date_time = $('.daterangepicker-input'),
            $attachInput = $('#id_se_attachments'),
            $attach_deletes = $('.attach-delete'),
            $user_or_thirdparty = $('.user_or_thirdparty'),
            $attach_delete_ids = $('#id_se_attachments_delete_ids'),
            $attach_names = $('#se-attachment-names'),
            $all_inputs = $('input, select, textarea'),
            $template_service_area = $('#template_service_area'),
            $submit_cover = $('#submit_cover');

        $utc_initiated_by.parent().append($tli_display);
        $units_fake.val($units.val());
        $($units_fake).data('previous_val', $($units_fake).val());
        $service_areas_fake.val($service_areas.val());
        $($service_areas_fake).data('previous_val', $($service_areas_fake).val());

        $service_save.one('click', function (event) {
            $submit_cover.show();
            removeDisabled();
            event.preventDefault();
            $(window).off("beforeunload");
            disableTemplateFields(false);
            $service_event_form.submit();
            $(this).prop('disabled', true);
        });

        var changed = false;
        $all_inputs.change(function() {
            if ($(this).val()) {
                changed = true;
            }
        });
        if ($('.has-error').length > 0) {
            changed = true;
        }
        $(window).bind("beforeunload", function(){
            if (changed) {
                return  "If you leave this page now you will lose all entered values.";
            }
        });

        // General fields ------------------------------------------------------------------------------
        autosize($('textarea.autosize'));

        var s2 = $('.select2:visible, #template-modal .select2:not(#template_unit)').select2({
            minimumResultsForSearch: 10,
            width: '100%',
            templateSelection: function(a) {
                if (($(a.element).parent().prop('required') && a.id === '') || ($(a.element).parent().attr('id') === 'id_unit_field_fake' && a.id === '')) {
                    return $('<span class="required-option">required</span>');
                }
                return a.text;
            },
            templateResult: function(a) {
                if ($(a.element).parent().attr('id') === 'id_initiated_utc_field') {
                    return $('<span>' + a.text + '<span class="pull-right"><i class="fa fa-chevron-right new-tab-icon" aria-hidden="true"></i></span></span>');
                } else {
                    return a.text;
                }
            }
        })

        try {
          s2.overrideSelect2Keys();
        }catch(e) {
          // IE11 fail
        }

        $.each($date_time, function(idx, dt){
            var init_date = null;
            var $dt = $(dt);
            if (from_se_schedule && $dt.attr("id") === "id_datetime_service"){
                init_date = moment().format(siteConfig.MOMENT_DATETIME_FMT);
            }
            $dt.flatpickr({
                enableTime: true,
                time_24hr: true,
                minuteIncrement: 1,
                dateFormat: siteConfig.FLATPICKR_DATETIME_FMT,
                allowInput: true,
                defaultDate: init_date,
                onOpen: [
                    function(selectedDates, dateStr, instance) {
                        if (dateStr === '') {
                            instance.setDate(moment()._d);
                        }
                    }
                ]
            });
        });


        $('.inputmask').inputmask('99:99', {numericInput: true, placeholder: "_", removeMaskOnSubmit: true});

        // Service Event status -----------------------------------------------------------------
        function generate_status_label(status) {
            if (status.id) {
                var colour = status_colours_dict[status.id];
                var disabled = status.disabled ? ' disabled' : '';
                var $label = $('<span class="label smooth-border' + disabled + '" style="border-color: ' + colour + ';">' + status.text + '</span>');
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

        try {
          // https://github.com/qatrackplus/qatrackplus/issues/679
          $service_status.overrideSelect2Keys();
        } catch (e) {
        }


        // Service Type and Review Required --------------------------------------------------------------
        $service_type.change(function() {
            $review_required_fake.prop('disabled', se_types_review[$service_type.val()]);
            if (se_types_review[$service_type.val()]) {
                $review_required_fake.prop('checked', true);
            }
            $review_required_fake.change();
        });
        $review_required_fake.change(function() {
            $review_required.prop('checked', this.checked);
        });

        // Service Events Related ------------------------------------------------------------------------------
        function generate_related_result(res) {
            if (res.loading) { return res.text; }
            var colour = status_colours_dict[se_statuses[res.id]];
            var $div = $('<div class="select2-result-repository clearfix"><span>' + res.text + '  (' + res.date + ') </span><span class="label smooth-border pull-right" style="border-color: ' + colour + ';">' + res.status + '</span></div>');
            return $div;
        }
        function generate_related_selection(res, container) {
            var colour = status_colours_dict[se_statuses[res.id]];
            $(container).css('background-color', colour);
            $(container).css('border-color', colour);
            if (isTooBright(rgbaStringToArray(colour))) {
                $(container).css('color', 'black').children().css('color', 'black');
            }
            var $label = $('<span>' + res.text + '</span>');
            return $label;
        }
        function process_related_results(data, params) {
            var results = [];
            for (var i in data.service_events) {
                var se_id = data.service_events[i][0],
                    se_status_id = data.service_events[i][1],
                    se_problem_description = data.service_events[i][2],
                    se_date = moment(data.service_events[i][3]).format(siteConfig.MOMENT_DATETIME_FMT),
                    se_status_name = data.service_events[i][4];
                results.push({id: se_id, text: se_id, title: se_problem_description, date: se_date, status: se_status_name});
                se_statuses[se_id] = se_status_id;
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
                        page: params.page,
                        unit_id: $units.val(),
                        self_id: se_id
                    };
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

        // Unit -----------------------------------------------------------------------------------------------
        $units_fake.change(function(e) {
            var unit_id = $units_fake.val();

            if ($(this).data('previous_val') === $(this).val()){
                return;
            }
            $(this).data('previous_val', $(this).val());

            $units.val(unit_id);
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
                        $service_areas_fake.find('option:not(:first)').remove();
                        $service_areas.find('option:not(:first)').remove();
                        $template_service_area.find('option:not(:first)').remove();
                        var service_areas = response.service_areas;
                        if (service_areas.length > 0) {
                            for (var sa in service_areas) {
                                $service_areas_fake.append('<option value=' + service_areas[sa].id + '>' + service_areas[sa].name + '</option>');
                                $service_areas.append('<option value=' + service_areas[sa].id + '>' + service_areas[sa].name + '</option>');
                                $template_service_area.append('<option value=' + service_areas[sa].id + '>' + service_areas[sa].name + '</option>');
                            }
                        }
                        else {
                            $service_areas_fake.append('<option value>No service areas found for unit</option>');
                            $service_areas.append('<option value>No service areas found for unit</option>');
                            $template_service_area.append('<option value>No service areas found for unit</option>');
                        }
                        $service_areas_fake.prop('disabled', false);
                        $service_areas.prop('disabled', false);
                        $related_se.prop('disabled', false);

                        var $utcs = $('.rtsqa-utc'),
                            $template_utcs = $('#template_return_to_service_utcs');
                        $utc_initiated_by.find('option:not(:first)').remove();
                        $utc_initiated_by.val('').change();
                        $utcs.find('option:not(:first)').remove();
                        $template_utcs.find('option:not(:first)').remove();
                        $related_se.find('option').remove();
                        var utcs = response.utcs;
                        if (utcs.length > 0) {

                            $.each(response.utcs, function(i, v) {
                                $utcs.append('<option value=' + v.id + '>' + v.name + '</option>');
                                $template_utcs.append('<option value=' + v.id + '>' + v.name + '</option>');
                                $utc_initiated_by.append('<option value=' + v.id + '>(' + v.frequency + ') ' + v.name + '</option>');
                            });
                        }
                        else {
                            $utcs.append('<option value>No test lists found for unit</option>');
                            $utc_initiated_by.append('<option value>No test lists found for unit</option>');
                            $template_utcs.append('<option value>No test lists found for unit</option>');
                        }
                        $utcs.prop('disabled', false);
                        $utc_initiated_by.prop('disabled', false);
                    },
                    traditional: true,
                    error: function (e, data) {
                        console.log('ErROr');
                    }
                });
            }
            else {
                $service_areas_fake.prop('disabled', true).find('option:not(:first)').remove();
                $service_areas.prop('disabled', true).find('option:not(:first)').remove();
                $related_se.prop('disabled', true).find('option').remove();
                var $utcs = $('.rtsqa-utc');
                $utcs.prop('disabled', true).find('option:not(:first)').remove();
                $utc_initiated_by.prop('disabled', true).find('option:not(:first)').remove();
            }
        });

        $service_areas_fake.change(function(){
            var service_area_id = $service_areas_fake.val();

            if ($(this).data('previous_val') === $(this).val()){
                return;
            }
            $(this).data('previous_val', $(this).val());

            $service_areas.val(service_area_id);
        });

        // Hours Formset --------------------------------------------------------------------------------------
        function set_hours_time_to_service_time() {
            var service_time_val = $service_time.val();
            if (service_time_val !== '') {
                $(this).closest('.hours-row').find('.user_thirdparty_time').val(service_time_val);
            }
        }
        $user_or_thirdparty.change(set_hours_time_to_service_time);
        $('#add-hours').click(function() {

            var empty_hours_form = $('#empty-hours-form').html(),
                $hours_index = $('#id_hours-TOTAL_FORMS'),
                hours_index = $hours_index.val();

            $('#hours-tbody').append(empty_hours_form.replace(/__prefix__/g, hours_index));
            var $u_tp_select = $('#id_hours-' + hours_index + '-user_or_thirdparty');
            $u_tp_select.select2({
                minimumResultsForSearch: 10,
                width: '100%'
            });
            $u_tp_select.change(set_hours_time_to_service_time);
            $('#id_hours-' + hours_index + '-time').inputmask('99:99', {numericInput: true, placeholder: "_", removeMaskOnSubmit: true});

            $hours_index.val(parseInt(hours_index) + 1);
        });

        // RTS QA Formset --------------------------------------------------------------------------------
        function set_select_tli() {
            var $select_tli = $('.select-tli');
            $select_tli.off('click').click(function (event) {
                var w = window.open($(this).attr('data-link'), '_blank', 'scrollbars=no,menubar=no,height=900,width=1200,resizable=yes,toolbar=yes,status=no');
                w.focus();
            });
        }
        function set_review_tli() {
            var $review_tli = $('.review-tli');
            $review_tli.off('click').click(function (event) {
                var w = window.open($(this).attr('data-link'), '_blank', 'menubar=no,height=900,width=1200,resizable=yes,toolbar=yes,status=no');
                w.focus();
            });
        }
        displayTLI = function (prefix, data, returnValue) {
            var $pass_fail_label_group = $('<span class="label-group ' + prefix + '-hider" style="display: none;"></span>');
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
                    $pass_fail_label_group.append($label);
                }
            }
            $('#pass-fail-' + prefix).html($pass_fail_label_group);
            var $review_label_group = $('<span class="label-group ' + prefix + '-hider" style="display: none;"></span>');

            for (status in data['review']) {

                var label_class = 'label',
                    status_name = status,
                    icon = '',
                    colour = '';
                if (data['review'][status]['is_comments']) {
                    status_name = '';
                    icon = '<i class="fa fa-commenting"></i>';
                } else if (!data['review'][status]['valid']) {
                    icon = '<i class="fa fa-minus"></i>';
                } else if (data['review'][status]['reqs_review']) {
                    icon = '<i class="fa fa-question"></i>';
                }
                colour = data['review'][status]['colour'];
                if (data['review'][status]['is_comments']) {
                    if (data['review'][status]['num'] > 0) {
                        $review_label_group.append('<span class="' + label_class + '">' + icon + ' ' + data["review"][status]["num"] + ' ' + status_name + '</span>');
                    }
                } else {
                    $review_label_group.prepend('<span class="' + label_class + '" style="background-color: ' + colour + '">' + icon + ' ' + data["review"][status]["num"] + ' ' + status_name + '</span>');
                }
            }
            $('#review-' + prefix).html($review_label_group);

            if (prefix === 'utc_initiated') {

                var new_html = $tli_initiated_display_template.html()
                    .replace(/__utc-date__/g, moment(data['datetime']).format(siteConfig.MOMENT_DATETIME_FMT))
                    .replace(/__tli-id__/g, returnValue)
                    .replace(/__pass-fail__/g, $pass_fail_label_group.html())
                    .replace(/__utc-rev__/g, $review_label_group.html());

                $tli_display.html(new_html);
                $tli_display.slideDown('fast');
            } else {
                var completed_hrml = data['in_progress'] ? 'In progress' : moment(data['work_completed']).format(siteConfig.MOMENT_DATETIME_FMT);
                $('#work-completed-' + prefix).html(completed_hrml);
                $('#id_' + prefix + '-all_reviewed').val(data.all_reviewed);

                $('#' + prefix + '-review-btn').addClass(prefix + '-hider');
                $('.' + prefix + '-hider').fadeIn('fast');
                $('#id_' + prefix + '-unit_test_collection').change();
            }
            set_review_tli();

        };
        setSearchResult = function (form, returnValue) {
            window.focus();
            if (form == 'utc_initiated') {
                if (returnValue) {
                    $tli_initiated_by.val(returnValue);
                } else {
                    $utc_initiated_by.val('').change();
                    $tli_initiated_by.val('');
                }
            } else {
                $('#id_' + form + '-test_list_instance').val(returnValue);
            }

            if (returnValue) {
                $.ajax({
                    url: QAURLs.TLI_STATUSES,
                    data: {'tli_id': returnValue},
                    success: function (res) {
                        displayTLI(form, res, returnValue);
                    }
                });
            }
        };
        disable_units = function(force) {

            var disable = false;
            if (force) {
                disable = true;
            } else {
                $('select.rtsqa-utc').each(function () {
                    if ($(this).val()) {
                        disable = true;
                        return false;
                    }
                });
                if ($tli_initiated_by.val()) {
                    disable = true;
                }
            }
            $units_fake.prop('disabled', disable);
        };

        // set initial tli pass/fail and review statuses
        $.each($('.rtsqa-row'), function(i, v) {
            var prefix = $(v).attr('id');
            var tli_id = $(v).find('.tli-instance').val();
            setSearchResult(prefix, tli_id);
        });

        set_select_tli();
        set_review_tli();

        function addRtsqaRow() {

            var empty_rtsqa_form = $('#empty-rtsqa-form').html(),
                $rtsqa_index = $('#id_rtsqa-TOTAL_FORMS'),
                rtsqa_index = $rtsqa_index.val(),
                $rtsqa_tbody = $('#rtsqa-tbody');

            $tli_instances = $('.tli-instance');
            $rtsqa_rows = $('.rtsqa-row');

            $rtsqa_tbody.append(empty_rtsqa_form.replace(/__prefix__/g, rtsqa_index));

            $('#id_rtsqa-' + rtsqa_index + '-unit_test_collection').select2({
                minimumResultsForSearch: 10,
                width: '100%'
            }).change(rtsqa_change);

            $rtsqa_index.val(parseInt(rtsqa_index) + 1);

            return $rtsqa_tbody.find('#rtsqa-' + rtsqa_index);
        }
        $('#add-rtsqa').click(addRtsqaRow);

        function rtsqa_change(e) {

            var prefix = $(this).attr('data-prefix');

            var utc_id = $(this).val(),
                utc_id_old = $(this).attr('oldvalue'),
                tli_id = $('#id_' + prefix + '-test_list_instance').val(),
                rtsqa_id = $('#id_' + prefix + '-id').val(),
                se_id = $('#instance-id').val();

            if ($(this).attr('oldvalue') !== utc_id) {
                tli_id = '';
            }
            $(this).attr('oldvalue', utc_id);

            if (utc_id === '' || (utc_id_old !== '' && utc_id_old !== utc_id)) {
                $('#utc-actions-' + prefix).html('');
                $('#pass-fail-' + prefix).html('');
                $('#review-' + prefix).html('');
                $('#work-completed-' + prefix).html('');
                $('#id_' + prefix + '-test_list_instance').val('');
            }

            if (utc_id !== '') {
                // add utc action btns
                $('#utc-actions-' + prefix).html(
                    $('#utc-actions-template').html()
                        .replace(/__utc-id__/g, utc_id)
                        .replace(/__prefix__/g, prefix)
                        .replace(/__tli-id__/g, tli_id)
                        .replace(/__se-id__/g, se_id)
                        .replace(/__rtsqa-id__/g, rtsqa_id)
                );

                if (!tli_id) {
                    $('#utc-actions-' + prefix).find('div.btn-group.review-btn').removeClass(prefix + '-hider');
                }
                $('.' + prefix + '-hider').fadeIn('fast');
                set_select_tli();
            }
            disable_units();
        }

        $('select.rtsqa-utc').change(rtsqa_change);
        $('select.rtsqa-utc').change();

        // Parts formset --------------------------------------------------------------------------------------
        function process_part_results(data, params) {
            var results = [];
            for (var i in data.data) {
                var p_id = data.data[i][0],
                    p_number = data.data[i][1],
                    p_alt_number = data.data[i][2],
                    p_description = data.data[i][3],
                    p_qty_current = data.data[i][4];
                results.push({
                    id: p_id,
                    text: p_alt_number ? p_number + ' (' + p_alt_number + ') - ' + p_description : p_number + ' - ' + p_description,
                    title: p_qty_current + ' in storage'
                });
            }
            params.page = params.page || 1;
            return {
                results: results,
                pagination: {
                    more: (params.page * 30) < data.data.length
                }
            };
        }

        var part_select2 = {
            ajax: {
                url: QAURLs.PARTS_SEARCHER,
                dataType: 'json',
                delay: '500',
                data: function (params) {
                    return {
                        q: params.term, // search term
                        page: params.page,
                    };
                },
                success: function(res) {
                    console.log(res);
                },
                processResults: process_part_results,
                cache: true
            },
            escapeMarkup: function (markup) { return markup; },
            placeholder: '-------',
            minimumInputLength: 1,
            width: '100%',
            allowClear: true
        };

        function parts_used_changed() {
            var prefix = $(this).attr('data-prefix'),
                p_id = $(this).val();

            $.ajax({
                url: QAURLs.PARTS_STORAGE_SEARCHER,
                data: {'p_id': p_id},
                success: function (res) {
                    var $s = $('#id_' + prefix + '-from_storage');

                    $s.find('option:not(:first)').remove();

                    if (res.data !== '__clear__') {
                        for (var i in res.data) {
                            var psc = res.data[i];
                            var text = (psc[1] ? psc[1] + ' - ' : '') + psc[2] + (psc[3] ? (' - ' + psc[3]) : '') + ' (' + psc[4] + ')',
                                title = (psc[1] ? 'Site: ' + psc[1] + '\n' : '') +
                                    'Room: ' + psc[2] + '\n' +
                                    (psc[4] ? 'Location: ' + psc[3] + '\n' : '') +
                                    'Quantity left: ' + psc[4];
                            $s.append($('<option></option>').attr('value', psc[0]).text(text).attr('title', title));
                        }
                    }
                }
            });
        }

        $parts_used_parts.select2(part_select2);
        $parts_used_parts.change(parts_used_changed);
        // $parts_used_parts.change();

        $parts_used_from_storage.select2({
            placeholder: '-------',
            minimumResultsForSearch: 10,
            width: '100%',
            allowClear: true
        });

        $('#add-part').click(function() {

            var empty_part_form = $('#empty-parts-form').html(),
                $part_index = $('#id_parts-TOTAL_FORMS'),
                part_index = $part_index.val();

            $('#parts-used-tbody').append(empty_part_form.replace(/__prefix__/g, part_index));

            var $parts_part = $('#id_parts-' + part_index + '-part');
            $parts_part.select2(part_select2);
            $parts_part.change(parts_used_changed);
            $('#id_parts-' + part_index + '-from_storage').select2({
                placeholder: '-------',
                minimumResultsForSearch: 10,
                width: '100%',
                allowClear: true
            });

            $part_index.val(parseInt(part_index) + 1);
        });

        // // initiated by -------------------------------------------------------------------------------------
        if ($tli_initiated_by.val() === '') {
            $tli_display.hide();
        } else {
            setSearchResult('utc_initiated', $tli_initiated_by.val());
        }

        $utc_initiated_by.change(function() {
            $tli_display.slideUp('fast', function() {
                $tli_initiated_by.val('');
                disable_units();
            });
            if ($(this).val() !== '') {
                var w = window.open($(this).attr('data-link') + '/' + $(this).val() + '/utc_initiated', '_blank', 'scrollbars=no,menubar=no,height=900,width=1200,resizable=yes,toolbar=no,location=no,status=no');
                w.focus();
                w.onbeforeunload = function() {
                    setSearchResult('utc_initiated', $tli_initiated_by.val());
                    disable_units();
                    return null;
                };
            }
        });
        disable_units();

        $attachInput.on("change", function(){
            var fnames = _.map(this.files, function(f){
                return '<tr><td><i class="fa fa-paperclip fa-fw" aria-hidden="true"></i>' + f.name + '</td></tr>';
            }).join("");
            $attach_names.html(fnames);
        });

        $attach_deletes.change(function() {
            var deletes = [];
            $.each($attach_deletes, function(i, v) {
                var el = $(v);
                if (el.prop('checked')) {
                    deletes.push(el.val());
                }
            });
            $attach_delete_ids.val(deletes.join(','));
        });

        // Service event template -------------------------------------------------------
        var $se_template_create = $('#create_template'),
            $se_template_btn = $('.se-template-btn'),
            $se_template_form = $('#template_form'),
            $se_template_modal = $('#template-modal'),
            $template_unit = $('#template_unit'),
            $template_service_type = $('#template_service_type'),
            $template_is_review_required = $('#template_is_review_required'),
            $template_problem_description = $('#template_problem_description'),
            $template_work_description = $('#template_work_description'),
            $template_return_to_service_utcs = $('#template_return_to_service_utcs'),
            $template_include_for_scheduling= $('#id_include_for_scheduling'),
            $template = $('#id_service_event_template');

        function disableTemplateFields(disable) {
            $template.prop('disabled', disable);
            $units_fake.prop('disabled', disable);
            $service_areas_fake.prop('disabled', disable);
            $service_type.prop('disabled', disable);
            $review_required_fake.prop('disabled', disable);
            $('.rtsqa-utc').prop('disabled', disable);
        }
        if (from_se_schedule){
            disableTemplateFields(true);
        }else{
            $template_include_for_scheduling.prop("checked", false).prop('disabled', true);
        }

        var available_templates = {};

        $template_unit.hide();
        var $template_unit_name = $('<input type="text" disabled class="form-control">');
        $template_unit.after($template_unit_name);

        var template_fields = [
            $units_fake,
            $service_areas_fake
        ];

        $.each(template_fields, function(i, v) {
            $(v).change(checkValidTemplate);
        });

        function checkValidTemplate() {

            if (from_se_schedule) return;

            $se_template_btn.removeClass('disabled').attr('data-target', '#template-modal');

        }

        $se_template_modal.on('shown.bs.modal', function () {

            $units_fake.change();
            $template_unit.val($units_fake.val()).change();
            $template_unit_name.val($units_fake.find('option:selected').text());
            $template_service_area.val($service_areas_fake.val()).change();
            $template_service_type.val($service_type.val()).change();
            $template_is_review_required.prop('checked', $review_required_fake.prop('checked'));
            $template_problem_description.val($problem_description.val());
            $template_work_description.val($work_description.val());
            $template_return_to_service_utcs.val(
                $(".rtsqa-utc")
                .filter(function() { return this.value !== ""; })
                .map(function(i, v) { return $(v).val(); })
                .get()
            ).change();
        });

        $se_template_create.click(function() {

            var dataArray = $se_template_form.serializeArray();
            var data = {};

            $.map(dataArray, function(n, i){
                if (n['name'] !== 'return_to_service_utcs')
                    data[n['name']] = n['value'];
            });
            var rts_utcs = $template_return_to_service_utcs.val();
            if (!rts_utcs){
                rts_utcs = [];
            }
            data['return_to_service_utcs'] = rts_utcs;

            $se_template_form.find('.has-error').removeClass('has-error');
            $se_template_form.find('.error-message').remove();

            $.ajax({
                url: QAURLs.SE_TEMPLATE,
                data: data,
                method: "POST",
                success: function(res) {
                    if (res.success){
                        GoodTemplate(res);
                    } else{
                        BadTemplate(JSON.parse(res.errors));
                    }
                },
                error: function (e, data) {
                    var errors = {"name": [{message: "Server Error. Template not saved."}]};
                    BadTemplate(errors);
                }
            });
        });

        function GoodTemplate(res) {
            $("#template-form-success").append('<div class="help-block success-message"><i class="fa fa-check-circle-o"></i> '+ res.message + '</div>');
            setTimeout(function(){$se_template_modal.modal('hide');}, 1000);
            checkForTemplates(res.template.id);
        }

        function BadTemplate(errors) {

            $.each(errors, function(k, v) {

                var $field = $('#template_' + k);
                var $form_group = $field.parents('.form-group');

                $form_group.addClass('has-error');

                $.each(v, function(k, v) {
                    var $error_div = $('<div class="col-sm-12 help-block text-center error-message">' + v.message + '</div>');
                    $field.after($error_div);
                });

            });

        }

        checkValidTemplate();

        var checkForTemplatesInputs = [
            $units_fake, $service_areas_fake, $service_type
        ];

        $.each(checkForTemplatesInputs, function(i, v) {
            $(v).change(checkForTemplates);
        });

        function checkForTemplates(setValue) {

            if (from_se_schedule || $template.val()) return;

            if (!$units.val()) {
                $template.prop('disabled', true).find('option:not(:first)').remove();
                return;
            }

            var data = {
                'unit': $units.val(),
            };
            if ($service_type.val()){
                data['service_type'] = $service_type.val();
            }
            if ($service_areas_fake.val()){
                data['service_area'] = $service_areas_fake.val();
            }

            $.ajax({
                data: data,
                url: QAURLs.SE_TEMPLATE_SEARCHER,
                method: "GET",
                success: function(res) {
                    fillTemplatesSelect(res, setValue);
                }
            });

        }

        function fillTemplatesSelect(se_templates, setValue) {

            if (from_se_schedule) return;

            if (se_templates.length === 0) {
                $template.prop('disabled', true).find('option:not(:first)').remove();
                return;
            }

            $template.find('option:not(:first)').remove();
            $.each(se_templates, function(i, v) {
                $template.append('<option value=' + v.id + '>' + v.name + '</option>');
            });

            available_templates = _.transform(se_templates, function(a, b) {
                return a[b.id] = b;
            });
            $template.prop('disabled', false);

            if (setValue)
                $template.val(setValue).change();
        }

        $template.change(function(e) {

            var rts_utcs = $('.rtsqa-utc');

            if (!$(this).val()) {

                $units_fake.prop('disabled', rts_utcs.filter(function() { return $(this).val(); }).length > 0);
                $service_areas_fake.prop('disabled', false);
                $service_type.prop('disabled', false);
                $review_required_fake.prop('disabled', $service_type.val() && se_types_review[$service_type.val()]);
                rts_utcs.prop('disabled', false);
                return;
            }
            $units_fake.prop('disabled', true);
            //$service_areas_fake.prop('disabled', true);
            $review_required_fake.prop('disabled', true);
            rts_utcs.prop('disabled', true);

            var values = available_templates[$(this).val()];

            if (values['service_type']){
                $service_type.val(values['service_type']).trigger("change");
                $service_type.prop('disabled', true);
            }else {
                $service_type.prop('disabled', false);
            }

            if (values['service_area']){
                $service_areas_fake.val(values['service_area']).trigger("change");
                $service_areas_fake.prop('disabled', true);
            }else {
                $service_areas_fake.prop('disabled', false);
            }
            $review_required_fake.prop('checked', values['is_review_required']);
            $problem_description.val(values['problem_description']);
            $work_description.val(values['work_description']);

            $('#rtsqa-tbody .rtsqa-row').remove();
            $('#id_rtsqa-TOTAL_FORMS').val(0);

            $.each(values['return_to_service_utcs'], function(i, v) {
                var $new_row = addRtsqaRow();
                $new_row.find('select.rtsqa-utc').val(v).change();
            });
        });

        function removeDisabled() {
            $service_type.prop('disabled', false);
            $template.prop('disabled', false);
            $('.rtsqa-utc').prop('disabled', false);
            // TODO remove all "fake" fields and simply remove disabled before submitting.
        }
        function disableFields() {
            if (!$template.val()) return;
            $units_fake.prop('disabled', true);
            var template_sa_not_set = $template.val() && !$service_areas_fake.val();
            if (!template_sa_not_set){
                $service_areas_fake.prop('disabled', true);
            }
            var template_st_not_set = $template.val() && !$service_type.val();
            if (!template_st_not_set){
                $service_type.prop('disabled', false);
            }
            $review_required_fake.prop('disabled', true);
            $('.rtsqa-utc').filter(function() { return $(this).val(); }).prop('disabled', true);
        }

        checkForTemplates();
        disableFields();
    });


});
