/*
Allows drag and drop reordering of many to many fields (related by intermediary models)
in the admin. Starting point was http://djangosnippets.org/snippets/1053/
*/

function set_order(grouping){

            $(grouping).find('tr').each(function(i) {
                if ($(grouping).find("option:selected").val()){
                    $(grouping).find('input[id$=order]').val(i);
                }
            });
}

$(document).ready(function() {

    /*set up dragabble membership list*/
    $('div.inline-group').sortable({
        containment: 'parent',
        zindex: 10,
        items: 'tr[class*=dynamic-]',
        handle: 'td',
        update: function() {set_order(this)}
    });

    /*change cursor to "move" when over table cells*/
    $('div.inline-related td').css('cursor', 'move');

    /*hides the ordering header*/
    $('div.inline-related').find('th:contains("order")').hide();

    /*hides the ordering inputs*/
    $('div.inline-related').find('input[id$=order]').parent('td').hide();

    /*need to reset the order on submit otherwise an inline that was created
    may not have it's order value set*/
    $('form').submit(function(){set_order($('div.inline-group'));});

    $('div.inline-related').sort();
});
