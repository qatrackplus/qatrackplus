
/***************************************************************/
//Set up the values we will need to do validation on data
var validation_data = {};
function initialize_qa(){

    $(".qa-valuerow").each(function(order){
        var context_name = $(this).find(".qa-contextname").val();
        var qa_row = $(this);
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


        validation_data[context_name] = {
            name:context_name,
            tolerances:tolerances,
            reference:reference,
            current_value: get_value_for_row($(this))
        };

    });
}

function get_value_for_row(input_row_element){
    if ($(input_row_element).find(".qa-tasktype").val() === "boolean"){
        if ($(input_row_element).find(":checked").length > 0){
            return parseFloat($(input_row_element).find(":checked").val());
        }else{
            return null;
        }
    }else {
        var val = parseFloat(input_row_element.find(".qa-value input").val());
        if (isNaN(val)){
            return null;
        }else{
            return val;
        }
    }

}
/***************************************************************/
//main function for handling test validation
function check_status(input_element){
    var parent = input_element.parents("tr:first");
    var name = parent.find(".qa-contextname").val();
    validation_data[name].current_value = get_value_for_row(input_element.parents(".qa-valuerow"));
    check_item_status(input_element);

}
//check a single qa items status
function check_item_status(input_element){


    var parent = input_element.parents("tr:first");
    var name = parent.find(".qa-contextname").val();
    var is_bool = parent.find(".qa-tasktype").val() === "boolean";
    var qastatus = parent.find(".qa-status");
    var val = get_value_for_row(input_element.parents(".qa-valuerow"));

    //remove any previous formatting
    qastatus.removeClass("btn-danger btn-warning btn-success");
    qastatus.text("Not Done");


    //ensure numerical value and highlight input element appropriately
    if (val === null){
        set_invalid_input(input_element);
        return;
    }
    set_valid_input(input_element);


    var tolerances = validation_data[name].tolerances;
    var reference = validation_data[name].reference;
    var result = QAUtils.test_tolerance(val,reference.value,tolerances, is_bool);

    qastatus.text(result.message);

    if (result.gen_status === QAUtils.WITHIN_TOL){
        qastatus.addClass("btn-success");
    }else if(result.gen_status === QAUtils.TOLERANCE){
        qastatus.addClass("btn-warning");
    }else{
        qastatus.addClass("btn-danger");
    }

}

function set_invalid_input(input_element){
    input_element.parents(".control-group").removeClass("success");
    input_element.parents(".control-group").addClass("error");
}
function set_valid_input(input_element){
    input_element.parents(".control-group").removeClass("error");
    input_element.parents(".control-group").addClass("success");
}

function valid_input(input_element){
    return (!isNaN(parseFloat(input_element.val())) && $.trim(input_element.val()) !== "") ;
}
/***************************************************************/
function filter_by_category(){

    var selected_categories = new Array();
    $("#category_filter option:selected").each(function(){
        selected_categories.push($(this).val());
    });

    var show_all = (selected_categories.length === 0) ||
        ($.inArray("all",selected_categories) >= 0);

    if (show_all){
        $(".qa-valuerow").show();
        $(".qa-comment .qa-procedure").hide();
        $(".qa-skip input").attr("checked",false)
        return;
    }

    //loop over each qa-value row and show or hide related rows
    $(".qa-valuerow").each(function(e){

        var category = $(this).find("td.qa-category").text().toLowerCase();

        var to_toggle = $(this);
        to_toggle.add($(this).nextUntil(".qa-valuerow"));
        to_toggle.add($(this).prevUntil(".qa-valuerow"));

        if ($.inArray(category,selected_categories) < 0){
            $(this).find
            to_toggle.hide();
        }else{
            $(this).find(".qa-skip input").attr("checked",false)
            to_toggle.show();
        }
    });
};

/****************************************************************/
$(document).ready(function(){

    initialize_qa();

    //hide all procedures and comments initially
    $(".qa-procedure, .qa-comment").hide();

    //set tab index
    $("input:text, input:radio").each(function(i,e){ $(e).attr("tabindex", i) });

    //show procedures when clicked
    $(".qa-showproc a").click(function(){
        $(this).parent().parent().next().slideToggle(1200);
    });

    //show comment when clicked
    $(".qa-showcmt a").click(function(){
      $(this).parent().parent().next().next().slideToggle(1200);
    });

    //anytime an input changes run validation
    $("form input").change(function(){check_status($(this))});

    $("#category_filter").change(filter_by_category);

    //prevent form submission when user hits enter key
    $(this).on("keypress","input", function(e) {

        //rather than submitting form on enter, move to next value
        if (e.keyCode == 13) {
            var inputs = $(this).parents("form").find("input:text, input:radio");
            var idx = inputs.index(this);

            if (idx == inputs.length - 1) {
                inputs[0].select()
            } else {
                inputs[idx + 1].focus(); //  handles submit buttons
                inputs[idx + 1].select();
            }
            return false;
        }
    });

});

