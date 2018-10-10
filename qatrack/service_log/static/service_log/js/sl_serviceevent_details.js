require(['jquery', 'autosize', 'sl_utils', 'comments'], function ($, autosize) {
    
    $(document).ready(function() {

        $('.se_tag').each(function() {
            var $service_event = $(this);
            var colour = $service_event.attr('data-bgcolour');
            $service_event.css('background-color', colour);
            $service_event.css('border-color', colour);
            if (isTooBright(rgbaStringToArray($service_event.css('background-color')))) {
                $service_event.css('color', 'black').children().css('color', 'black');
            }
            else {
                $service_event.css('color', 'white').children().css('color', 'white');
            }

            $service_event.hover(
                function () {
                    $(this).css(
                        'background-color',
                        lightenDarkenColor(rgbaStringToArray($(this).css('background-color')), -15)
                    )
                },
                function () {
                    $(this).css('background-color', $(this).attr('data-bgcolour'))
                }
            );

        });
        
        autosize($('textarea.autosize'));
    });
    
});