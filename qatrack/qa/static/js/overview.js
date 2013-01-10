function unit_container_id(option){
    return "#unit-container-"+$(option).val();
}
function filter_units(){
    var units_to_show;
    var units_to_hide;

    if ($("#all-option").is(":selected")){
        units_to_show = _.map($(".unit-option"),unit_container_id);
        units_to_hide = [];
    }else{
        units_to_show = _.map($("#unit-filter option:selected"),unit_container_id)
        units_to_hide = _.map($("#unit-filter option").not(":selected"),unit_container_id);
    }

    $(units_to_show.join(",")).show();
    $(units_to_hide.join(",")).hide();
}
/**************************************************************************/
$(document).ready(function(){
    $("#unit-filter").change(filter_units);
});

