require(['jquery', 'moment', 'flatpickr', 'select2', 'comments', 'sl_utils'], function($, moment) {
    "use strict";
    $(document).ready(function () {

        var unitInfo;
        var s2config = {
            width: "100%",
            dropdownParent: null
        };
        var $faultModalToggle = $(".fault-modal-toggle");
        var $faultModal = $("#fault-modal");
        var $saveFault = $("#save_fault");

        if ($faultModal.length > 0){
            s2config.dropdownParent = $faultModal;
        }
        var $faultForm = $faultModal.find("form");
        var $faultMessage = $("#modal-fault-message");



        function resetModalFaultForm(){
            $faultMessage.html("");
            $faultModal.find(".has-error").removeClass("has-error");
            $faultModal.find(".has-success").removeClass("has-success");
            $faultModal.find(".error-message").remove();
        }

        $.ajax({
            type: "GET",
            url: QAURLs.UNIT_INFO,
            success: function(data){
                unitInfo = data;
                configureFaults();
            },
            error: function(data){
                alert("An error occured during initialization. Please reload the page");
            }
        });

        function configureFaults(){

            var $date_time = $("#id_fault-occurred");

            $date_time.flatpickr({
                enableTime: true,
                time_24hr: true,
                minuteIncrement: 1,
                dateFormat: siteConfig.FLATPICKR_DATETIME_FMT,
                allowInput: true,
                defaultDate: moment().format(siteConfig.MOMENT_DATETIME_FMT),
                onOpen: [
                    function(selectedDates, dateStr, instance) {
                        if (dateStr === '') {
                            instance.setDate(moment()._d);
                        }
                    }
                ]
            });

            var $modality = $("#id_fault-modality").select2(s2config);
            var $technique = $("#id_fault-treatment_technique").select2(s2config);
            var $related_se = $('#id_fault-related_service_events');
            var initialLoad = true;
            var $unit = $("#id_fault-unit");

            var $faultType = $("#id_fault-fault_type_field").select2({
                width: '100%',
                dropdownParent: s2config.dropdownParent,
                ajax: {
                    url: QAURLs.FAULT_TYPE_AUTOCOMPLETE,
                    dataType: 'json',
                    data: function(params){
                        return {
                            q: params.term,
                            unit: $unit.val(),
                            suggestions: 1
                        };
                    }
                },
                placeholder: '-----------',
                allowClear: true,
                minimumInputLength: 2,
                selectOnClose: true
            });
            $unit.select2(s2config).change(function(){
                var cur_unit = parseInt($unit.val(), 10);
                var unit_modalities = [];
                if (cur_unit in unitInfo){
                    unit_modalities = unitInfo[cur_unit].modalities;
                }
                $modality.val("");
                $modality.find("option").each(function(i, opt){
                    var $opt = $(opt);
                    var mod_id = parseInt($(opt).val());
                    var enable = unit_modalities.indexOf(mod_id) >= 0 || mod_id === "";
                    $opt.prop('disabled', !enable);
                });
                $modality.select2("destroy");
                $modality.select2(s2config);

                var unit_techniques = [];
                if (cur_unit in unitInfo){
                    unit_techniques = unitInfo[cur_unit].treatment_techniques;
                }
                $technique.val("");
                $technique.find("option").each(function(i, opt){
                    var $opt = $(opt);
                    var tech_id = parseInt($(opt).val());
                    var enable = unit_techniques.indexOf(tech_id) >= 0 || tech_id === "";
                    $opt.prop('disabled', !enable);
                });
                $technique.select2("destroy");
                $technique.select2(s2config);


                if (cur_unit){
                    $related_se.prop('disabled', false);
                    if (!initialLoad){
                        $related_se.find('option').remove();
                    }
                }else{
                    $related_se.prop('disabled', true).find('option').remove();
                }

                initialLoad = false;

            });
            $unit.change();


            /* fault log modal operation */
            function faultSuccess(result){
                $faultMessage.append(
                    '<div class="help-block success-message"><i class="fa fa-check-circle-o"></i> '+
                    result.message +
                    '</div>'
                ).parent().addClass("has-success");
                setTimeout(function(){$faultModal.modal('hide');}, 2000);
            }
            function faultError(result){
                $.each(result.non_field_errors, function(k, v){
                    $faultMessage.append(
                        '<div class="help-block error-message"><i class="fa fa-ban"></i> '+
                        v +
                        '</div>'
                    ).parent().addClass("has-error");
                });
                $.each(result.errors, function(field, errs) {
                    var $field = $('#id_fault-' + field);
                    var $form_group = $field.parents('.form-group');

                    $form_group.addClass('has-error');

                    $.each(errs, function(err_idx, err) {
                        var $error_div = $('<div class="col-sm-12 help-block text-center error-message">' + err + '</div>');
                        $field.after($error_div);
                    });
                });
            }
            $saveFault.click(function(){
                resetModalFaultForm();
                $.ajax({
                    type: "POST",
                    url: $faultForm.data("create-url"),
                    data: $faultForm.serialize(),
                    success: function(data){
                        if (data.error){
                            faultError(data);
                        }else{
                            faultSuccess(data);
                        }
                    },
                    error: function(data){
                        faultError({'non_field_errors': ["Sorry, there was a server error."]});
                    }
                });
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
                            unit_id: $unit.val(),
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

        }
    });
});