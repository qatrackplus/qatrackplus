function toggle_image_class(img){
       var to_add, to_rem;

        if (img.hasClass("icon-minus-sign")){
            to_add = "icon-plus-sign";
        }else{
            to_add = "icon-minus-sign";
        }

        img.removeClass("icon-minus-sign icon-plus-sign").addClass(to_add);
}
/**************************************************************************/
$(document).ready(function(){
    $("span.toggle-unit").click(function(){
        $(this).parent().parent().next("div.unit-container").toggle();
        toggle_image_class($(this).find("i"))
    });

    $("#collapse-container").click(function(){
        var img = $(this).find("i");
        var txt = $("#collapse-string");
        var to_toggle;

        var containers = $("div.unit-container");

        if (img.hasClass("icon-minus-sign")){
            containers.hide();
            txt.text("Show All");
            to_toggle = ".icon-minus-sign";
        }else{
            containers.show();
            txt.text("Collapse All");
            to_toggle = ".icon-plus-sign";
        }

        toggle_image_class($(to_toggle));

    });
});

