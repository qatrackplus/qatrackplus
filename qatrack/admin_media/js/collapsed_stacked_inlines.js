(function($){
    function add_click_handler(h3){
            h3.find('a.stacked_collapse-toggle').bind("click", function(){
                fs = $(this).parent('h3').next('fieldset');
                if (!fs.hasClass('collapsed'))
                {
                    fs.addClass('collapsed');
                    $(this).html('(' + gettext('Show') + ')');
                }
                else
                {
                    fs.removeClass('collapsed');
                    $(this).html('(' + gettext('Hide') + ')');
                }
            }).removeAttr('href').css('cursor', 'pointer');

    }

    $(document).ready(function() {
        // Only for stacked inlines
        $('div.inline-group div.inline-related:not(.tabular)').each(function() {
            fs = $(this).find('fieldset');
            h3 = $(this).find('h3:first');

            // Don't collapse if fieldset contains errors
            if (fs.find('div').hasClass('errors'))
                fs.addClass('stacked_collapse');
            else
                fs.addClass('stacked_collapse collapsed');

            // Add toggle link
            h3.prepend('<a class="stacked_collapse-toggle" href="#">(' + gettext('Show') + ')</a> ');
            add_click_handler(h3);
        });

        $(".add-row").find("a").click(function(){
            //bind toggle click handler when new row is added
            $('div.inline-group div.inline-related:not(.tabular, .empty-form):last').each(function() {
                fs = $(this).find('fieldset');
                h3 = $(this).find('h3:first');
                fs.addClass('stacked_collapse');
                add_click_handler(h3);
            });

        });
    });
})(django.jQuery);
