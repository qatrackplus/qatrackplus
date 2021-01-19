require(['jquery', 'moment', 'flatpickr', 'select2', 'comments'], function($, moment) {
    "use strict";
    $(document).ready(function () {

        var $date_time = $("#id_occurred");

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

        var $modality = $("#id_modality").select2({});
        var $technique = $("#id_treatment_technique").select2({});
        var $faultType = $("#id_fault_type_field").select2({
            ajax: {
                url: window.fault_type_autocomplete,
                dataType: 'json'
            },
            placeholder: '-----------',
            allowClear: true,
            minimumInputLength: 2
        });
        var $unit = $("#id_unit").select2().change(function(){
            var cur_unit = parseInt($unit.val(), 10);
            var unit_modalities = [];
            var unit_techniques = [];
            if (cur_unit in window.modalities){
                unit_modalities = window.modalities[cur_unit];
                unit_techniques = window.techniques[cur_unit];
            }
            $modality.val("");
            $modality.find("option").each(function(i, opt){
                var $opt = $(opt);
                var mod_id = parseInt($(opt).val());
                var enable = unit_modalities.indexOf(mod_id) >= 0 || mod_id === "";
                $opt.prop('disabled', !enable);
            });
            $modality.select2("destroy");
            $modality.select2();

            $technique.val("");
            $technique.find("option").each(function(i, opt){
                var $opt = $(opt);
                var tech_id = parseInt($(opt).val());
                var enable = unit_techniques.indexOf(tech_id) >= 0 || tech_id === "";
                $opt.prop('disabled', !enable);
            });
            $technique.select2("destroy");
            $technique.select2();
        });

    });
});
