
function qs(key) {
    key = key.replace(/[*+?^$.\[\]{}()|\\\/]/g, "\\$&"); // escape RegEx meta chars
    var match = location.search.match(new RegExp("[?&]"+key+"=([^&]+)(&|$)"));
    return match && decodeURIComponent(match[1].replace(/\+/g, " "));
}

require(['jquery', 'lodash', 'moment', 'datatables.net-bs'], function ($, _, moment) {

    "use strict";

    (function ($) {
        $.fn.refreshDataSelect2 = function (data) {
            this.select2('data', data);

            // Update options
            var $select = $(this[0]);
            var options = data.map(function(item) {
                return '<option value="' + item.id + '">' + item.text + '</option>';
            });
            $select.html(options.join('')).change();
        };
    })($);

    (function() {

        /*
        * Natural Sort algorithm for Javascript - Version 0.7 - Released under MIT license
        * Author: Jim Palmer (based on chunking idea from Dave Koelle)
        * Contributors: Mike Grier (mgrier.com), Clint Priest, Kyle Adams, guillermo
        * See: http://js-naturalsort.googlecode.com/svn/trunk/naturalSort.js
        */
        function naturalSort (a, b, html) {
            var re = /(^-?[0-9]+(\.?[0-9]*)[df]?e?[0-9]?%?$|^0x[0-9a-f]+$|[0-9]+)/gi,
                sre = /(^[ ]*|[ ]*$)/g,
                dre = /(^([\w ]+,?[\w ]+)?[\w ]+,?[\w ]+\d+:\d+(:\d+)?[\w ]?|^\d{1,4}[\/\-]\d{1,4}[\/\-]\d{1,4}|^\w+, \w+ \d+, \d{4})/,
                hre = /^0x[0-9a-f]+$/i,
                ore = /^0/,
                htmre = /(<([^>]+)>)/ig,
                // convert all to strings and trim()
                x = a.toString().replace(sre, '') || '',
                y = b.toString().replace(sre, '') || '';
                // remove html from strings if desired
                if (!html) {
                    x = x.replace(htmre, '');
                    y = y.replace(htmre, '');
                }
                // chunk/tokenize
            var xN = x.replace(re, '\0$1\0').replace(/\0$/,'').replace(/^\0/,'').split('\0'),
                yN = y.replace(re, '\0$1\0').replace(/\0$/,'').replace(/^\0/,'').split('\0'),
                // numeric, hex or date detection
                xD = parseInt(x.match(hre), 10) || (xN.length !== 1 && x.match(dre) && Date.parse(x)),
                yD = parseInt(y.match(hre), 10) || xD && y.match(dre) && Date.parse(y) || null;

            // first try and sort Hex codes or Dates
            if (yD) {
                if ( xD < yD ) {
                    return -1;
                }
                else if ( xD > yD ) {
                    return 1;
                }
            }

            // natural sorting through split numeric strings and default strings
            for(var cLoc=0, numS=Math.max(xN.length, yN.length); cLoc < numS; cLoc++) {
                // find floats not starting with '0', string or 0 if not defined (Clint Priest)
                var oFxNcL = !(xN[cLoc] || '').match(ore) && parseFloat(xN[cLoc], 10) || xN[cLoc] || 0;
                var oFyNcL = !(yN[cLoc] || '').match(ore) && parseFloat(yN[cLoc], 10) || yN[cLoc] || 0;
                // handle numeric vs string comparison - number < string - (Kyle Adams)
                if (isNaN(oFxNcL) !== isNaN(oFyNcL)) {
                    return (isNaN(oFxNcL)) ? 1 : -1;
                }
                // rely on string comparison if different types - i.e. '02' < 2 != '02' < '2'
                else if (typeof oFxNcL !== typeof oFyNcL) {
                    oFxNcL += '';
                    oFyNcL += '';
                }
                if (oFxNcL < oFyNcL) {
                    return -1;
                }
                if (oFxNcL > oFyNcL) {
                    return 1;
                }
            }
            return 0;
        }

        jQuery.extend( jQuery.fn.dataTableExt.oSort, {
            "natural-asc": function ( a, b ) {
                return naturalSort(a,b,true);
            },

            "natural-desc": function ( a, b ) {
                return naturalSort(a,b,true) * -1;
            },

            "natural-nohtml-asc": function( a, b ) {
                return naturalSort(a,b,false);
            },

            "natural-nohtml-desc": function( a, b ) {
                return naturalSort(a,b,false) * -1;
            },

            "natural-ci-asc": function( a, b ) {
                a = a.toString().toLowerCase();
                b = b.toString().toLowerCase();

                return naturalSort(a,b,true);
            },

            "natural-ci-desc": function( a, b ) {
                a = a.toString().toLowerCase();
                b = b.toString().toLowerCase();

                return naturalSort(a,b,true) * -1;
            }
        } );

    }());


    var $previewFrame = $("#report-preview");
    var $preview = $("#preview");
    var $previewContainer = $("#preview-container");
    var $configContainer = $("#config-container");
    var $savedReportsContainer = $("#saved-reports-container");
    var $report = $("#report");
    var $form = $("#report-form");
    var $formErrors = $("#form-errors");
    var $formSuccess = $("#form-success");
    var $title = $("#id_root-title");
    var $filter = $("#filters");
    var $reportType = $("#id_root-report_type").select2().on('select2:select', clearTooltips);
    var $reportFormat = $("#id_root-report_format").select2();
    var $reportId = $("#report_id");
    var $visibleTo = $("#id_root-visible_to").select2({'multiple': true});
    var $savedReports = $("#saved-reports");
    var $save = $("#save");
    var savedReportsTable = null;
    var $publicReports = $("#public-reports");
    var publicReportsTable = null;
    var $current = $("#current");

    var $deleteReport = $("#delete-report");
    var $deleteModal = $("#delete-modal");
    var $deleteModalTitle = $deleteModal.find(".modal-title");

    var $scheduleModal = $("#schedule-modal");
    var $scheduleForm = $("#schedule-form");
    var $scheduleMessage = $("#schedule-message");
    var $scheduleModalTitle = $scheduleModal.find(".modal-title");
    var $updateSchedule = $("#schedule");

    var $addNote = $("#add-note");

    var date_range_locale = {
        "format": siteConfig.DATERANGEPICKER_DATE_FMT,
        "separator": " - ",
        "applyLabel": "Apply",
        "cancelLabel": "Clear",
        "fromLabel": "From",
        "toLabel": "To",
        "customRangeLabel": "Custom",
        "weekLabel": "W",
        "daysOfWeek": [
            "Su",
            "Mo",
            "Tu",
            "We",
            "Th",
            "Fr",
            "Sa"
        ],
        "monthNames": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December"
        ],
        "firstDay": 1
    };

    var pastRanges = {
        "Today": [moment(), moment()],
        "Last 7 Days": [
            moment().subtract(7, 'days'),
            moment()
        ],
        "Last 30 Days": [
            moment().subtract(30, 'days'),
            moment()
        ],
        "Last 90 Days": [
            moment().subtract(90, 'days'),
            moment()
        ],
        "Last 180 Days": [
            moment().subtract(90, 'days'),
            moment()
        ],
        "Last 365 Days": [
            moment().subtract(365, 'days'),
            moment()
        ],
        "This Week": [
            moment().startOf('week'),
            moment().endOf('week')
        ],
        "This Month": [
            moment().startOf('month'),
            moment().endOf('month')
        ],
        "This Year": [
            moment().startOf('year'),
            moment().endOf('year')
        ],
        "Last Week": [
            moment().subtract(1, 'weeks').startOf('week'),
            moment().subtract(1, 'weeks').endOf('week')
        ],
        "Last Month": [
            moment().subtract(1, 'months').startOf('month'),
            moment().subtract(1, 'months').endOf('month')
        ],
        "Last 3 Months": [
            moment().subtract(3, 'months').startOf('month'),
            moment().subtract(1, 'months').endOf('month')
        ],
        "Last 6 Months": [
            moment().subtract(6, 'months').startOf('month'),
            moment().subtract(1, 'months').endOf('month')
        ],
        "Last Year": [
            moment().subtract(1, 'years').startOf('year'),
            moment().subtract(1, 'years').endOf('year')
        ]
    };

    var futureRanges = {
        "Today": [moment(), moment()],
        "Next 7 Days": [moment(), moment().add(7, 'days')],
        "Next 30 Days": [moment(), moment().add(30, 'days')],
        "Next 90 Days": [moment(), moment().add(90, 'days')],
        "Next 180 Days": [moment(), moment().add(180, 'days')],
        "Next 365 Days": [moment(), moment().add(365, 'days')],
        "This Week": [moment().startOf('week'), moment().endOf('week')],
        "This Month": [moment().startOf('month'), moment().endOf('month')],
        "This Year": [moment().startOf('year'), moment().endOf('year')],
        "Next Week": [moment().add(1, 'weeks').startOf('week'), moment().add(1, 'weeks').endOf('week')],
        "Next Month": [moment().add(1, 'months').startOf('month'), moment().add(1, 'months').endOf('month')],
        "Next 3 Months": [moment().add(1, 'months').startOf('month'), moment().add(3, 'months').endOf('month')],
        "Next 6 Months": [moment().add(1, 'months').startOf('month'), moment().add(6, 'months').endOf('month')],
        "Next Year": [moment().add(1, 'years').startOf('year'), moment().add(1, 'years').endOf('year')]
    };

    function prepareForm(){
        /* when report type is switched, do any initialization of form specific
        * fields required */

        var selects = $("#filters").find("select").each(function(i, el){
            var $el = $(el);
            var opts = {};
            if (!_.isUndefined($el.attr("multiple"))){
                opts.multiple = true;
            }
            $el.select2(opts);
        });

        createDateRangePicker($(".pastdate"), pastRanges, 'Last Month');
        createDateRangePicker($(".futuredate"), futureRanges, 'This Week');

    }

    function createDateRangePicker($el, ranges, initial){

        if ($el.val() === null || $el.val() === ""){
            $el.val(initial);//ranges[initial][0].format(siteConfig.MOMENT_DATE_FMT) + ' - ' + ranges[initial][1].format(siteConfig.MOMENT_DATE_FMT));
        }

        $el.daterangepicker({
            autoUpdateInput: false,
            "ranges": ranges,
            "showDropdowns": true,
            "linkedCalendars": false,
            "locale": date_range_locale
        }, function (start_date, end_date) {
            $(this.element).val(start_date.format(siteConfig.MOMENT_DATE_FMT) + ' - ' + end_date.format(siteConfig.MOMENT_DATE_FMT));
        }).on('apply.daterangepicker', function (ev, picker) {
            if (picker.chosenLabel.toLowerCase() === "custom"){
                $(picker.element).val(picker.startDate.format(siteConfig.MOMENT_DATE_FMT) + ' - ' + picker.endDate.format(siteConfig.MOMENT_DATE_FMT));
            }else{
                $(picker.element).val(picker.chosenLabel);
            }
            if (!picker.startDate.isSame(picker.oldStartDate) || !picker.endDate.isSame(picker.oldEndDate)) {
                $(this).trigger('keyup');
            }
        }).on('cancel.daterangepicker', function (ev, picker) {
            $(this).val('');
            $(this).trigger('keyup');
            picker.startDate = moment();
            picker.endDate = moment();
        });
    }

    function setupToolTips() {
        /* Set up the event handlers to display the tool tips that are used with the select2 options */

        /* show the tooltip when we hover over a select2 option */
        $('body').on('mouseenter', '.select2-results__option.select2-results__option--highlighted', function (e) {

            clearTooltips();

            var title = $(this).prop("title") || $(this).data().data.title;
            if (title !== "") {
                var t = $(this).tooltip({
                    title: title,
                    placement: "right",
                    html: true,
                    container: "body",
                    trigger: "manual"
                }).tooltip('show');
            }
        });

        /* when we mouse out of the option, restore the original title and destroy the tooltip */
        $('body').on('mouseleave', '.select2-results__option.select2-results__option--highlighted', function (e) {
            var orig_title = $(this).data().data.title;
            if (orig_title){
                $(this).prop("title", orig_title);
            }
            $(this).tooltip('destroy');

            clearTooltips();
        }).on('select2:close', function(){
            clearTooltips();
        });
    }

    function clearTooltips(){
        /* destroy any tooltips on the page.  This is to prevent some tooltips
        * from getting "stuck" when used with select2 */

        $('body').tooltip("destroy");
        $(".tooltip").remove();
    }

    function formErrors(data){
        /* Accepts object like
         * {
         *    base_errors: {field_name: ['error list']},  // errors with report meta form
         *    report_errors: {field_name: ['error list']}, // errors with report filter form
         *    save_errors: ['error list'] // errors from issues with saving etc
         * }
         *
         * and displays them for user.
        */

        _.each(data.report_errors, function(v, k){
            var $parent, callback;
            if (k === "__all__") {
                $parent = $("#filters");
                callback = function(content){$parent.prepend(content);};
            } else {
                $parent = $("#id_" + k).parents("[class^='col-sm']");
                callback = function(content){$parent.append(content);};
            }
            $parent.addClass("has-error");
            callback('<div class="help-block error-message">'+ v.join(", ") + '</div>');
        });

        _.each(data.base_errors, function(v, k){
            var $parent = $("#id_root-" + k).parents("[class^='col-sm']");
            $parent.addClass("has-error");
            $parent.append('<div class="help-block error-message">'+ v.join(", ") + '</div>');
        });

        _.each(data.notes_formset_errors, function(errs, err_num){
            _.each(errs, function(v, k){
                var $parent = $("#id_reportnote_set-" + err_num + "-"+ k).parents("[class^='col-sm']");
                $parent.addClass("has-error");
                $parent.append('<div class="help-block error-message">'+ v.join(", ") + '</div>');
            });
        });

        _.each(data.save_errors, function(v, k){
            $formErrors.parents(".form-group").addClass("has-error");
            $formErrors.append('<div class="help-block error-message"><i class="fa fa-ban"></i> '+ v + '</div>');
        });

    }

    function formSuccess(msg){
        $formSuccess.parents(".form-group").addClass("has-success");
        $formSuccess.append('<div class="help-block success-message"><i class="fa fa-check-circle-o"></i> '+ msg + '</div>');
    }

    function clearErrors(){
        /* clear any form error messages */
        $(".has-error").removeClass("has-error").find(".error-message").remove();
        $(".has-success").removeClass("has-success").find(".success-message").remove();
    }

    function selectReport(reportId){

        clearErrors();

        $savedReports.find("tr").removeClass("info");

        if (reportId){
            reportId = reportId.toString();
            $("#report-id-" + reportId).parents("tr").addClass("info");
            if ($reportId.val() !== reportId){

                var loadError = function(){
                    var data = {'save_errors': ["Unable to load report. Please try again later."]};
                    formErrors(data);
                };

                $.ajax({
                    type: "GET",
                    url: $form.data("load"),
                    data: "report_id=" + reportId,
                    success: function(data){
                        if (data.errors.length > 0){
                            loadError();
                        } else {
                            loadReport(data);
                        }
                    },
                    error: function(e){loadError();}
                });
            }
        }
    }

    function setFieldVal(field, type_val){
        var field_type = type_val[0];
        var field_val = type_val[1];
        var $field = $("#id_" + field);
        if (field_type === "checkbox"){
            $field.prop('checked', field_val);
        }else if (field_type === "select"){
            $field.val(field_val);
            $field.trigger("change.select2");
        }else if (field_type === "date"){
            $field.val(field_val);
        }else {
            $field.val(field_val);
        }
    }

    function loadReport(data){


        setFilterForm(data.fields['root-report_type'][1], function(){
            $reportId.val(data.id);

            var title = data.fields['root-title'][1];
            $current.val(title);

            _.each(data.fields, function(vals, field){
                setFieldVal(field, vals);
            });

            initializeNotes(data.notes);

            if (!data.editable){
                $reportId.val("");
                $save.html('<i class="fa fa-save"></i> Save as New');
            }else {
                $save.html('<i class="fa fa-save"></i> Save');
            }
            if (!$preview.prop("disabled")){
                $preview.click();
            }
        });

    }

    function loadFromUrl(){
        var repId = qs('report_id');
        if (!_.isNil(repId)){
            selectReport(repId);
            return;
        }
        var opts = qs('opts');
        if (!_.isNil(opts)){
            try {
                opts = JSON.parse(opts);
                loadReport({'fields': opts});
            }catch(e){
            }
        }
    }

    function setFilterForm(reportType, callback){

        clearTooltips();
        clearErrors();

        if (reportType  === ""){
            $form.find("button").prop("disabled", true);
            $(".filter-only").addClass("hidden");
            $filter.html("");
            $(window).trigger('resize');
            return;
        }
        $(".filter-only").removeClass("hidden");
        $form.find("button").prop("disabled", false);

        $.ajax({
            type: "GET",
            url: $form.data("getfilter"),
            data: "report_type=" + reportType,
            success: function(data){
                $filter.html(data.filter);
                $preview.prop("disabled", _.indexOf(_.map(data.formats, function(f){return f[0];}), "pdf") < 0);
                var formats = _.map(data.formats, function(f){return {id: f[0], text: f[1]};});
                $reportFormat.refreshDataSelect2(formats);
                if ($title.val().trim().length === 0){
                    $title.val($reportType.find(":selected").text()).select();
                }
                prepareForm();
                $(window).trigger('resize');
                if (callback){
                    callback();
                }
            }
        });
    }

    // reset to new report state
    function clearReport(){
        clearErrors();
        clearNotes();
        $reportId.val("");
        $reportType.val("").trigger("change");
        $deleteModalTitle.html("");
        $form.find('select:not([multiple])').not("#id_root-report_type").prop("selectedIndex", 0).trigger("change.select2");
        $form.find('select[multiple]').val(null).trigger("change.select2");
        $form.find("input[type=text]").val("");
        $current.val($current.data("original"));
    }

    // delete confirmed. Do deletion then close modal.
    function deleteReport(){

        $.ajax({
            type: "POST",
            url: $form.data("delete"),
            data: $form.find("#report_id,input[name=csrfmiddlewaretoken]").serialize(),
            success: function(data){
                if (data.errors){
                    formErrors(data);
                }else{
                    clearReport();
                    savedReportsTable.ajax.reload();
                    formSuccess(data.success_message);
                }
                $deleteModal.modal("hide");
            },
            error: function(e){
                var data = {'save_errors': ["Unable to delete report. Please try again later."]};
                formErrors(data);
            }
        });

    }

    function scheduleReport(){

        $scheduleMessage.hide().removeClass("alert-success alert-error").html("");

        $.ajax({
            type: "POST",
            url: $scheduleForm.data("schedule-url"),
            data: $scheduleForm.serialize(),
            success: function(data){
                setupScheduleForm(data.form);
                if (!data.error){
                    $scheduleMessage.show().addClass("alert-success").html(data.message);
                    savedReportsTable.ajax.reload();
                }
            },
            error: function(data){
                $scheduleMessage.show().addClass("alert-error").html("Server error");
            }
        });
    }

    function clearSchedule(){

        $scheduleMessage.hide().removeClass("alert-success alert-error").html("");
        $.ajax({
            type: "POST",
            url: $scheduleForm.data("clear-schedule-url"),
            data: $scheduleForm.serialize(),
            success: function(data){
                setupScheduleForm(data.form);
                if (!data.error){
                    $scheduleMessage.show().addClass("alert-success").html(data.message);
                    savedReportsTable.ajax.reload();
                }
            },
            error: function(data){
                $scheduleMessage.show().addClass("alert-error").html("Server error");
            }
        });
    }

    function setupScheduleForm(form){
        $scheduleForm.find(".contents").html(form);
        new recurrence.widget.Widget("id_schedule-schedule", {});
        $scheduleForm.find("select").select2();
    }

    function addNote(){
        var form_idx = $('#id_reportnote_set-TOTAL_FORMS').val();
        $('#notes-formset').append(
            $('#notes-empty-form').html().replace(
                /__prefix__/g, form_idx
            ).replace(
                /__empty__/g, "dynamic-note"
            )
        );
        $('#id_reportnote_set-TOTAL_FORMS').val(parseInt(form_idx) + 1);
        $("#id_reportnote_set-remove-" + form_idx).click(deleteNote);
    }

    function deleteNote(event){
        var note_id = _.last($(event.currentTarget).attr("id").split("-"));
        if ($reportId.val() === ""){
            var form_idx = $('#id_reportnote_set-TOTAL_FORMS').val();
            $('#notes-form-' + note_id).remove();
            $('#id_reportnote_set-TOTAL_FORMS').val(parseInt(form_idx) - 1);
        }else{
            $("#id_reportnote_set-" + note_id + "-DELETE").prop("checked", true);
            $('#notes-form-' + note_id).addClass("hidden");
        }
    }

    function clearNotes(){
        $(".dynamic-note").remove();
        $('#id_reportnote_set-TOTAL_FORMS').val(0);
    }

    function initializeNotes(notes){
        clearNotes();
        for (var i=0; i < notes.count; i++){
            addNote();
        }
        $("#id_reportnote_set-INITIAL_FORMS").val(notes.count);
        _.each(notes.notes, function(vals, field){
            setFieldVal(field, vals);
        });
    }

    $(document).ready(function(){


        /* maintain preview & filter window size */
        $(window).resize(function(e){

            var pt = $previewContainer.position().top;
            var ct = $configContainer.position().top;
            var st = $savedReportsContainer.position().top;
            var is_large = st == ct && ct == pt;
            var is_small = st !== ct;

            if (is_large){
                $configContainer.css("min-height", $(window).height() - 200);
                $savedReportsContainer.height($configContainer.height());
                $report.height($configContainer.height()-60);
            } else if (is_small){
                $configContainer.css("min-height", "auto");
                $report.height("auto");
                $savedReportsContainer.height("auto");
            } else {
                $configContainer.css("min-height", $(window).height() - 200);
                $savedReportsContainer.height($configContainer.height());
                $report.height("auto");
            }
            if (!_.isNull(savedReportsTable)){
                savedReportsTable.draw();
            }
        }).trigger('resize');

        /* don't submit when user hits enter */
        $form.submit(function(e) {
            if ($reportType.val() === ""){
                e.preventDefault();
            }
        });

        /* handle user changing report type */
        $reportType.change(function(e){
            setFilterForm($(this).val());
        });

        /* handle fetching and displaying preview */
        $preview.click(function(e) {

            $previewFrame.addClass("loading");

            clearErrors();

            var url = $form.data("preview");

            var form_data = $form.find(':input').not(
                "[name^=reportnote_set-][name$=-report]"
            ).not(
                "[name^=reportnote_set-][name$=-id]"
            ).serialize().replace(/INITIAL_FORMS=\d+/,"INITIAL_FORMS=0");

            $.ajax({
                type: "POST",
                url: url,
                data: form_data, // serializes the form's elements.
                success: function(data){
                    if (data.errors){
                        formErrors(data);
                    }
                    $report.html(data.preview);
                },
                error: function(e){
                    $report.html('<div class="loading-error">Sorry, we were unable to prepare the report. Please try again later.</div>');
                },
                complete: function(data){
                    $previewFrame.removeClass("loading");
                },
            });
        });

        /* handle saving form */
        $save.click(function(e) {

            clearErrors();

            var url = $form.data("save");

            $.ajax({
                type: "POST",
                url: url,
                data: $form.serialize(), // serializes the form's elements.
                success: function(data){
                    if (data.errors){
                        formErrors(data);
                    }else{
                        $reportId.val(data.report_id);
                        initializeNotes(data.notes);
                        savedReportsTable.ajax.reload(function(){
                            selectReport(data.report_id);
                            formSuccess(data.success_message);
                            $save.html('<i class="fa fa-save"></i> Save');
                        });
                    }
                },
                error: function(e){
                    var data = {'save_errors': ["Unable to save report. Please check fields and try again"]};
                    formErrors(data);
                }
            });
        });

        savedReportsTable = $savedReports.DataTable({
            ajax: $savedReports.data("src"),
            lengthChange: false,
            pageLength: 10,
            autoSize: false,
            dom:
                "<'row'<'col-sm-12'f>>" +
                "<'row'<'col-sm-12'tr>>" +
                "<'row'<'col-sm-12 text-center'i>>" +
                "<'row'<'col-sm-12'p>>",
            columnDefs: [
                {
                    targets: [0],
                    type: 'natural'
                },
                {
                    targets: [3],
                    visible: false
                }
            ]
        });

        $savedReports.on("click", "a.saved-report-link", function(evt){
            selectReport($(this).data("report"));
        });

        $savedReports.on("click", "a.schedule-report", function(evt){
            var $this = $(this);
            $scheduleModalTitle.html("Update schedule for " + $this.data("report-title"));
            $scheduleMessage.hide().removeClass("alert-success alert-error").html("");
            $.ajax({
                type: "GET",
                url: $this.data('schedule-form-url'),
                success: function(data){
                    setupScheduleForm(data.form);
                    $scheduleModal.modal("show");
                }
            });
        });

        $("#clear-report").click(clearReport);

        $deleteReport.click(function(){
            if ($reportId.val() === ""){
                return;
            }
            $deleteModalTitle.html("Delete '" + $title.val() + "'?");
            $deleteModal.modal("show");
        });
        $("#delete").click(deleteReport);

        $("#schedule").click(scheduleReport);

        $("#clear-schedule").click(clearSchedule);

        $addNote.click(addNote);

        prepareForm();
        setupToolTips();
        loadFromUrl();
    });


});
