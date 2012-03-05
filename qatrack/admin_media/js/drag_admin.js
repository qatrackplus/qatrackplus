$(document).ready(function() {
    $('div.inline-group').sortable({
        /*containment: 'parent',
        zindex: 10, */
        items: 'div.inline-related',
        handle: 'h3:first',
        update: function() {
            $(this).find('div.inline-related').each(function(i) {
                if ($(this).find('input[id$=name]').val()) {
                    $(this).find('input[id$=order]').val(i+1);
                }
            });
        }
    });
    $('div.inline-related h3').css('cursor', 'move');
    $('div.inline-related').find('input[id$=order]').parent('div').hide();
    $('form').submit(function(){
       $('div.inline-group').find('div.inline-related').each(function(i){
            if ($(this).find('input[id$=name]').val()) {
                    $(this).find('input[id$=order]').val(i+1);
            }
    /*
       .find('input[id$=order]').not("input[id$=__prefix__-order]").each(function(i){
            $(this).val(i+1);*/
        });
    });

});

/*function on_sort(event,ui){
    var orders =  $('input[name$="order"]');

    for (var i=0; i < orders.length; i++){
        orders.value = i;
    }
}
$(document).ready(function(){
    $( ".inline-group" ).sortable( {
     update: on_sort
    });
    $( ".inline-group" ).disableSelection();
    $('input[name$="order"]').attr({readonly:"readonly"});
});*/
