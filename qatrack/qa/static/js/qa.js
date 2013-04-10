"use strict";
/***************************************************************/
//Test statuse and Table context used to narrow down jQuery selectors.
//Improves performance in IE
var context = $("#perform-qa-table")[0];
var test_statuses = $("td.qa-status",context);
var fail_warnings = $("#do-not-treat-bottom, #do-not-treat-top");
var pass_fail_only = $("#pass-fail-only").val() === "yes" ? true : false;

/***************************************************************/
//Set up the values we will need to do validation on data
var validation_data = {};
var composite_ids = {};

/***************************************************************/
//set the intitial values, tolerances & refs for all of our tests
function initialize_qa(){

    var rows = $(".qa-valuerow",context);
    var i;
    for (i=0; i< rows.length; i++){
        //loop over each row containing a qa test and grab relevant info
        var row = $(rows[i]);
        var context_name = row.find(".qa-contextname").val();

        var reference = {
            value:parseFloat(row.find(".qa-reference-val").val()),
            pk:row.find(".qa-reference-pk").val()
        };

        var tolerances = {
            act_low:parseFloat(row.find(".act_low").val()),
            tol_low:parseFloat(row.find(".tol_low").val()),
            tol_high:parseFloat(row.find(".tol_high").val()),
            act_high:parseFloat(row.find(".act_high").val()),
            mc_pass_choices:QAUtils.non_empty(row.find(".mc_pass_choices").val().split(',')),
            mc_tol_choices:QAUtils.non_empty(row.find(".mc_tol_choices").val().split(',')),
            type:row.find(".qa-tolerance-type").val(),
            pk:row.find(".qa-tolerance-pk").val()

        };

        //update global validation object with data
        validation_data[context_name] = {
            name:context_name,
            tolerances:tolerances,
            reference:reference,
            current_value: get_value_for_test(context_name)
        };

    }


    //store ids and names for all composite tests
    $('.qa-testtype[value="composite"]',context).each(function(){
        var row = $(this).parents(".qa-valuerow");
        var test_id = row.find('.qa-test-id').val();
        var name = row.find('.qa-contextname').val();
        composite_ids[name] = test_id;
    });
}
/***************************************************************/
//Perform Ajax calls to calculate all composite values
function calculate_composites(){
    if ($("#contains-composites").val() !== "yes"){
        return
    }
    var submit = $('#submit-qa');
    submit.attr("disabled", true);
    var data = {
        qavalues:JSON.stringify(validation_data),
        composite_ids:JSON.stringify(composite_ids)
    };
    
    var on_success = function(data){
        submit.attr("disabled", false);

        if (data.success){
            $.each(data.results,function(name,result){
                set_value_by_name(name,result.value);
            });
        }
    }

    var on_error = function(){
        submit.attr("disabled", false);
    }

    QAUtils.call_api(QAUtils.COMPOSITE_URL,"POST",data,on_success,on_error);
}

/***************************************************************/
//Check the tolerances for a single input and format appropriately
function check_test_status(name){

    var test_type = $("#testtype-"+name).val();
    var qastatus = $("#status-"+name);
    var val = get_value_for_test(name);

    //update the current value of the test that just changed and check tolerances
    validation_data[name].current_value = val;

    //remove any previous formatting
    qastatus.removeClass("btn-danger btn-warning btn-success btn-info");
    qastatus.text("Not Done");

    if ($("#skip-"+name+" input").is(":checked")){
        return;
    }

    //ensure numerical value and highlight input element appropriately

    if ((val === "") || (val === null)){
        return;
    }

    //check the value versus the reference
    var tolerances = validation_data[name].tolerances;
    var reference = validation_data[name].reference;

    var result = QAUtils.test_tolerance(val,reference.value,tolerances, test_type,pass_fail_only);

    //update formatting with result
    qastatus.text(result.message);
    if (result.gen_status === QAUtils.WITHIN_TOL){
        qastatus.addClass("btn-success");
    }else if(result.gen_status === QAUtils.TOLERANCE){
        qastatus.addClass("btn-warning");
    }else if(result.gen_status === QAUtils.ACTION){
        qastatus.addClass("btn-danger");
    }else{
        qastatus.addClass("btn-info");
    }

}

