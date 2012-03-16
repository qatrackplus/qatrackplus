/*Allows drag and drop reordering of many to many fields (related by intermediary models)
in the admin. Starting point was http://djangosnippets.org/snippets/1053/
*/

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
        });
    });

});

