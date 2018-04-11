/*!
 * Cheeky Check v 0.0.1
 *
 * Author: Ryan Bottema
 */

(function (factory) {
    "use strict";
    if (typeof exports === 'object') {
        module.exports = factory(window.jQuery);
    } else if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (window.jQuery && !window.jQuery.fn.cheekycheck) {
        factory(window.jQuery);
    }
}(function ($) {
    'use strict';

    /*
     * Default plugin options
     */
    var defaults = {
        right: false,
        label_text: '',
        check: 'C',
        extra_class: ''
    };

    var Cheeky = function (element, options) {
        var self = this;
        self.element = $(element).addClass('cheeky-element');
        self.options = $.extend(true, {}, defaults, self.element.data(), options);
        self.checked = self.element.is(':checked');

        self.orig_label = $('label[for=' + self.element.attr('id') + ']').addClass('cheeky-orig-label');
        self.label_text = self.options.label || self.orig_label.text() || '';

        // Setup picker
        if (self.options.right) {
            self.cheeky = $(
                '<div class="cheeky' + (self.checked ? ' checked' : '') + '">' +
                '    <div class="cheeky-label">' + self.label_text + '</div>' +
                '    <div class="cheeky-checkbox">' +
                '        ' + self.options.check +
                '    </div>' +
                '</div>'
            );
        } else {
            self.cheeky = $(
                '<div class="cheeky ' + (self.checked ? ' checked' : '') + '">' +
                '    <div class="cheeky-checkbox">' +
                '        ' + self.options.check +
                '    </div>' +
                '    <div class="cheeky-label">' + self.label_text + '</div>' +
                '</div>'
            );
        }
        self.cheeky.addClass(self.options.extra_class);
        self.cheeky.insertBefore(self.element);

        self.cheeky.click(function() {
            self.checked = !self.checked;
            self.cheeky.toggleClass('checked');
            self.element.prop('checked', self.checked);
            self.element.change();
        });

    };

    Cheeky.prototype = {
        constructor: Cheeky,
        destroy: function () {
            var self = this;
            self.cheeky.remove();
            this.element.removeClass('cheeky-element');
        },
        getValue: function (defaultValue) {
            var self = this;
            return self.element.is(':checked');
        },
        isDisabled: function () {
            var self = this;
            return self.element.is(':disabled')
        },
        disable: function () {
            var self = this;
            self.element.prop('disabled', true);
            self.cheeky.addClass('cheeky-disabled');
        },
        enable: function () {
            var self = this;
            self.element.prop('disabled', false);
            self.cheeky.removeClass('cheeky-disabled');
        },
        change: function (e) {
            var self = this;
            self.element.change();
        }
    };

    $.cheekycheck = Cheeky;

    $.fn.cheekycheck = function (option) {
        var apiArgs = Array.prototype.slice.call(arguments, 1),
            isSingleElement = (this.length === 1),
            returnValue = null;

        var $jq = this.each(function () {
            var $this = $(this),
                inst = $this.data('cheekycheck'),
                options = ((typeof option === 'object') ? option : {});

            if (!inst) {
                inst = new Cheeky(this, options);
                $this.data('cheekycheck', inst);
            }

            if (typeof option === 'string') {
                if ($.isFunction(inst[option])) {
                    returnValue = inst[option].apply(inst, apiArgs);
                } else { // its a property ?
                    if (apiArgs.length) {
                        // set property
                        inst[option] = apiArgs[0];
                    }
                    returnValue = inst[option];
                }
            } else {
                returnValue = $this;
            }
        });
        return isSingleElement ? returnValue : $jq;
    };

    $.fn.cheekycheck.constructor = Cheeky;

}));
