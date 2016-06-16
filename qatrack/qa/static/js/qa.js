"use strict";


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
jQuery.Topic = function( id ) {
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

function Status(status,diff,message){
    this.status = status;
    this.diff = diff;
    this.message = message;
}
var NO_TOL = new Status(QAUtils.NO_TOL,"",QAUtils.NO_TOL_DISP);
var NOT_DONE = new Status(QAUtils.NOT_DONE,"",QAUtils.NOT_DONE_DISP);
var DONE = new Status(QAUtils.DONE,"",QAUtils.DONE_DISP);

function TestInfo(data){
    var self = this;
    this.id = data.id;
    this.test = new Test(data.test);
    this.reference = new Reference(data.reference);
    this.tolerance = new Tolerance(data.tolerance);


    this.check_value = function(value){
        var result = self.check_dispatch[self.test.type](value)
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
        if (_.isEmpty(self.reference)){
            return NO_TOL;
        }else if (QAUtils.almost_equal(value,self.reference.value)){
            return new Status(QAUtils.WITHIN_TOL,0,QAUtils.WITHIN_TOL_DISP);
        }

        return new Status(QAUtils.ACTION,1,QAUtils.ACTION_DISP);
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

    this.check_upload = function(value){
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

    this.check_dispatch = {}
    this.check_dispatch[QAUtils.BOOLEAN]=this.check_bool;
    this.check_dispatch[QAUtils.MULTIPLE_CHOICE]=this.check_multi;
    this.check_dispatch[QAUtils.CONSTANT]=this.check_numerical;
    this.check_dispatch[QAUtils.SIMPLE]=this.check_numerical;
    this.check_dispatch[QAUtils.COMPOSITE]=this.check_numerical;
    this.check_dispatch[QAUtils.STRING_COMPOSITE]=this.check_multi;
    this.check_dispatch[QAUtils.STRING]=this.check_multi;
    this.check_dispatch[QAUtils.UPLOAD]=this.check_upload;

    this.calculate_diff = function(value){
        if (self.tolerance.type === QAUtils.PERCENT){
            return 100.*(value-self.reference.value)/self.reference.value;
        }
        return value - self.reference.value;
    };

    this.diff_display = function(diff){

        if (self.tolerance.type === QAUtils.PERCENT){
            return "(" + diff.toFixed(1)+"%)";
        }
        return "(" + diff.toFixed(2)+")";
    }

}

function TestInstance(test_info, row){
    var self = this;
    this.initialized = false;
    this.test_info = test_info;
    this.row = $(row);
    this.inputs = this.row.find("td.qa-value").find("input, textarea, select");

    this.visible = true;

    this.status = this.row.find("td.qa-status");
    this.test_status = null;

    this.skip = this.row.find("td.qa-skip input");
    this.skipped = false;
    this.set_skip = function(skipped){
        self.skipped = skipped;
        self.skip.prop("checked",self.skipped);
    }
    this.skip.change(function(){
        self.skipped = self.skip.is(":checked");
        if (self.skipped){
            if (comment_on_skip && !self.test_info.test.skip_without_comment){
                self.comment.show(600);
            }
            if (self.test_info.test.type === QAUtils.BOOLEAN || self.test_info.test.type === QAUtils.UPLOAD){
                self.set_value(null);
            }
            $.Topic("valueChanged").publish();
        }else{
            self.comment.hide(600);
        }
    });

    this.show_comment = this.row.find("td.qa-showcmt a");
    this.comment = this.row.next();
    this.comment_box = this.comment.find("textarea");
    this.comment_icon = this.row.find(".qa-showcmt i");

    this.show_comment.click(function(){
        self.comment.toggle(600);
        return false;
    });
    this.set_comment_icon = function(){
        self.comment_icon.removeClass();
        if ( $.trim(self.comment_box.val()) != ''){
            self.comment_icon.addClass("icon-comment");
        }else{
            self.comment_icon.addClass("icon-edit");
        }
    }
    this.set_comment_icon(); //may already contain comment on initialization
    this.comment_box.blur(this.set_comment_icon);

    this.show_procedure = this.row.find("td.qa-showproc a");
    this.procedure = this.comment.next();
    this.show_procedure.click(function(){
        self.procedure.toggle(600);
        return false;
    });


    this.value = null;

    this.inputs.change(function(){
        self.update_value_from_input();
        if (self.skipped){
            self.set_skip(false);
        }
        $.Topic("valueChanged").publish();
        $.Topic("qaUpdated").publish();
    });

    this.set_value = function(value){
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
        }else if (tt=== QAUtils.STRING || tt === QAUtils.MULTIPLE_CHOICE || tt === QAUtils.STRING_COMPOSITE){
            self.inputs.val(value);
        }else if (tt === QAUtils.UPLOAD){
            if (_.isNull(value)){
                self.inputs.filter(":hidden").val("");
            }else{
                self.inputs.filter(":hidden").val(value["temp_file_name"]);
                self.value = value.result;
            }
        }else if (tt === QAUtils.SIMPLE || tt === QAUtils.COMPOSITE){
            if (_.isNull(value)){
                self.inputs.val("");
            }else{
                self.inputs.val(QAUtils.format_float(value));
            }
        }

        this.update_status();
    }

    this.update_value_from_input = function(){

        var tt = self.test_info.test.type;
        if (tt === QAUtils.BOOLEAN){
            var value = parseFloat(self.inputs.filter(":checked").val());
            self.value = _.isNaN(value) ? null : value;
        }else if (tt === QAUtils.MULTIPLE_CHOICE){
            var value = $.trim(self.inputs.find(":selected").text());
            self.value = value !== "" ? value : null;
        }else if (tt=== QAUtils.UPLOAD){
            if (editing_tli && !this.initialized){
                var data = {
                    filename: self.inputs.val(),
                    test_id: self.test_info.test.id,
                    test_list_instance: editing_tli,
                    meta: JSON.stringify(get_meta_data()),
                    refs: JSON.stringify(get_ref_data()),
                    tols: JSON.stringify(get_tol_data())
                };

                $.ajax({
                    type:"POST",
                    url: QAURLs.UPLOAD_URL,
                    data: $.param(data),
                    dataType:"json",
                    success: function (result) {
                        self.status.removeClass("btn-info btn-primary btn-danger btn-success");
                        if (result.errors.length > 0){
                            self.set_value(null);
                            self.status.addClass("btn-danger").text("Failed");
                            self.status.attr("title",result.errors[0]);
                        }else{
                            self.set_value(result);
                            self.status.addClass("btn-success").text("Success");
                            self.status.attr("title",result['temp_file_name']);
                            $.Topic("valueChanged").publish();
                        }
                    },
                    traditional:true,
                    error: function(e,data){
                        self.set_value(null);
                        self.status.removeClass("btn-primary, btn-danger, btn-success");
                        self.status.addClass("btn-danger").text("Server Error");
                    }
                });
            }

        }else if (tt=== QAUtils.STRING){
            self.value = self.inputs.val();
        }else {
            self.inputs.val(QAUtils.clean_numerical_value(self.inputs.val()));
            var dots = self.inputs.val().match(/\./g);
            if (dots===null || dots.length <= 1) {
                var value = parseFloat(self.inputs.val());
            }else {
                var value = NaN
            }
            self.value = _.isNaN(value) ? null : value;
        }

        this.update_status();
        this.initialized = true;
    }
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

        self.status.html(status.message);
        self.status.removeClass("btn-success btn-warning btn-danger btn-info");
        self.test_status = status.status;
        if (status.status === QAUtils.WITHIN_TOL){
            self.status.addClass("btn-success");
        }else if(status.status === QAUtils.TOLERANCE){
            self.status.addClass("btn-warning");
        }else if(status.status === QAUtils.ACTION){
            self.status.addClass("btn-danger");
        }else if(status.status !== QAUtils.NOT_DONE){
            self.status.addClass("btn-info");
        }
    };

    this.NOT_PERFORMED = "Category not performed";

    this.show = function(){
        self.row.show();
        self.comment.hide();
        self.procedure.hide();
        self.set_skip(false);
        self.visible = true;
        self.comment_box.val(self.comment_box.val().replace(self.NOT_PERFORMED,""));
        if (self.test_info.test.type == QAUtils.BOOLEAN){
            self.set_value(self.value);
        }

    }

    this.hide = function(){
        self.row.hide();
        self.comment.hide();
        self.procedure.hide();
        self.visible = false;

        // skipping sets value to null but we want to presever value in case it
        // is unfiltered later. Filtered values will be nulled on submitt
        var tmp_val = self.value;
        self.set_skip(true);
        self.set_value(tmp_val);
        if (self.test_info.test.type == QAUtils.BOOLEAN){
            self.inputs.prop("checked", false);
        }

        self.comment_box.val(self.NOT_PERFORMED);
    }

    var csrf_token = $("input[name=csrfmiddlewaretoken]").val();

    this.inputs.filter(".file-upload").each(function(){

        $(this).fileupload({

            dataType: 'json',
            url: QAURLs.UPLOAD_URL,
            dropZone:self.row.children(),
            singleFileUploads: true,
            paramName:"upload",
            replaceFileInput:false,
            formData: function(){
                return [
                    { name:"test_id", value: self.test_info.test.id},
                    { name:"meta", value:JSON.stringify(get_meta_data())},
                    { name:"refs", value:JSON.stringify(get_ref_data())},
                    { name:"tols", value:JSON.stringify(get_tol_data())},
                    { name:"csrfmiddlewaretoken", value:csrf_token}
                ]
            },
            done: function (e, data) {
                self.status.removeClass("btn-info btn-primary btn-danger btn-success");
                if (data.result.errors.length > 0){
                    self.set_value(null);
                    self.status.addClass("btn-danger").text("Failed");
                    self.status.attr("title",data.result.errors[0]);
                }else{
                    self.set_value(data.result);
                    self.status.addClass("btn-success").text("Success");
                    self.status.attr("title",data.result['temp_file_name']);

                    // Display Image if required
                    if (data.result.is_image){
                        var image_url = QAURLs.MEDIA_URL + "uploads/tmp/" + data.result.temp_file_name;
                        self.display_image(image_url);
                     }

                    $.Topic("valueChanged").publish();
                }
            },
            fail: function(e,data){
                self.set_value(null);
                self.status.removeClass("btn-primary, btn-danger, btn-success");
                self.status.addClass("btn-danger").text("Server Error");
            },
            progressall: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                self.status.removeClass("btn-primary, btn-danger, btn-success");
                self.status.addClass("btn-warning").text(progress+"%");
            }

        })
    });
    //Set initial value
    this.update_value_from_input();
    // Display images
    self.display_image = function(url){
        var id = self.test_info.test.slug;
        var name = self.test_info.test.name;
        var test_name = '<strong><p>Test name: '+ name + '</p></strong>';
        var img_tag =  '<img src="'+ url+ '" class="qa-image">';
        var html = test_name + img_tag;
        if (self.test_info.test.display_image){
          $("#qa-images").css({"display": "block"});
          $("#" + id).addClass("qa-image-box").html(html);
        }
    };
}

