"use strict";

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
	  $(this).find("button[type=submit]").enable(false).addClass(".disabled").text("Submitting...");
      this.beenSubmitted = true;
	}
  });
};