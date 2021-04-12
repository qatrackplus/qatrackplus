require(['jquery'], function ($) {
    $(document).ready(function () {
        $('.collapse').on('show.bs.collapse', function (e)
        {
            e.stopPropagation();
            $(this).prev().find('i').addClass('fa-caret-down').removeClass('fa-caret-right');
            var link = $(this).prev().find('a');
            link.attr('title', link.data('title-shown'));
        });

        $('.collapse').on('hide.bs.collapse', function (e)
        {
            e.stopPropagation();
            $(this).prev().find('i').addClass('fa-caret-right').removeClass('fa-caret-down');
            var link = $(this).prev().find('a');
            link.attr('title', link.data('title-hidden'));
            $(this).find('.collapse').collapse('hide');
        });
    });
});