/***************************************************************/
//Return the value of the input for the given test name (slug)
function get_value_for_test(name){
    var test_type = $("#testtype-"+name).val();
    var val;

    if (test_type === QAUtils.BOOLEAN){
        var checked = $("#value-"+name+" :checked");
        if (checked.length > 0){
            return parseFloat(checked.val());
        }else{
            return null;
        }
    }else if (test_type === QAUtils.MULTIPLE_CHOICE){
        var selected = $("#value-"+name+" :selected");

        val = $.trim(selected.text());
        if (val !== ""){
            return val;
        }else{
            return null;
        }

    }else {
        val = $("#value-"+name+" input").val();
        if ($.trim(val) === ""){
            return "";
        }

        val = parseFloat(val);
        if (isNaN(val)){
            return null;
        }else{
            return val;
        }
    }

}

/***************************************************************/
//set the value of an input by using it's name
function set_value_by_name(name, value){
    var input = $("#value-"+name+" input");
    if (QAUtils.is_number(value)){
        value =QAUtils.format_float(value);
    }
    input.val(value);
    check_test_status(name);
    check_skip_status(name);
    update_qa_status();
}

/***************************************************************/
//determine whether an input box contains a float
function valid_input(input_element){
    return (!isNaN(parseFloat(input_element.val())) && $.trim(input_element.val()) !== "") ;
}

/***************************************************************/
//perform a full validation of all data (for example on page load after submit)
function full_validation(){
    calculate_composites();

    var i;
    var names = $(".qa-contextname",context);
    for (i=0; i < names.length; i++){
        check_test_status(names[i].value);
    }

    update_qa_status();

}

/***************************************************************/
//Filter table rows by category and mark anything hidden as being skipped
function filter_by_category(){

    var selected_categories = new Array();
    var not_performed = "Category not performed";

    $("#category_filter option:selected").each(function(){
        selected_categories.push($(this).val());
    });

    var show_all = (selected_categories.length === 0) ||
        ($.inArray("all",selected_categories) >= 0);

    var cmt;

    if (show_all){
        $(".qa-valuerow").show();
        $(".qa-comment, .qa-procedure").hide();
        $(".qa-skip input").attr("checked",false);
        $(".qa-comment textarea").each(function(){
            $(this).val($(this).val().replace(not_performed,""));
        })
        return;
    }

    //loop over each qa-value row and show or hide related rows
    $(".qa-valuerow").each(function(e){

        var category = $(this).find("td.qa-category").text().toLowerCase();

        var to_toggle = $(this);
        to_toggle.add($(this).nextUntil(".qa-valuerow"));
        to_toggle.add($(this).prevUntil(".qa-valuerow"));

        if ($.inArray(category,selected_categories) < 0){
            $(this).find(".qa-skip input").attr("checked",true);
            $(this).next().find("textarea").val(not_performed);
            to_toggle.hide();
        }else{
            $(this).find(".qa-skip input").attr("checked",false);
            $(this).next().find("textarea").val($(this).next().find("textarea").val().replace(not_performed,""));
            to_toggle.show();
        }
    });
};

/***************************************************************/
//set link for cycle when user changes cycle day dropdown
function set_cycle_day(){
    var day = $("#cycle-day option:selected").val();
    var cur = document.location.href;
    var next = cur.replace(/day=(next|[1-9])/,"day="+day);

    document.location.href = next;
}

/***************************************************************/
function confirm_leave_page(){
    var confirm_msg = "If you leave this page now you will lose all entered values.";
    var inp_type;
    var inputs = $(".qa-input");
    var inp;
    var inp_idx;

    for (inp_idx=0; inp_idx < inputs.length; inp_idx++){
        inp = $(inputs[inp_idx]);
        inp_type = inp.attr("type")
        if ((inp_type === "radio") && inp.is(":checked")){
            return confirm_msg;
        }else if((inp_type === "text") && (inp.val() !== "")){
            return confirm_msg;
        }else if((inp_type !== "radio") && (inp_type !== "text")){
            return "Unknown input type";
        }
    }
}

/****************************************************************/
function check_skip_status(name){
    var val = get_value_for_test(name);
    if (val !== "") {
        $("#skip-"+name+" input").attr("checked",false);
    }
}
/****************************************************************/
function update_qa_status(){
    var i;
    for (i=0;i<test_statuses.length;i++){
        if ($(test_statuses[i]).hasClass("btn-danger")){
            fail_warnings.show();
            return;
        }
    }

    fail_warnings.hide();
}

