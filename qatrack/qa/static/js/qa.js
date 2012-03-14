function validate(initiator){
    console.log(initiator);
    console.log($("form input.qainput"));
    var validation_data = {
        
    };
}

$(document).ready(function(){

    //hide all procedures and comments initially
    $(".qaprocedure, .qacomment").hide();

    //enable toggle behaviour for boolean tests 
    $(".qaboolean").button();

    //set tab index
    $("input:text, input:radio").each(function(i,e){ $(e).attr("tabindex", i) });

    //show procedures when clicked
    $(".qashowproc a").click(function(){
        $(this).parent().parent().next().slideToggle(1200);
    });
  
    //show comment when clicked
    $(".qashowcmt a").click(function(){
      $(this).parent().parent().next().next().slideToggle(1200);
    });
    
    //anytime an input changes run validation    
    $("form input").change(function(){validate($(this))});

});

//prevent form submission when user 
$(document).on("keypress","input", function(e) {

    //rather than submitting form on enter, move to next value
    if (e.keyCode == 13) {
        /* FOCUS ELEMENT */
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
