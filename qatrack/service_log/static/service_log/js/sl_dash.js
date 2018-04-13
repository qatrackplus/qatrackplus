require(['jquery', 'cheekycheck'], function($) {

    $(document).ready(function() {

        var $se_toggle = $('#se_toggle'),
            $rts_toggle = $('#rts_toggle');

        $se_toggle.cheekycheck({
            right: true,
            check: '<i class="fa fa-check"></i>',
            extra_class: 'info'
        });

        $rts_toggle.cheekycheck({
            right: true,
            check: '<i class="fa fa-check"></i>',
            extra_class: 'info'
        });

        $rts_toggle.change(function() {
            $('.rtsqa_log').slideToggle('fast');
        });
        $se_toggle.change(function() {
            $('.se_log').slideToggle('fast');
        });

    })

});