function get_meta_data(){

    var meta = {
        test_list_name: $("#test-list-name").val(),
        unit_number: parseInt($("#unit-number").val()),
        cycle_day: parseInt($("#cycle-day-number").val()),
        work_completed: QAUtils.parse_date($("#id_work_completed").val()),
        work_started: QAUtils.parse_date($("#id_work_started").val()),
        username: $("#username").text()
    };

    return meta;

}

function get_ref_data(){
    var ref_values = _.map(tli.test_instances, function(ti){
        return ti.test_info.reference.value ? ti.test_info.reference.value : null;
    });

    return _.object(_.zip(tli.slugs, ref_values));
}

function get_tol_data(){

    var tol_properties = ["act_high", "act_low", "tol_high", "tol_low", "mc_pass_choices", "mc_tol_choices", "type"];

    var tol_values = _.map(tli.test_instances, function(ti){
        var tol = ti.test_info.tolerance;
        return !tol.id ? null : _.pick(tol, tol_properties);
    });
    return _.object(_.zip(tli.slugs, tol_values));
}

function TestListInstance(){
    var self = this;

    this.test_instances = [];
    this.tests_by_slug = {};
    this.slugs = [];
    this.composites = [];
    this.composite_ids = [];

    this.submit = $("#submit-qa");

    /***************************************************************/
    //set the intitial values, tolerances & refs for all of our tests
    this.initialize = function(){
        var test_infos = _.map(window.unit_test_infos,function(e){ return new TestInfo(e)});

        self.test_instances = _.map(_.zip(test_infos, $("#perform-qa-table tr.qa-valuerow")), function(uti_row){return new TestInstance(uti_row[0], uti_row[1])});
        self.slugs = _.map(self.test_instances, function(ti){return ti.test_info.test.slug});
        self.tests_by_slug = _.object(_.zip(self.slugs,self.test_instances));
        self.composites = _.filter(self.test_instances,function(ti){return ti.test_info.test.type === QAUtils.COMPOSITE || ti.test_info.test.type === QAUtils.STRING_COMPOSITE;});
        self.composite_ids = _.map(self.composites,function(ti){return ti.test_info.test.id;});
        self.calculate_composites();
    }


    this.calculate_composites = function(){


        if (self.composites.length === 0){
            return;
        }


        var cur_values = _.map(self.test_instances,function(ti){return ti.value;});
        var qa_values = _.object(_.zip(self.slugs,cur_values));
        var meta = get_meta_data();
        var refs = get_ref_data();
        var tols = get_tol_data();

        var data = {
            qavalues:qa_values,
            composite_ids:self.composite_ids,
            meta: meta,
            refs: refs,
            tols: tols
        };

        var on_success = function(data, status, XHR){
            if (latest_composite_call !== XHR){
                return;
            }

            self.submit.attr("disabled", false);

            if (data.success){
                _.each(data.results,function(result, name){
                    var ti = self.tests_by_slug[name];
                    if (!ti.skipped){
                        ti.set_value(result.value);
                    }
                });
            }
            $.Topic("qaUpdated").publish();
        }

        var on_error = function(){
            self.submit.attr("disabled", false);
            $.Topic("qaUpdated").publish();
        }

        self.submit.attr("disabled", true);

        latest_composite_call = $.ajax({
            type:"POST",
            url:QAURLs.COMPOSITE_URL,
            data:JSON.stringify(data),
            contentType:"application/json",
            dataType:"json",
            success: on_success,
            traditional:true,
            error:on_error
        });
    };

    this.has_failing = function(){
        return _.filter(self.test_instances,function(ti){return ti.test_status === QAUtils.ACTION}).length > 0;
    };

    $.Topic("categoryFilter").subscribe(function(categories){
        _.each(self.test_instances,function(ti){
            if (categories === "all" || _.contains(categories,ti.test_info.test.category.toString())){
                ti.show();
            }else{
                ti.hide();
            }
        });
        $.Topic("qaUpdated").publish();
    });

    $.Topic("valueChanged").subscribe(self.calculate_composites);
}



