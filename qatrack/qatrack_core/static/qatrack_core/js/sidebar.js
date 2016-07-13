
$.fn.animateRotate = function(start, stop, duration, easing, complete) {
    return this.each(function() {
        var $elem = $(this);

        $({deg: start}).animate({deg: stop}, {
            duration: duration,
            easing: easing,
            step: function(now) {
                $elem.css({
                    transform: 'rotate(' + now + 'deg)'
                });
            },
            complete: complete || $.noop
        });
    });
};

(function(){

    var originalAddClassMethod = jQuery.fn.addClass;

    jQuery.fn.addClass = function(){
        // Execute the original method.
        var result = originalAddClassMethod.apply( this, arguments );

        // trigger a custom event
        if (jQuery(this).is('body')) {
            jQuery(this).trigger('cssClassChanged');
        }

        // return the original result
        return result;
    }
})();

(function(){

    var originalRemoveClassMethod = jQuery.fn.removeClass;

    jQuery.fn.removeClass = function(){
        // Execute the original method.
        var result = originalRemoveClassMethod.apply( this, arguments );

        // trigger a custom event
        if (jQuery(this).is('body')) {
            jQuery(this).trigger('cssClassChanged');
        }

        // return the original result
        return result;
    }
})();

$(document).ready(function() {

    $('.iCheck').iCheck({
        checkboxClass: 'icheckbox_polaris'
    });

    var icon = $('#toggle-icon');

    $('body.sidebar-mini').on('cssClassChanged', function () {
        var body_class = $(this).attr('class');
        if (body_class.indexOf('sidebar-collapse') > -1) {
            $(icon).animateRotate(0, 180, 'slow', 'swing');
        } else if ($(icon).css('transform') != 'none') {
            $(icon).animateRotate(180, 0, 'slow', 'swing');
        }
    });

    $('.toggle-element').each(function () {
        var self = this;
        var target = $(this).attr('data-toggle');
        console.log(target);
        $(self).click(function () {
            $(self).toggleClass('active');
            $('#box-' + target).slideToggle();
        });
    });

    $('.sidebar-menu > li a.has-icheck').click(function(e) {
        e.stopPropagation();
        $(this).find('ins').click();
    });


});