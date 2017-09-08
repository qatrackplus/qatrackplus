
require(['jquery'], function ($) {
    /* add filter to IE*/
    if (!Array.prototype.filter)
    {
      Array.prototype.filter = function(fun /*, thisp*/)
      {
        var len = this.length;
        if (typeof fun != "function")
          throw new TypeError();

        var res = new Array();
        var thisp = arguments[1];
        for (var i = 0; i < len; i++)
        {
          if (i in this)
          {
            var val = this[i]; // in case fun mutates this
            if (fun.call(thisp, val, i, this))
              res.push(val);
          }
        }

        return res;
      };
    }

    if(!Array.prototype.indexOf) {
        Array.prototype.indexOf = function(needle) {
            for(var i = 0; i < this.length; i++) {
                if(this[i] === needle) {
                    return i;
                }
            }
            return -1;
        };
    }


    $.fn.preventDoubleSubmit = function() {
      jQuery(this).submit(function() {
        if (this.beenSubmitted)
          return false;
        else{
          $(this).find("button[type=submit]").prop('disabled', true).addClass(".disabled").text("Submitting...");
          this.beenSubmitted = true;
        }
      });
      return jQuery(this);
    };

    var KEYS = {
            ENTER: 13,
            SPACE: 32,
            UP: 38,
            DOWN: 40,
            ESC: 27,
            TAB: 9,
            a: 65,
            b: 66,
            c: 67,
            d: 68,
            e: 69,
            f: 70,
            g: 71,
            h: 72,
            i: 73,
            j: 74,
            k: 75,
            l: 76,
            m: 77,
            n: 78,
            o: 79,
            p: 80,
            q: 81,
            r: 82,
            s: 83,
            t: 84,
            u: 85,
            v: 86,
            w: 87,
            x: 88,
            y: 89,
            z: 90,
            '0': 48,
            '1': 49,
            '2': 50,
            '3': 51,
            '4': 52,
            '5': 53,
            '6': 54,
            '7': 55,
            '8': 56,
            '9': 57,
            DASH: 189
        };

    (function ($) {

        $.fn.extend({

            overrideSelect2Keys: function () {
                this.each(function () {
                    new $.overrideSelect2Keys($(this));
                });
                return this;
            }
        });

        $.overrideSelect2Keys = function (els) {
            var self = $(els).data('select2');
            delete self.listeners.keypress;
            self.on('keypress', function (evt) {
                var key = evt.which;

                if (self.isOpen()) {
                    if (key === KEYS.ENTER) {
                        self.trigger('results:select');

                        evt.preventDefault();
                    } else if ((key === KEYS.SPACE && evt.ctrlKey)) {
                        self.trigger('results:toggle');

                        evt.preventDefault();
                    } else if (key === KEYS.UP) {
                        self.trigger('results:previous');

                        evt.preventDefault();
                    } else if (key === KEYS.DOWN) {
                        self.trigger('results:next');

                        evt.preventDefault();
                    } else if (key === KEYS.ESC || key === KEYS.TAB) {
                        self.close();

                        evt.preventDefault();
                    }
                } else {
                    if (key === KEYS.ENTER || key === KEYS.SPACE ||
                        ((key === KEYS.DOWN || key === KEYS.UP) && evt.altKey)) {
                        self.open();

                        evt.preventDefault();
                    }
                    if (key === KEYS.DOWN) {
                        var val = self.$element.find('option:selected').nextAll(":enabled").first().val();
                        if (undefined !== val) {
                            self.$element.val(val);
                            self.$element.trigger('change');
                        }
                        evt.preventDefault();
                    }
                    if (key === KEYS.UP) {
                        var val = self.$element.find('option:selected').prevAll(":enabled").first().val();
                        if (undefined !== val) {
                            self.$element.val(val);
                            self.$element.trigger('change');
                        }
                        evt.preventDefault();
                    }
                    if (((65 <= key && key <= 90) || (48 <= key && key <= 57) || (key === KEYS.DASH))) {
                        if (!self.keys_pressed) {
                            self.keys_pressed = [key];
                            self.key_timer = setTimeout(function () {
                                self.keys_pressed = [];
                            }, 1000)
                        } else {
                            self.keys_pressed.push(key);
                            clearTimeout(self.key_timer);
                            self.key_timer = setTimeout(function () {
                                self.keys_pressed = [];
                            }, 1000)
                        }
                        var best_options = self.$element.find('option:enabled');
                        $.each(self.keys_pressed, function (i, v) {
                            $.each(best_options, function (ii, vv) {
                                if (KEYS[$(vv).text().charAt(i).toLowerCase()] !== v) {
                                    best_options = best_options.not(vv);
                                }
                            });
                        });
                        self.$element.val(best_options.first().val());
                        self.$element.trigger('change');
                        evt.preventDefault();
                    }
                }
            });
            self.on('select2:selecting', function (evt) {
                console.log(self);
            });
        };
    })(jQuery);
});