/***************************************************************/
function set_tab_stops(){

    var user_inputs=  $('.qa-input',context).not("[readonly=readonly]").not("[type=hidden]");
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

        var to_focus;
        //rather than submitting form on enter, move to next value
        if (e.which == QAUtils.KC_ENTER  || e.which == QAUtils.KC_DOWN ) {
            var idx = visible_user_inputs.index(this);

            if (idx == visible_user_inputs.length - 1) {
                to_focus= visible_user_inputs.first();
            } else {
                to_focus = visible_user_inputs[idx+1];
            }
            to_focus.focus()
            if (to_focus.type === "text"){
                to_focus.select();
            }
            return false;
        }else if (e.which == QAUtils.KC_UP ){
            var idx = visible_user_inputs.index(this);

            if (idx == 0) {
                to_focus = visible_user_inputs.last();
            } else {
                to_focus = visible_user_inputs[idx-1];
            }
            to_focus.focus()
            if (to_focus.type === "text"){
                to_focus.select();
            }
            return false;
        }
    });

}


var tli;

/****************************************************************/
$(document).ready(function(){

    tli = new TestListInstance();
    tli.initialize();

    context = $("#perform-qa-table")[0];

    pass_fail_only = $("#pass-fail-only").val() === "yes" ? true : false;
    comment_on_skip = $("#require-comment-on-skip").val() === "yes" ? true : false;

    $("#test-list-info-toggle").click(function(){ $("#test-list-info").toggle(600); });

    //toggle general comment
    $("#toggle-gen-comment").click(function(){
        $("#id_comment").toggle();
    });

    //toggle contacts
    $("#toggle-contacts").click(function(){
        $("#contacts").toggle();

        var icon = $("#contacts").is(":visible") ? "icon-minus-sign" : "icon-plus-sign";
        $("#toggle-contacts i").removeClass("icon-plus-sign icon-minus-sign").addClass(icon);
    });

    //set link for cycle when user changes cycle day dropdown
    $("#cycle-day").change(function(){
        var day = $("#cycle-day option:selected").val();
        var cur = document.location.href;
        var next = cur.replace(/day=(next|[0-9]+)/,"day="+day);
        document.location.href = next;
    });

    //run filter routine anytime user alters the categories
    $("#category_filter").change(function(){
        var categories = $(this).val();
        if (categories === null  || _.contains(categories,"all")){
            $.Topic("categoryFilter").publish("all");
        }else{
            $.Topic("categoryFilter").publish(categories);
        }
        $.Topic("categoryFilterComplete");
    });


    //make sure user actually want's to go back
    //this is here to help mitigate the risk that a user hits back or backspace key
    //by accident and completely hoses all the information they've entered during
    //a qa session
    $(window).bind("beforeunload",function(){
        if (_.any(_.pluck(tli.test_instances,"value"))){
            return  "If you leave this page now you will lose all entered values.";
        }
    });

    $("#qa-form").preventDoubleSubmit().submit(function(){
        $(window).unbind("beforeunload");
    });

    $("#work-completed, #work-started").datepicker({
        autoclose:true,
        keyboardNavigation:false
    }).on('changeDate',function (ev){
        // Set times to default values after a date is chosen
        // If the current date is selected, the time defaults to  the current time
        // otherwise 19:30 for work started and 20:30 for work completed

        var input = $(this).find("input");
        var cur_val = input.val();

        var now = new Date();

        var zero_pad = function(inp){return inp < 10 ? '0'+inp : inp;};

        var date = zero_pad(now.getDate());
        var month = zero_pad(now.getMonth()+1);
        var year = now.getFullYear();
        var hours = zero_pad(now.getHours());
        var mins = zero_pad(now.getMinutes());

        var now_str = date +'-'+ month + '-'+year;

        if (now_str === cur_val){
            input.val(cur_val+" "+hours+":"+mins);
        }else if (input.attr("name") === "work_completed"){
            input.val(cur_val+" 20:30");
        }else{
            input.val(cur_val+" 19:30");
        }
    });

    var fail_warnings = $("#do-not-treat-bottom, #do-not-treat-top");
    $.Topic("qaUpdated").subscribe(function(){
        if (self.tli.has_failing()){
            fail_warnings.show();
        }else{
            fail_warnings.hide();
        }
    });


    set_tab_stops();


});
