"use strict";

/***************************************************************/
//Set up the values we will need to do validation on data
var validation_data = {};
var composite_ids = {};

/***************************************************************/
//set the intitial values, tolerances & refs for all of our tests
function initialize_qa(){

    $(".qa-valuerow").each(function(order){
        //loop over each row containing a qa test and grab relevant info


        var context_name = $(this).find(".qa-contextname").val();

        var reference = {
            value:parseFloat($(this).find(".qa-reference-val").val()),
            pk:$(this).find(".qa-reference-pk").val()
        };

        var tolerances = {
            act_low:parseFloat($(this).find(".act_low").val()),
            tol_low:parseFloat($(this).find(".tol_low").val()),
            tol_high:parseFloat($(this).find(".tol_high").val()),
            act_high:parseFloat($(this).find(".act_high").val()),
            type:$(this).find(".qa-tolerance-type").val(),
            pk:$(this).find(".qa-tolerance-pk").val()

        };

        //update global validation object with data
        validation_data[context_name] = {
            name:context_name,
            tolerances:tolerances,
            reference:reference,
            current_value: get_value_for_row($(this))
        };

    });


    //store ids and names for all composite tests
    $('.qa-testtype[value="composite"]').each(function(){
        var row = $(this).parents(".qa-valuerow");
        var test_id = row.find('input[name$="-test"]').val();
        var name = row.find('.qa-contextname').val();
        composite_ids[name] = test_id;
    });
}
/***************************************************************/
//Perform Ajax calls to calculate all composite values
function calculate_composites(){

    var composites = $('.qa-testtype[value="composite"]');
    if (composites.length <= 0){
        return;
    }

    $.ajax({
        url:"/qa/composite/",
        type:"POST",
        data:{
            qavalues:JSON.stringify(validation_data),
            composite_ids:JSON.stringify(composite_ids)
        },
        success: function(data){
            if (data.success){
                $.each(data.results,function(name,result){
                    set_value_by_name(name,result.value);
                });
            }
        },
        dataType:"json"
    });

}

/***************************************************************/
//Check the tolerances for a single input and format appropriately
function check_test_status(input_element){

    var parent = input_element.parents("tr:first");
    var name = parent.find(".qa-contextname").val();
    var test_type = parent.find(".qa-testtype").val();
    var qastatus = parent.find(".qa-status");
    var val = get_value_for_row(input_element.parents(".qa-valuerow"));

    //update the current value of the test that just changed and check tolerances
    validation_data[name].current_value = val;

    //remove any previous formatting
    qastatus.removeClass("btn-danger btn-warning btn-success btn-info");
    qastatus.text("Not Done");

    if (parent.find(".qa-skip input").is(":checked")){
        return;
    }

    //ensure numerical value and highlight input element appropriately
    set_valid_input(input_element);
    if (val === ""){
        return;
    }else if (val === null){
        set_invalid_input(input_element);
        return;
    }

    //check the value versus the reference
    var tolerances = validation_data[name].tolerances;
    var reference = validation_data[name].reference;

    var result = QAUtils.test_tolerance(val,reference.value,tolerances, test_type);

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
//Take an qavaluerow and return the value of the input contained within it
function get_value_for_row(input_row_element){
    var test_type = $(input_row_element).find(".qa-testtype").val();
    var val;
    if (test_type === QAUtils.BOOLEAN){
        if ($(input_row_element).find(":checked").length > 0){
            return parseFloat($(input_row_element).find(":checked").val());
        }else{
            return null;
        }
    }else if (test_type === QAUtils.MULTIPLE_CHOICE){
        val = $(input_row_element).find(":selected").val();
        if (val !== ""){
            return parseFloat(val);
        }else{
            return null;
        }

    }else {
        val = input_row_element.find(".qa-value input").val();
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
    var row = $('.qa-contextname[value="'+name+'"]').parents(".qa-valuerow");
    var input = row.find(".qa-value input");
    input.val(value);
    check_test_status(input);
}

/***************************************************************/
//mark an input box as having invalid input
function set_invalid_input(input_element){
    input_element.parents(".control-group").removeClass("success");
    input_element.parents(".control-group").addClass("error");
}
/***************************************************************/
//mark an input box as having valid input
function set_valid_input(input_element){
    input_element.parents(".control-group").removeClass("error");
    input_element.parents(".control-group").addClass("success");
}

/***************************************************************/
//determine whether an input box contains a float
function valid_input(input_element){
    return (!isNaN(parseFloat(input_element.val())) && $.trim(input_element.val()) !== "") ;
}

/***************************************************************/
//perform a full validation of all data (for example on page load after submit)
function full_validation(){
    $(".qa-input").each(function(){
        check_test_status($(this));
        calculate_composites();
    });
}

/***************************************************************/
//Filter table rows by category and mark anything hidden as being skipped
function filter_by_category(){

    var selected_categories = new Array();
    $("#category_filter option:selected").each(function(){
        selected_categories.push($(this).val());
    });

    var show_all = (selected_categories.length === 0) ||
        ($.inArray("all",selected_categories) >= 0);

    if (show_all){
        $(".qa-valuerow").show();
        $(".qa-comment").hide();
        $(".qa-skip input").attr("checked",false);
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
            $(this).next().find("textarea").val("Category not performed");
            to_toggle.hide();
        }else{
            $(this).find(".qa-skip input").attr("checked",false);
            $(this).next().find("textarea").val("");
            to_toggle.show();
        }
    });
};

/***************************************************************/
//set link for cycle when user changes cycle day dropdown
function set_cycle_link(){
    var day = $("#cycle-day option:selected").val();
    $("#change-test-list").attr("href",window.location.pathname+"?day="+day);
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
$(document).ready(function(){

    initialize_qa();

    //hide all  comments initially
    $(".qa-comment").hide();

    //set tab index
    $(".qa-input").each(function(i,e){ $(e).attr("tabindex", i) });

    //show comment when clicked
    $(".qa-showcmt a").click(function(){
      $(this).parent().parent().next().toggle(600);
    });

    //anytime an input changes run validation
    $(".qa-input").change(function(){
        //only allow numerical characters on input

        this.value = this.value.replace(QAUtils.NUMERIC_WHITELIST_REGEX,'');
        check_test_status($(this));
        calculate_composites();
    });

    /*$(".qa-input").keyup(function(e){
        //whitelist characters

        check_test_status($(this));

    });
*/
    //run filter routine anytime user alters the categories
    $("#category_filter").change(filter_by_category);

    //update the link for user to change cycles
    $("#cycle-day").change(set_cycle_link);

    //prevent form submission when user hits enter key
    $(this).on("keypress","input, select", function(e) {

        //rather than submitting form on enter, move to next value
        if (e.keyCode == 13) {
            var inputs = $(this).parents("form").find(".qa-input");
            var idx = inputs.index(this);
            var next_row;
            if (idx == inputs.length - 1) {
                next_row = $(this).parents("form").find(".qa-valuerow").first();
            } else {
                next_row = $(this).parents("tr").nextAll(".qa-valuerow");
            }
            next_row.find(".qa-input").first().focus();
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

    //automaticall unhide comment if test is being skipped
    $(".qa-skip input").click(function(){
        if ($(this).is(':checked')){
            $(this).parent().parent().next().next().show(600);
        }
    });

    $("#work-completed").datepicker();

    //run a full validation on page load
    full_validation();

    var tabindex = 1;
    $('.qa-input').each(function() {
        if ($(this).type !== "hidden") {
            $(this).attr("tabindex", tabindex);
            tabindex++;
        }
    });
    $(".qa-input").first().focus();
});

