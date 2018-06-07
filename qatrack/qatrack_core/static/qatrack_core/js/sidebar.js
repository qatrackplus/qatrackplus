
require(['jquery', 'icheck'], function($) {
    $.fn.animateRotate = function (start, stop, duration, easing, complete) {
        return this.each(function () {
            var $elem = $(this);

            $({deg: start}).animate({deg: stop}, {
                duration: duration,
                easing: easing,
                step: function (now) {
                    $elem.css({
                        transform: 'rotate(' + now + 'deg)'
                    });
                },
                complete: complete || $.noop
            });
        });
    };

    (function () {

        var originalAddClassMethod = jQuery.fn.addClass;

        jQuery.fn.addClass = function () {
            // Execute the original method.
            var result = originalAddClassMethod.apply(this, arguments);

            // trigger a custom event
            if (jQuery(this).is('body')) {
                jQuery(this).trigger('cssClassChanged');
            }

            // return the original result
            return result;
        }
    })();

    (function () {

        var originalRemoveClassMethod = jQuery.fn.removeClass;

        jQuery.fn.removeClass = function () {
            // Execute the original method.
            var result = originalRemoveClassMethod.apply(this, arguments);

            // trigger a custom event
            if (jQuery(this).is('body')) {
                jQuery(this).trigger('cssClassChanged');
            }

            // return the original result
            return result;
        }
    })();

    // /* Prevent sidebar daterange picker from moving */
    // window.daterangepicker.prototype.move = function () {};

    $(document).ready(function () {

        $('.iCheck').iCheck({
            checkboxClass: 'icheckbox_minimal-blue',
            radioClass: 'iradio_minimal-blue'
        });

        $('#toggle-icon').click(function() {
            $(this).toggleClass('rotate');
        });


        $('.toggle-element').each(function () {
            var self = this;
            var target = $(this).attr('data-toggle');
            $(self).click(function () {
                $(self).toggleClass('active');
                $('#box-' + target).slideToggle('fast');
            });
        });

        $('.sidebar-menu > li a.has-icheck').click(function (e) {
            $(this).find('ins').click();
        });
        $('.sidebar-menu > li a.has-icheck').hover(function (e) {
            $(this).find('div').addClass('hover');
        }, function (e) {
            $(this).find('div').removeClass('hover');
        });


    });
});