
/***************************************************************/
//main function for handling test validation
function validate(initiator){
    console.log(initiator);
    console.log($("form input.qa-input"));
    var validation_data = {

    };
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

    //hide all procedures and comments initially
    $(".qa-procedure, .qa-comment").hide();

    //enable toggle behaviour for boolean tests
    $(".qa-boolean").button();

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
    $("form input").change(function(){validate($(this))});

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

