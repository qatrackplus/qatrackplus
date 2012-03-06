/*
Allows drag and drop reordering of many to many fields in the admin
Starting point was http://djangosnippets.org/snippets/1053/
*/

$(document).ready(function() {
    $('div.inline-group').sortable({
        containment: 'parent',
        zindex: 10,
        items: 'tr[class*=dynamic-]',
        handle: 'td',
        update: function() {
            $(this).find('tr').each(function(i) {
                if ($(this).find("option:selected").val()){
                    $(this).find('input[id$=order]').val(i);
                }
            });
        }
    });
    $('div.inline-related td').css('cursor', 'move');

    /*hides the ordering header*/
    $('div.inline-related').find('th:contains("order")').hide();

    /*hides the ordering inputs*/
    $('div.inline-related').find('input[id$=order]').parent('td').hide();

    $('div.inline-related').sort();
});