function update_time(input){
    if (input.attr("name") === "work_completed"){
        input.val(input.val()+" 20:30");
    }else{
        input.val(input.val()+" 19:30");
    }
}
/****************************************************************/
function set_comment_icon(input){
    var icon = $(input).parents("tr").prev("tr").find(".qa-showcmt i");
    icon.removeClass();
    if ( $.trim($(input).val()) != ''){
        icon.addClass("icon-comment");
    }else{
        icon.addClass("icon-edit");
    }

}
/****************************************************************/
$(document).ready(function(){
    var that = $(this);

    var composites = $('.qa-testtype[value="composite"]',context);
    if (composites.length <= 0){
        $("#contains-composites").val("no");
    }else{
        $("#contains-composites").val("yes");
    }

    $("#test-list-info-toggle").click(function(){
        $("#test-list-info").toggle(600);
    });

    //show comment when clicked
    $(".qa-showcmt a",context).click(function(){
      $(this).parent().parent().nextAll(".qa-comment").first().toggle(600);
      return false;
    });

    //show comment when clicked
    $("#toggle-gen-comment").click(function(){
      $(".qa-tli-comment textarea").toggle(600);
      return false;
    });

    $(".qa-comment textarea",context).blur(function(){
        set_comment_icon($(this));
    });
    _.map($(".qa-comment textarea"),set_comment_icon);

    //toggle contacts
    $("#toggle-contacts").click(function(){
        $("#contacts").toggle();

        var visible = $("#contacts").is(":visible");
        var icon = "icon-plus-sign";
        if (visible) {
            icon = "icon-minus-sign";
        }

        $("#toggle-contacts i").removeClass("icon-plus-sign icon-minus-sign").addClass(icon);

    });

    $(".qa-showproc a").click(function(){
      $(this).parent().parent().nextAll(".qa-procedure").first().toggle(600);
      return false;
    });


    initialize_qa();

    var user_inputs=  $('.qa-input',context).not("[readonly=readonly]").not("[type=hidden]");
    var visible_user_inputs = user_inputs;

    //anytime an input changes run validation
    user_inputs.change(function(){
//        var name = $(this).parents("td").siblings(".qa-contextname").val();
        var name = $(this).parents("tr.qa-valuerow").find(".qa-contextname").val();
        check_skip_status(name);

        if (this.type === "text"){
            this.value = QAUtils.clean_numerical_value(this.value);
        }
        check_test_status(name);
        calculate_composites();
        update_qa_status();
    });

    //run filter routine anytime user alters the categories
    $("#category_filter").change(function(){
        filter_by_category();
        visible_user_inputs = user_inputs.filter(':visible');
    });

    //update the link for user to change cycles
    $("#cycle-day").change(set_cycle_day);

    //allow arrow key and enter navigation
    $(that).on("keydown","input, select", function(e) {

        var to_focus;
        //rather than submitting form on enter, move to next value
        if (e.which == QAUtils.KC_ENTER  || e.which == QAUtils.KC_DOWN ) {
            var idx = visible_user_inputs.index(this);

            if (idx == user_inputs.length - 1) {
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

    //make sure user actually want's to go back
    //this is here to help mitigate the risk that a user hits back or backspace key
    //by accident and completely hoses all the information they've entered during
    //a qa session
    $(window).bind("beforeunload",confirm_leave_page);
    $("#qa-form").submit(function(){
        $(window).unbind("beforeunload")
    });

    $("#qa-form").preventDoubleSubmit();

    //automatically unhide comment if test is being skipped
    $(".qa-skip input").click(function(){
        if ($(this).is(':checked')){
            $(this).parent().parent().next().show(600);
            $(this).parents(".qa-valuerow").find("input[type=radio]").attr("checked",false);
        }else{
           $(this).parent().parent().next().hide(600);
        }
    });

    $("#work-completed, #work-started").datepicker({
        autoclose:true,
        keyboardNavigation:false
    }).on('changeDate',function (ev){
        update_time($(this).find("input"));
    });

    //run a full validation on page load
    full_validation();

    var tabindex = 1;
    user_inputs.each(function() {
        $(this).attr("tabindex", tabindex);
        tabindex++;
    });
    user_inputs.first().focus();

});

