(function(){

"use strict";

/* globals jQuery, window, QAUtils, require, document */

require(['jquery', 'lodash', 'moment', 'dropzone', 'autosize', 'cheekycheck', 'inputmask', 'jquery-ui', 'comments', 'flatpickr'], function ($, _, moment, Dropzone, autosize) {
    var csrf_token = $("input[name=csrfmiddlewaretoken]").val();

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    function sameOrigin(url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });

    /***************************************************************/
    //Test statuse and Table context used to narrow down jQuery selectors.
    //Improves performance in IE
    var context;

    var pass_fail_only;
    var comment_on_skip;


    // keeps track of latest composite call so we can
    // ignore older ones f they comlete after the latest one
    var latest_composite_call;

    /***************************************************************/
    //minimal Pub/Sub functionality
    var topics = {};
    $.Topic = function( id ) {
        var callbacks,
            method,
            topic = id && topics[ id ];

        if ( !topic ) {
            callbacks = jQuery.Callbacks();
            topic = {
                publish: callbacks.fire,
                subscribe: callbacks.add,
                unsubscribe: callbacks.remove
            };
            if ( id ) {
                topics[ id ] = topic;
            }
        }
        return topic;
    };

    window.imageTemplate = _.template($("#attach-template").html());

    function Test(data){
        _.extend(this,data);
    }

    function Reference(data){
        _.extend(this,data);
    }

    function Tolerance(data){
        _.extend(this,data);
        if (this.type === QAUtils.MULTIPLE_CHOICE){
            this.mc_pass_choices = this.mc_pass_choices ? this.mc_pass_choices.split(",") : [];
            this.mc_tol_choices = this.mc_tol_choices ? this.mc_tol_choices.split(",") : [];
        }
    }

    function Status(status, diff, message){
        this.status = status;
        this.diff = diff;
        this.message = message;
    }
    var NO_TOL = new Status(QAUtils.NO_TOL, "", QAUtils.NO_TOL_DISP);
    var NOT_DONE = new Status(QAUtils.NOT_DONE, "", QAUtils.NOT_DONE_DISP);
    var DONE = new Status(QAUtils.DONE, "", QAUtils.DONE_DISP);

    function TestInfo(data){
        var self = this;
        this.id = data.id;
        this.test = new Test(data.test);
        this.reference = new Reference(data.reference);
        this.tolerance = new Tolerance(data.tolerance);


        this.check_value = function(value){
            var result = self.check_dispatch[self.test.type](value);
            if (pass_fail_only){
                if (result.status === QAUtils.ACTION){
                    result.message = QAUtils.FAIL_DISP;
                }else if (result.status === QAUtils.TOLERANCE || result.status === QAUtils.NO_TOL){
                    result.message = QAUtils.WITHIN_TOL_DISP;
                    result.status = QAUtils.WITHIN_TOL;
                }else{
                    result.message = QAUtils.WITHIN_TOL_DISP;
                }
            }
            return result;
        };

        this.check_bool = function(value){
            var status, message;
            if (_.isEmpty(self.reference)){
                return NO_TOL;
            }else if (QAUtils.almost_equal(value, self.reference.value)){
                return new Status(QAUtils.WITHIN_TOL,0,QAUtils.WITHIN_TOL_DISP);
            }
            if (self.tolerance.bool_warning_only){
                status = QAUtils.TOLERANCE;
                message = QAUtils.TOLERANCE_DISP;
            } else {
                status = QAUtils.ACTION;
                message = QAUtils.ACTION_DISP;
            }

            return new Status(status, 1, message);
        };

        this.check_multi = function(value){

            var status, message;

            if (value === ""){
                return NOT_DONE;
            }

            if (_.isEmpty(self.tolerance) || self.tolerance.mc_pass_choices.length === 0){
                return NO_TOL;
            }
            if (_.indexOf(self.tolerance.mc_pass_choices,value) >= 0){
                status = QAUtils.WITHIN_TOL;
                message = QAUtils.WITHIN_TOL_DISP;
            }else if (_.indexOf(self.tolerance.mc_tol_choices,value) >= 0){
                status = QAUtils.TOLERANCE;
                message = QAUtils.TOLERANCE_DISP;
            }else{
                status = QAUtils.ACTION;
                message = QAUtils.ACTION_DISP;
            }

            return new Status(status,null,message);
        };

        this.check_done = function(value){
            return value ? DONE : NOT_DONE;
        };

        this.check_numerical = function(value){

            if (_.isEmpty(self.reference) || _.isEmpty(self.tolerance)){
                return NO_TOL;
            }

            var diff = self.calculate_diff(value);
            var message = self.diff_display(diff);

            var al=self.tolerance.act_low,
                tl=self.tolerance.tol_low,
                th=self.tolerance.tol_high,
                ah=self.tolerance.act_high;

            al = !_.isNull(al) ? al : -1.E99;
            tl = !_.isNull(tl) ? tl : -1.E99;
            th = !_.isNull(th) ? th : 1.E99;
            ah = !_.isNull(ah) ? ah : 1.E99;

            var on_action_border = QAUtils.almost_equal(al, diff) || QAUtils.almost_equal(ah, diff);
            var on_tolerance_border = QAUtils.almost_equal(tl, diff) || QAUtils.almost_equal(th, diff);

            var inside_action = ((al <= diff) && (diff <= ah )) || on_action_border;
            var inside_tolerance = (tl < diff) && (diff < th ) || on_tolerance_border;


            var status;
            if (!inside_action){
                message = QAUtils.ACTION_DISP + message;
                status = QAUtils.ACTION;
            }else if (!inside_tolerance){
                status = QAUtils.TOLERANCE;
                message = QAUtils.TOLERANCE_DISP + message;
            }else{
                status = QAUtils.WITHIN_TOL;
                message = QAUtils.WITHIN_TOL_DISP + message;
            }

            return new Status(status,diff,message);

        };

        this.check_dispatch = {};
        this.check_dispatch[QAUtils.BOOLEAN]=this.check_bool;
        this.check_dispatch[QAUtils.MULTIPLE_CHOICE]=this.check_multi;
        this.check_dispatch[QAUtils.CONSTANT]=this.check_numerical;
        this.check_dispatch[QAUtils.SIMPLE]=this.check_numerical;
        this.check_dispatch[QAUtils.COMPOSITE]=this.check_numerical;
        this.check_dispatch[QAUtils.STRING_COMPOSITE]=this.check_multi;
        this.check_dispatch[QAUtils.STRING]=this.check_multi;
        this.check_dispatch[QAUtils.DATE]=this.check_done;
        this.check_dispatch[QAUtils.DATETIME]=this.check_done;
        this.check_dispatch[QAUtils.UPLOAD]=this.check_done;

        this.calculate_diff = function(value){
            if (self.tolerance.type === QAUtils.PERCENT){
                return 100.0*(value-self.reference.value)/self.reference.value;
            }
            return value - self.reference.value;
        };

        this.diff_display = function(diff){

            if (self.tolerance.type === QAUtils.PERCENT){
                return "(" + diff.toFixed(1)+"%)";
            }
            return "(" + diff.toFixed(2)+")";
        };

    }

    function TestInstance(test_info, row){
        var self = this;
        this.initialized = false;
        this.test_info = test_info;
        var tt = this.test_info.test.type;
        this.row = $(row);
        this.prefix = this.row.attr('data-prefix');
        this.inputs = this.row.find("td.qa-value").find("input, textarea, select").not("[name$=user_attached]");
        this.user_attach_input = this.row.find("input[name$=user_attached]");
        this.unit_id = $("#unit-id").val();
        this.test_list_id = $("#test-list-id").val();

        this.comment = this.row.next();
        this.comment_closed_by_user = false;
        this.error = $('.qa-error.row-' + this.prefix);

        this.visible = true;
        this.showing_comment = false;
        this.showing_procedure = false;

        this.hover = false;

        this.status = this.row.find("td.qa-status");
        this.test_status = null;

        this.skip = this.row.find("td.qa-skip input");
        this.skipped = false;
        this.set_skip = function(skipped){
            self.skipped = skipped;
            self.skip.prop("checked", self.skipped);
        };
        this.skip.change(function(){
            self.skipped = self.skip.is(":checked");
            if (self.skipped){
                if (comment_on_skip && !self.test_info.test.skip_without_comment){
                    show_comment();
                }
                if (self.test_info.test.type === QAUtils.BOOLEAN || self.test_info.test.type === QAUtils.UPLOAD){
                    self.set_value(null);
                }
                $.Topic("valueChanged").publish();
            }
        });

        self.rows = $('.row-' + self.prefix);
        self.rows.hover(
            function() {
                self.rows.addClass('hover');
            },
            function() {
                $('.hover').removeClass('hover');
            }
        );
        self.inputs.focus(function(){self.rows.addClass("hover");});
        self.inputs.blur(function(){self.rows.removeClass("hover");});

        function show_comment() {
            self.comment.slideDown('fast');
            self.showing_comment = true;
            self.comment.find('.comment-bar').slideDown('fast');
            self.comment.find('.comment-bar').addClass('in');
            self.row.find('.comment-bar').addClass('in');
        }
        function hide_comment() {
            self.comment.slideUp('fast');
            self.showing_comment = false;
            self.comment.find('.comment-bar').slideUp('fast');
            self.comment.find('.comment-bar').removeClass('in');
            self.row.find('.comment-bar').removeClass('in');
        }

        this.show_comment = this.row.find("td.qa-showcmt a");
        this.comment_box = this.comment.find("textarea");
        this.comment_icon = this.row.find(".qa-showcmt i");

        this.show_comment.click(function(){
            if (!self.showing_comment) {
                show_comment();
            } else  {
                self.comment_closed_by_user = true;
                hide_comment();
            }
            return false;
        });
        this.set_comment_icon = function(){
            self.comment_icon.removeClass();
            if ( $.trim(self.comment_box.val()) !== ''){
                self.comment_icon.addClass("fa fa-commenting");
            }else{
                self.comment_icon.addClass("fa fa-commenting-o");
            }
        };
        autosize(self.comment.find('textarea'));
        this.set_comment_icon(); //may already contain comment on initialization
        this.comment_box.blur(function(){
            self.set_comment_icon();
            $.Topic("valueChanged").publish();
        });

        this.show_procedure = this.row.find("td.qa-showproc a");
        this.procedure = this.comment.next();
        this.show_procedure.click(function(){
            // self.procedure.toggle('fast');
            self.showing_procedure = !self.showing_procedure;
            self.procedure.find('.procedure-bar').slideToggle('fast').toggleClass('in');
            self.comment.find('.procedure-bar').toggleClass('in');
            self.row.find('.procedure-bar').toggleClass('in');
            return false;
        });

        this.value = null;

        this.date_picker = null;
        if (tt === "date" || tt === "datetime"){
            var has_time = tt === "datetime";
            this.date_picker = this.inputs.flatpickr({
                enableTime: has_time,
                time_24hr: true,
                minuteIncrement: 1,
                enableSeconds: true,
                dateFormat: has_time ? siteConfig.FLATPICKR_DATETIME_FMT: siteConfig.FLATPICKR_DATE_FMT,
                altInput: true,
                altFormat: has_time ? siteConfig.FLATPICKR_DATETIME_FMT: siteConfig.FLATPICKR_DATE_FMT
            });

            this.inputs.parent().find(".qa-date-clear").click(function(){
                self.date_picker.clear();
            });

            this.inputs.parent().find(".qa-date-pick").click(function(){
                self.date_picker.open();
            });

        }

        this.inputs.change(function(){
            self.update_value_from_input();
            if (self.skipped){
                self.set_skip(false);
            }
            $.Topic("valueChanged").publish();
            $.Topic("qaUpdated").publish();
        });

        this.set_comment = function(comment){
            self.comment_box.val(comment);
        };

        this.set_value = function(value, user_attached, formatted){
            //set value manually and update inputs accordingly
            var tt = self.test_info.test.type;

            self.value = value;

            if (tt === QAUtils.BOOLEAN){
                if (_.isNull(value)){
                    self.inputs.prop("checked",false);
                }else{
                    self.inputs[0].checked = value === 0;
                    self.inputs[1].checked = !self.inputs[0].checked;
                }
            }else if (
                tt === QAUtils.STRING ||
                tt === QAUtils.MULTIPLE_CHOICE ||
                tt === QAUtils.STRING_COMPOSITE
            ){
                if (_.isObject(value)){
                    self.inputs.val(JSON.stringify(value));
                }else{
                    self.inputs.val(value);
                }
            }else if (
                tt === QAUtils.DATE ||
                tt === QAUtils.DATETIME
            ){
                if (_.isObject(value)){
                    self.inputs.val(JSON.stringify(value));
                }else{
                    self.inputs.val(value);
                }
                this.date_picker.setDate(value);
            }else if (tt === QAUtils.UPLOAD){
                if (_.isNull(value)){
                    self.inputs.filter(".qa-input:hidden").val("");
                    self.upload_data = value;
                }else{
                    self.inputs.filter(".qa-input:hidden").val(value.attachment_id);
                    self.value = value.result;
                    self.upload_data = value;
                }
            }else if (tt === QAUtils.COMPOSITE){
                if (_.isNull(value)){
                    self.inputs.val("");
                }else{
                    self.inputs.attr("title", "Actual value = " + self.value);
                    self.inputs.val(formatted);
                }
            }else if (tt === QAUtils.SIMPLE || tt === QAUtils.COMPOSITE){
                if (_.isNull(value)){
                    self.inputs.val("");
                }else{
                    self.inputs.val(QAUtils.format_float(value));
                }
            }

            var uploadAttached =  value && value.attachment;
            var uploadUserAttached = value && (value.user_attached && value.user_attached.length > 0);
            var compUserAttached = user_attached && user_attached.length > 0;
            var uattachs = [];
            if (uploadAttached){
                uattachs = uattachs.concat(value.attachment);
            }
            if (uploadUserAttached){
                uattachs = uattachs.concat(value.user_attached);
            }
            if (compUserAttached){
                uattachs = uattachs.concat(user_attached);
            }
            if (uattachs.length > 0){

                var attach_ids = _.map(uattachs, "attachment_id");
                self.user_attach_input.val(attach_ids.join(","));

                self.clear_images();

                _.each(uattachs, function(att){
                    if (att.is_image){
                        self.display_image(att);
                    }
                });

            }

            this.update_status();
        };

        this.update_value_from_input = function(){

            var value;
            var data;

            var tt = self.test_info.test.type;
            if (tt === QAUtils.BOOLEAN){
                value = parseFloat(self.inputs.filter(":checked").val());
                self.value = _.isNaN(value) ? null : value;
            }else if (tt === QAUtils.MULTIPLE_CHOICE){
                value = $.trim(self.inputs.find(":selected").text());
                self.value = value !== "" ? value : null;
            }else if (tt === QAUtils.UPLOAD){
                if (self.inputs.val() && !this.initialized){
                    data = {
                        attachment_id: self.inputs.val(),
                        test_id: self.test_info.test.id,
                        test_list_instance: editing_tli,
                        meta: JSON.stringify(get_meta_data()),
                        test_list_id: self.test_list_id,
                        unit_id: self.unit_id,
                        comments: JSON.stringify(get_comments()),
                        skips: JSON.stringify(get_skips())
                    };

                    $('body').addClass("loading");
                    $.ajax({
                        type:"POST",
                        url: QAURLs.UPLOAD_URL,
                        data: $.param(data),
                        dataType:"json",
                        success: function (result) {
                            $('body').removeClass("loading");
                            self.status.removeClass("btn-info btn-primary btn-danger btn-success");
                            if (result.errors.length > 0){
                                self.set_value(null);
                                self.status.addClass("btn-danger").text("Failed");
                                self.status.attr("title", result.errors[0]);
                                if (window.console){
                                    console.log(result.errors);
                                }
                            }else{
                                self.set_value(result);
                                self.status.addClass("btn-success").text("Success");
                                self.status.attr("title", result.url);
                                if (window.console){
                                    console.log(result);
                                }
                                $.Topic("valueChanged").publish();
                            }
                        },
                        traditional:true,
                        error: function(e, data){
                            $('body').removeClass("loading");
                            self.set_value(null);
                            self.status.removeClass("btn-primary btn-danger btn-success");
                            self.status.addClass("btn-danger").text("Server Error");
                        }
                    });
                }
            }else if (tt === QAUtils.STRING || tt === QAUtils.DATE || tt === QAUtils.DATETIME){
                self.value = self.inputs.val();
            }else if (tt === QAUtils.CONSTANT){
                self.value = parseFloat(self.inputs.val());
                self.inputs.val(self.inputs.data("formatted"));
            }else {
                self.inputs.val(QAUtils.clean_numerical_value(self.inputs.val()));
                var dots = self.inputs.val().match(/\./g);
                if (dots===null || dots.length <= 1) {
                    value = parseFloat(self.inputs.val());
                }else {
                    value = NaN;
                }
                self.value = _.isNaN(value) ? null : value;
            }

            this.update_status();
            this.initialized = true;
        };
        this.update_status = function(){
            var status = _.isNull(self.value)? NOT_DONE : self.test_info.check_value(self.value);
            if (self.test_info.test.type === QAUtils.UPLOAD){
                if (status === DONE){
                    self.status.attr("title", self.value);
                }else{
                    self.status.attr("title","");
                }
            }
            self.set_status(status);
        };
        this.set_status = function(status){
            if (test_info.test.type != 'upload') {
                self.status.html(status.message);
                self.status.removeClass("btn-success btn-warning btn-danger btn-info");
                self.test_status = status.status;
                if (status.status === QAUtils.WITHIN_TOL) {
                    self.status.addClass("btn-success");
                } else if (status.status === QAUtils.TOLERANCE) {
                    self.status.addClass("btn-warning");
                } else if (status.status === QAUtils.ACTION) {
                    self.status.addClass("btn-danger");
                } else if (status.status !== QAUtils.NOT_DONE) {
                    self.status.addClass("btn-info");
                }
            }
        };

        this.NOT_PERFORMED = "Category not performed";

        this.show = function(){
            self.row.show();
            self.comment.find('.comment-div').show();
            if (self.showing_procedure) {
                self.procedure.find('.procedure-container').show();
            }
            this.error.show();
            self.set_skip(false);
            self.visible = true;
            self.comment_box.val(self.comment_box.val().replace(self.NOT_PERFORMED,""));
            if (self.test_info.test.type == QAUtils.BOOLEAN){
                self.set_value(self.value);
            }
        };

        this.hide = function(){
            self.row.hide();
            self.comment.find('.comment-div').hide();
            self.procedure.find('.procedure-container').hide();
            self.visible = false;
            this.error.hide();

            // skipping sets value to null but we want to presever value in case it
            // is unfiltered later. Filtered values will be nulled on submitt
            var tmp_val = self.value;
            if (self.test_info.test.type === QAUtils.UPLOAD){
                tmp_val = self.upload_data;
            }
            self.set_skip(true);
            self.set_value(tmp_val);
            if (self.test_info.test.type == QAUtils.BOOLEAN){
                self.inputs.prop("checked", false);
            }

            self.comment_box.val(self.NOT_PERFORMED);
        };

        if (test_info.test.type == 'upload') {

            self.dropzone = new Dropzone('#upload-button-' + test_info.test.id, {

                url: QAURLs.UPLOAD_URL,
                previewsContainer: false,
                // previewTemplate: $('#preview-template')[0].innerHTML,
                // dropZone: self.row.children(),
                // singleFileUploads: true,
                uploadMultiple: false,
                paramName: "upload",
                replaceFileInput: false,
                params: {
                    'csrfmiddlewaretoken': csrf_token,
                    "test_id": self.test_info.test.id,
                    "meta": JSON.stringify(get_meta_data()),
                    "test_list_id": self.test_list_id,
                    "unit_id": self.unit_id,
                    "comments": JSON.stringify(get_comments()),
                    "skips": JSON.stringify(get_skips())
                },
                accept: function(file, done) {
                    if (file.name.length > 150) {
                        self.set_value(null);
                        self.status.removeClass("btn-primary btn-danger btn-success");
                        done("Filename exceeds 150 characters!");
                    }
                    else { done(); }
                }

            });

            self.dropzone.on('totaluploadprogress', function(progress) {
                self.status.removeClass("btn-primary btn-danger btn-success btn-info");
                if (progress.toFixed(0) === "100"){
                    self.status.addClass("btn-warning").text("Processing...").attr('title', 'Processing upload');
                }else{
                    self.status.addClass("btn-warning").text(progress.toFixed(0) + "%").attr('title', 'Uploading file');
                }
            });

            self.dropzone.on('error', function(file, data) {
                var btn_txt, tool_tip;
                if (!data || !file){
                    btn_txt = "Server Error";
                    tool_tip = "Server Error";
                }else if (file.xhr && file.xhr.status === 413){
                    btn_txt = "File too large";
                    tool_tip = "You may need to increase the maximum request size on your server";
                }else{
                    btn_txt = data;
                    tool_tip = data;
                }
                self.set_value(null);
                self.status.removeClass("btn-primary btn-danger btn-success");
                self.status.addClass("btn-danger").text(btn_txt).attr('title', tool_tip);
            });

            self.dropzone.on('success', function(file, data) {

                var response_data = JSON.parse(data);
                self.status.removeClass("btn-primary btn-info btn-warning btn-danger btn-success");
                if (response_data.errors.length > 0) {
                    self.set_value(null);
                    self.status.addClass("btn-danger").text("Failed");
                    self.status.attr("title", response_data.errors[0]);
                    if (window.console){
                        console.log(response_data.errors);
                    }
                } else {
                    self.set_value(response_data);
                    if (response_data.skips){
                        set_skips(response_data.skips);
                    }
                    if (response_data.comment){
                        self.set_comment(response_data.comment);
                        self.set_comment_icon();
                        if (!self.showing_comment && !self.comment_closed_by_user) {
                            self.show_comment.click();
                        }
                    }
                    self.status.addClass("btn-success").text("Success");
                    self.status.attr("title", response_data.attachment.url);

                    $.Topic("valueChanged").publish();
                }
            });

        }

        // set initial skip state
        this.skip.trigger("change");

        //Set initial value
        this.update_value_from_input();

        // Display images
        self.display_image = function(attachment){
            var name = self.test_info.test.name;
            var html = imageTemplate({a: attachment, test: name});
            if (self.test_info.test.display_image){
              $("#qa-images").css({"display": "block"});
              $("#"+self.test_info.test.slug).append(html);
            }
        };

        self.clear_images = function(){
            if (self.test_info.test.display_image){
              $("#qa-images").css({"display": ""});
              $("#" + self.test_info.test.slug).removeClass("qa-image-box").html("");
            }
        };
    }

    function get_meta_data(){

        var meta = {
            test_list_name: $("#test-list-name").val(),
            unit_number: parseInt($("#unit-number").val()),
            cycle_day: parseInt($("#cycle-day-number").val()),
            work_completed: QAUtils.parse_dd_mmm_yyyy_date($("#id_work_completed").val()),
            work_started: QAUtils.parse_dd_mmm_yyyy_date($("#id_work_started").val()),
            username: $("#username").val()
        };

        return meta;

    }

    function get_comments(){

        var comments = _.map(tli.test_instances, function(ti){
            var comment = ti.comment_box.val().trim();
            return comment;
        });
        return _.zipObject(tli.slugs, comments);
    }

    function get_skips(){

        var skips = _.map(tli.test_instances, function(ti){
            return ti.skipped;
        });
        return _.zipObject(tli.slugs, skips);
    }

    function set_skips(skips){

        _.each(tli.test_instances, function(ti){
            var skip = skips[ti.test_info.test.slug];
            if (skip !== ti.skipped){
                ti.set_skip(skip);
            }
        });
    }

    function TestListInstance(){
        var self = this;

        this.test_instances = [];
        this.tests_by_slug = {};
        this.slugs = [];
        this.composites = [];

        this.$spinners = $(".comp-calc-spinner i.fa");
        this.submit = $("#submit-qa");

        this.attachInput = $("#id_tli_attachments");

        /***************************************************************/
        //set the intitial values, tolerances & refs for all of our tests
        this.initialize = function(){
            var test_infos = _.map(window.unit_test_infos,function(e){ return new TestInfo(e);});
            self.test_list_id = $("#test-list-id").val();
            self.unit_id = $("#unit-id").val();
            self.test_instances = _.map(_.zip(test_infos, $("#perform-qa-table tr.qa-valuerow")), function(uti_row){return new TestInstance(uti_row[0], uti_row[1]);});
            self.slugs = _.map(self.test_instances, function(ti){return ti.test_info.test.slug;});
            self.tests_by_slug = _.zipObject(self.slugs,self.test_instances);
            self.composites = _.filter(self.test_instances,function(ti){return ti.test_info.test.type === QAUtils.COMPOSITE || ti.test_info.test.type === QAUtils.STRING_COMPOSITE;});
            self.attachInput.on("change", function(){
                var fnames = _.map(this.files, function(f){
                    return '<i class="fa fa-paperclip fa-fw" aria-hidden="true"></i>' + f.name +" ";
                }).join("");
                $("#tli-attachment-names").html(fnames);
            });

            self.calculate_composites(true);
        };


        this.calculate_composites = function(init){

            init = init || false;

            if (!init && self.composites.length === 0){
                return;
            }
            self.$spinners.removeClass("text-info").addClass("fa-spin text-warning").attr("title", "Performing calculations...");

            var cur_values = _.map(self.test_instances, function(ti){return ti.value;});
            var qa_values = _.zipObject(self.slugs, cur_values);
            var meta = get_meta_data();
            var comments = get_comments();
            var skips = get_skips();

            // only set default values if not editing an existing tli
            var get_defaults = !has_errors && editing_tli === 0 && init;

            var data = {
                defaults: get_defaults,
                tests: qa_values,
                meta: meta,
                test_list_id: self.test_list_id,
                unit_id: self.unit_id,
                comments: comments,
                skips: skips
            };

            var on_success = function(data, status, XHR){

                if (init){
                    $('body').removeClass("loading");
                }

                if (latest_composite_call !== XHR){
                    return;
                }
                self.submit.attr("disabled", false);

                if (data.success){
                    _.each(data.results,function(result, name){
                        var ti = self.tests_by_slug[name];
                        if (!_.isNil(ti) && !ti.skipped){
                            if (result.comment){
                                ti.set_comment(result.comment);

                                ti.set_comment_icon();
                                if (!ti.showing_comment && !ti.comment_closed_by_user) {
                                    ti.show_comment.click();
                                }
                            }
                            ti.set_value(result.value, result.user_attached, result.formatted);

                            if (result.error){
                                ti.status.attr("title", result.error);
                                ti.status.addClass("btn-danger").text("Failed");
                                if (window.console){
                                    console.log(result.error);
                                }
                            }else{
                                if (ti.test_status !== QAUtils.ACTION){
                                    ti.status.removeClass("btn-danger");
                                }
                                ti.status.attr("title", "");
                            }
                        }

                    });

                    if (data.skips){
                        set_skips(data.skips);
                    }
                }

            };

            var on_complete = function(){
                self.$spinners.removeClass("fa-spin text-warning").addClass("text-info").attr("title", "Calculations complete");
                self.submit.attr("disabled", false);
                if (init){
                    $.Topic("valueChanged").subscribe(self.calculate_composites);
                    $('body').removeClass("loading");
                    if (get_defaults){
                        // if first call was to get default values, then run composites now
                        self.calculate_composites();
                    }
                }
                $.Topic("qaUpdated").publish();
            }

            self.submit.attr("disabled", true);

            latest_composite_call = $.ajax({
                type: "POST",
                url: QAURLs.COMPOSITE_URL,
                data: JSON.stringify(data),
                contentType: "application/json",
                dataType: "json",
                success: on_success,
                traditional: true,
                complete: on_complete
            });
        };

        this.has_failing = function(){
            return _.filter(self.test_instances, function(ti){
                    return ti.test_status === QAUtils.ACTION;
                }).length > 0;
        };

        $.Topic("categoryFilter").subscribe(function(categories) {
            _.each(self.test_instances, function(ti){
                if (categories === "all" || _.includes(categories, ti.test_info.test.category.toString())){
                    if (!ti.visible){
                        ti.show();
                    }
                }else{
                    if (ti.visible){
                        ti.hide();
                    }
                }
            });
            $.Topic("qaUpdated").publish();
        });

    }

    function set_tab_stops(){

        var user_inputs=  $('.qa-input',context).not("[readonly=readonly]").not("[type=hidden]").not(".btn");
        var visible_user_inputs = user_inputs;

        var tabindex = 1;
        user_inputs.each(function() {
            $(this).attr("tabindex", tabindex);
            tabindex++;
        });
        user_inputs.first().focus();

        $.Topic("categoryFilterComplete").subscribe(function(){
            visible_user_inputs = user_inputs.filter(":visible");
        });

        //allow arrow key and enter navigation
        $(document).on("keydown","input, select", function(e) {

            var visible_user_inputs = user_inputs.filter(":visible");
            var to_focus;
            var idx;
            //rather than submitting form on enter, move to next value
            if (e.which == QAUtils.KC_ENTER  || e.which == QAUtils.KC_DOWN ) {
                idx = visible_user_inputs.index(this);

                if (idx == visible_user_inputs.length - 1) {
                    to_focus= visible_user_inputs.first();
                } else {
                    to_focus = visible_user_inputs[idx+1];
                }
                to_focus.focus();
                if (to_focus.type === "text" || to_focus.type === "number"){
                    to_focus.select();
                }
                return false;
            }else if (e.which == QAUtils.KC_UP ){
                idx = visible_user_inputs.index(this);

                if (idx === 0) {
                    to_focus = visible_user_inputs.last();
                } else {
                    to_focus = visible_user_inputs[idx-1];
                }
                if (to_focus){
                    to_focus.focus();
                    if (to_focus.type === "text" || to_focus.type === "number"){
                        to_focus.select();
                    }
                }
                return false;
            }
        });

    }

    var tli;

    $(document).ready(function(){

        tli = new TestListInstance();
        tli.initialize();

        context = $("#perform-qa-table")[0];

        pass_fail_only = $("#pass-fail-only").val() === "yes" ? true : false;
        comment_on_skip = $("#require-comment-on-skip").val() === "yes" ? true : false;

        $("#test-list-info-toggle").click(function(){
            $("#test-list-info").toggle(600);
        });

        $('#id_status').select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        function generate_se_selection(res, container) {
            if (res.loading || !res.id) { return res.text; }
            var colour = status_colours_dict[se_statuses[res.id]];
            $(container).css('border-color', colour);
            $(container).addClass('service-event-status-label');
            return $('<span>' + res.text + '</span>');
        }
        function generate_se_result(res, container) {
            if (res.loading || !res.id) { return res.text; }
            var colour = status_colours_dict[se_statuses[res.id]];
            var $label =  $('<span class="label service-event-status-label" style="border-color: ' + colour + '">' + res.text + '</span>');
            return $label;
        }

        $('#id_service_events').select2({
            ajax: {
                url: QAURLs.SE_SEARCHER,
                dataType: 'json',
                delay: '500',
                data: function (params) {
                    return {
                        q: params.term, // search term
                        page: params.page,
                        unit_id: unit_id
                    };
                },
                processResults: function (data, params) {
                    var results = [];
                    for (var i in data.service_events) {
                        var se_id = data.service_events[i][0],
                            s_id = data.service_events[i][1];
                        results.push({id: se_id, text: 'ServiceEvent ' + se_id});
                        se_statuses[se_id] = s_id;
                    }
                    params.page = params.page || 1;
                    return {
                        results: results,
                        pagination: {
                            more: (params.page * 30) < data.total_count
                        }
                    };
                },
                cache: true
            },
            escapeMarkup: function (markup) { return markup; },
            minimumInputLength: 1,
            templateResult: generate_se_result,
            templateSelection: generate_se_selection,
            width: '100%'
        });

        $.Topic("qaUpdated").subscribe(function(){
            if (tli.has_failing()){
                display_fail(true);
            }else{
                display_fail(false);
            }
        });

        // general comment
        // autosize($('#id_comment'));
        // $("#toggle-gen-comment").click(function(){
        //     $('#qa-tli-comment').slideToggle('fast');
        // });

        //set link for cycle when user changes cycle day dropdown
        $(".radio-days").on('ifChecked', function(){
            var day = $(this).attr('id').replace('day-', '');
            var cur = document.location.href;
            document.location.href = cur.replace(/day=(next|[0-9]+)/,"day="+day);
        });

        ////////// Submit button
        //make sure user actually want's to go back
        //this is here to help mitigate the risk that a user hits back or backspace key
        //by accident and completely hoses all the information they've entered during
        //a qa session

        $(window).bind("beforeunload", function(){
            var non_read_only_tis = _.filter(tli.test_instances, function(ti){
                var tt = ti.test_info.test.type;
                return QAUtils.READ_ONLY_TEST_TYPES.indexOf(tt) < 0;
            });

            if (_.some(_.map(non_read_only_tis,"value"))){
                return  "If you leave this page now you will lose all entered values.";
            }
        });
        $("#qa-form").preventDoubleSubmit().submit(function(){
            $(window).off("beforeunload");

            /* since value displayed may be different then actual value, replace text values before
             * submitting */
            _.each(tli.test_instances, function(ti){
                var tt = ti.test_info.test.type;
                if (tt === QAUtils.COMPOSITE || tt === QAUtils.CONSTANT){
                    ti.inputs.val(ti.value);
                }else if (tt !== QAUtils.UPLOAD && _.isObject(ti.value)){
                    ti.inputs.val(JSON.stringify(ti.value));
                }
            });
        });

        ///////// Category checkboxes:
        var categories = $('.check-category');
        var showall = $('#category-showall');
        showall.on('ifChecked ifUnchecked', function(e) {
            if (e.type == 'ifChecked') {
                categories.iCheck('check');
            } else {
                categories.iCheck('uncheck');
            }
        });
        categories.on('ifChanged', function(e){
            var cats = [];
            $.each(categories.filter(':checked'), function () {
                cats.push($(this).attr('id').replace('category-', ''));
            });
            if (categories.filter(':checked').length == categories.length) {
                showall.prop('checked', true);
            }
            else {
                showall.prop('checked', false);
            }
            $.Topic("categoryFilter").publish(cats);
            $.Topic("categoryFilterComplete");
            showall.iCheck('update');
        });

        ///////// Work time
        if (override_date) {

            var $start_picker = $('#id_work_started'),
                $completed_picker = $('#id_work_completed'),
                $duration_picker = $('#id_work_duration'),
                $start_clear = $('#clear-work_started'),
                $complete_clear = $('#clear-work_completed');

            var duration_change = true;
            var work_started_initial = !work_started_initial ? moment().valueOf() : moment(work_started_initial).valueOf();
            var work_completed_initial = !work_completed_initial ? false : moment(work_completed_initial).valueOf();

            if (work_completed_initial) {
                $complete_clear.show();
            }

            var setDuration = function(start_date, complete_date) {
                if (!start_date || !complete_date) {
                    $duration_picker.val('');
                    $.Topic("valueChanged").publish();
                    return;
                }
                var diff = complete_date - start_date,
                    hours = Math.floor(diff / 3600000),
                    mins = Math.floor((diff - hours * 3600000) / 60000);

                if (mins < 10) mins = '0' + mins; else mins = mins.toString();
                $duration_picker.val(hours.toString() + mins);

                $.Topic("valueChanged").publish();
            };

            var start_fp = $start_picker.flatpickr({
                enableTime: true,
                time_24hr: true,
                minuteIncrement: 1,
                dateFormat: siteConfig.FLATPICKR_DATETIME_FMT,
                maxDate: work_completed_initial ? _.max([work_completed_initial, moment().valueOf()]) : moment().valueOf(),
                onChange: function(selectedDates, dateStr, instance) {

                    if (dateStr === '') {
                        instance.setDate(work_started_initial);
                        selectedDates = [work_started_initial];
                    }

                    if ($completed_picker.val() !== '') {
                        setDuration(selectedDates[0], $completed_picker[0]._flatpickr.selectedDates[0]);
                    }
                    $completed_picker[0]._flatpickr.set('minDate', selectedDates[0].valueOf());
                    $start_clear.fadeIn('fast');
                }
            });
            $start_clear.click(function() {
                start_fp.clear();
                $(this).fadeOut('fast');
            });

            var complete_fp = $completed_picker.flatpickr({
                enableTime: true,
                time_24hr: true,
                dateFormat: siteConfig.FLATPICKR_DATETIME_FMT,
                minuteIncrement: 1,
                minDate: $start_picker[0]._flatpickr.selectedDates[0],
                onOpen: function(selectedDates, dateStr, instance) {
                    if (dateStr === '') {
                        instance.setDate(work_completed_initial ? work_completed_initial : moment().valueOf(), true);
                    }
                },
                onChange: function(selectedDates, dateStr, instance) {

                    if (dateStr === '') {
                        instance.setDate(null);
                        selectedDates = [];
                    }

                    setDuration($start_picker[0]._flatpickr.selectedDates[0], selectedDates[0]);

                    if (selectedDates.length > 0) {
                        $start_picker[0]._flatpickr.set('maxDate', _.max([selectedDates[0].valueOf(), moment().valueOf()]));
                        $complete_clear.fadeIn('fast');
                    } else {
                        $start_picker[0]._flatpickr.set('maxDate', moment().valueOf());
                    }
                }
            });

            $complete_clear.click(function() {
                complete_fp.clear();
                $(this).fadeOut('fast');
            });

            $duration_picker.inputmask('9{1,4}hr:99min', {
                numericInput: true,
                placeholder: "_",
                removeMaskOnSubmit: true
            }).on('keyup', function () {
                var duration = this.inputmask.unmaskedvalue(),
                    hour, min;
                if (duration === '') {
                    $completed_picker[0]._flatpickr.setDate('', true);
                    $complete_clear.fadeOut('fast');
                    return;
                }
                if (duration.length <= 2) {
                    hour = 0;
                    min = parseInt(duration);
                } else {
                    hour = parseInt(duration.substring(0, duration.length - 2));
                    min = parseInt(duration.substring(duration.length - 2));
                }
                $completed_picker[0]._flatpickr.setDate(
                    moment($start_picker.val(), siteConfig.MOMENT_DATETIME_FMT).add(hour, 'hours').add(min, 'minutes').valueOf()
                );
                $complete_clear.fadeIn('fast');
            });

            if ($start_picker[0]._flatpickr.selectedDates && $completed_picker[0]._flatpickr.selectedDates) {
                setDuration($start_picker[0]._flatpickr.selectedDates[0], $completed_picker[0]._flatpickr.selectedDates[0]);
            }
        }

        //////// Warning message
        var box_perform = $('#box-perform .box'),
            box_perform_header = $(box_perform).find('.box-header, .box-footer'),
            // box_perform_footer = $(box_perform).find('.box-footer'),
            sub_button = $('#submit-qa'),
            do_not_treat = $('.do-not-treat');

        function display_fail(fail) {
            if (do_not_treat.length === 0){
                return;
            }
            if (fail){
                do_not_treat.show();
                box_perform.switchClass('box-pho-borders', 'box-danger box-red-borders', 1000);
                sub_button.switchClass('btn-primary', 'btn-danger', 1000);
                box_perform_header.addClass('red-bg', 1000);

            }else{
                box_perform.switchClass('box-danger box-red-borders', 'box-pho-borders', 1000);
                sub_button.switchClass('btn-danger', 'btn-primary', 1000);
                box_perform_header.removeClass('red-bg', 1000, function() {
                    do_not_treat.hide();
                });
            }
        }

        /// Sublist
        $("a.show-sublist-details").click(function(){
            var tr = $(this).parent().parent().next();
            tr.find('.procedure-bar').slideToggle('fast').toggleClass('in');
            return false;
        });

        set_tab_stops();

        var $service_events = $('.service-event-btn');
		$.each($service_events, function(i, v) {
			var $service_event = $(this);
            var colour = $service_event.attr('data-bgcolour');
            $service_event.css('background-color', colour);
            $service_event.css('border-color', colour);
            if ($service_event.length > 0) {
                if (isTooBright(rgbaStringToArray($service_event.css('background-color')))) {
                    $service_event.css('color', 'black').children().css('color', 'black');
                }
                else {
                    $service_event.css('color', 'white').children().css('color', 'white');
                }
            }

            $service_event.hover(
                function () {
                    $(this).css(
                        'background-color',
                        lightenDarkenColor(rgbaStringToArray($(this).css('background-color')), -15)
                    );
                },
                function () {
                    $(this).css('background-color', $(this).attr('data-bgcolour'));
                }
            );
        });

		$('#id_in_progress').cheekycheck({
            right: true,
            check: '<i class="fa fa-check"></i>',
            extra_class: 'warning'
        });

		$('#id_initiate_service').cheekycheck({
            right: true,
            check: '<i class="fa fa-check"></i>',
            extra_class: 'warning'
        });

    });
});

})(); /* use strict IIFE */
