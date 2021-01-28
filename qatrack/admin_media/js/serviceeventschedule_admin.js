(function(){
    "use strict";

    $(document).ready(function() {
        var $service_area = $("#id_unit_service_area");
        $service_area.select2({ }).on('change', function(){
            var unit = $service_area.find("option:selected").parent("optgroup").attr("label");
            $("#id_unit").val(unit);
        });
        var $templates = $("#id_service_event_template");
        $templates.select2({});

        $("#id_frequency").select2({});
        $("#id_assigned_to").select2({});

        $service_area.change(function(event){
            var cur_template = $templates.val();
            var cur_template_sa = $templates.find("option:selected").data('service_area');
            var selected_sa = $service_area.find('option:selected').data('service_area');
            var cur_template_in_new_opts = cur_template_sa === selected_sa;
            if (!cur_template_in_new_opts){
                $templates.val("");
            }
            $templates.find("option").each(function(i, opt){
                var $opt = $(opt);
                var sa = $opt.data("service_area");
                $opt.prop('disabled', !(sa === selected_sa || sa === ""));
            });
            $templates.select2("destroy");
            $templates.select2();
        });
        $service_area.change();
    });
})();
