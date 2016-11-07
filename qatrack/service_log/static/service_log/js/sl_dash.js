require(['jquery', 'sl_utils'], function($) {

    $(document).ready(function() {

        $('.status_colour').each(function() {
            apply_data_colour($(this));
        });

        $('.timeline-toggle').click(function() {
            $(this).toggleClass('off');
            var t_class = $(this).attr('id').split('_toggle')[0];
            console.log(t_class);
            $('.' + t_class).slideToggle('fast');
        });

    })

});
