
$(document).ready(function() {

    $('#id_datetime_service').daterangepicker({
        singleDatePicker: true,
        autoClose: true,
        autoApply: true,
        keyboardNavigation: false,
        timePicker: true,
        timePicker24Hour: true,
        locale: {"format": siteConfig.MOMENT_DATETIME_FMT},
        // startDate: moment(),
        // endDate: moment()
    });

     $('.inputmask').inputmask('99:99', {numericInput: true, placeholder: "_", removeMaskOnSubmit: true});

});
