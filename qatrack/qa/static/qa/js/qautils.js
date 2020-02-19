/*jslint browser: true */
/*global window,$ */

var QAUtils = new function() {

    "use strict";

    this.ACT_LOW = "act_low";
    this.TOL_LOW = "tol_low";
    this.TOL_HIGH = "tol_high";
    this.ACT_HIGH = "act_high";

    this.TOL_TYPES = [this.ACT_LOW,this.TOL_LOW,this.ACT_HIGH,this.TOL_HIGH];

    this.WITHIN_TOL = "ok";
    this.TOLERANCE = "tolerance";
    this.ACTION = "action";
    this.NOT_DONE = "not_done";
    this.DONE = "done";
    this.NO_TOL = "no_tol";

    var sh = window.TEST_STATUS_SHORT;
    // this.WITHIN_TOL_DISP =  sh.ok;
    var icons = window.ICON_SETTINGS.SHOW_STATUS_ICONS_PERFORM;

    this.TOLERANCE_DISP = icons ? '<i class="pull-left fa fa-exclamation-circle"></i> ' + sh.tolerance : sh.tolerance;
    this.ACTION_DISP = icons ? '<i class="pull-left fa fa-ban"></i> ' + sh.action : sh.action;
    this.FAIL_DISP = icons ? '<i class="pull-left fa fa-ban"></i> ' + sh.fail : sh.fail;
    this.NOT_DONE_DISP = sh.not_done;
    this.WITHIN_TOL_DISP = icons ? '<i class="pull-left fa fa-check-circle-o"></i> ' + sh.ok : sh.ok;
    this.DONE_DISP = sh.done;
    this.NO_TOL_DISP = icons ? '<i class="pull-left fa fa-circle-o"></i> ' + sh.no_tol : sh.no_tol;

    this.PERCENT = "percent";
    this.ABSOLUTE = "absolute";

    this.NUMERICAL = "numerical";
    this.SIMPLE = "simple";
    this.WRAPAROUND = "wraparound";
    this.CONSTANT = "constant";
    this.BOOLEAN = "boolean";
    this.MULTIPLE_CHOICE = "multchoice";
    this.COMPOSITE = "composite";
    this.DATE = "date";
    this.DATETIME = "datetime";
    this.STRING_COMPOSITE = "scomposite";
    this.UPLOAD = "upload";
    this.STRING = "string";
    this.NUMBER_TEST_TYPES = [this.SIMPLE, this.WRAPAROUND, this.CONSTANT, this.COMPOSITE];
    this.READ_ONLY_TEST_TYPES = [this.COMPOSITE, this.STRING_COMPOSITE, this.CONSTANT];
    this.COMPOSITE_TEST_TYPES = [this.COMPOSITE, this.STRING_COMPOSITE];

    this.NUMERIC_WHITELIST_REGEX = /[^0-9\.eE\-]/g;
    this.NUMERIC_REGEX = /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/;

    //value equality tolerance
    this.EPSILON = 1E-10;
    this.COMPARISON_SIGNIFICANT = 7;

    this.COMPOSITE_URL = window.QAURLs.base+"/qa/composite/";
    this.INFO_URL = window.QAURLs.base+"/qa/utc/perform/info/";
    this.UPLOAD_URL = window.QAURLs.base+"/qa/upload/";
    this.CHARTS_URL = window.QAURLs.base+"/qa/charts/";
    this.OPTION_DELIM = "=";
    this.OPTION_SEP = "&";


    this.DUE = this.TOLERANCE;
    this.OVERDUE = this.ACTION;
    this.NOT_DUE = this.WITHIN_TOL;

    this.MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

    //initialized from api
    this.FREQUENCIES = {};
    this.STATUSES = {};


    this.KC_ENTER = 13;
    this.KC_LEFT = 37;
    this.KC_UP = 38;
    this.KC_RIGHT = 39;
    this.KC_DOWN = 40;

    /***************************************************************/
    /* Tolerance functions
    value is floating point number to be tested
    reference is a floating point number
    while tolerances must be an object with act_low, tol_low, tol_high,
    act_high and tol_type attributes.
    */

    this.log10 = function(x){
        return Math.log(x)/Math.LN10;
    };

    this.almost_equal = function(a, b){
        if (a == b){
            return true;
        }

        var scale;
        var sc_a,sc_b;

        try {
            scale = Math.pow(10,Math.floor(this.log10(scale)));
            scale = 0.5*(Math.abs(b) + Math.abs(a));
        }catch(err){

        }


        try {
            sc_b = b/scale;
        } catch(err) {
            sc_b = 0.0;
        }

        try {
            sc_a = a/scale;
        } catch(err) {
            sc_a = 0.0;
        }

        return Math.abs(sc_b - sc_a) <= Math.pow(10.0,-(this.COMPARISON_SIGNIFICANT-1));

    };



    this.format_float = function(val){
        if (Math.abs(val)<this.EPSILON){
            return "0";
        }else if ((Math.abs(val) < 0.01) || (Math.abs(val) >= 10000.0)){
            return val.toExponential(4);
        }
        return parseFloat(val).toPrecision(6);
    };


    this.clean_numerical_value = function(value){

        if (value.length === 0){
            return "";
        }

        //only allow numerical characters on input
        value = value.replace(this.NUMERIC_WHITELIST_REGEX,'');

        if ((value === ".") || (value === "-") || (value==="e") || (value==="E")){
            return "";
        }

        if (value[0] === ".") {
            value = "0" + value;
        }

        if ( (value[0] === "-") && (value[1]===".")){
            return "-0."+value.substr(2,value.length-1);
        }

        return value;

    };

    //*************************************************************
    //General


    /*************************************************************************/
    this.get_checked = function(container){
        var vals =  [];
        $(container + " input[type=checkbox]:checked").each(function(i,cb){
            vals.push(cb.value);
        });
        return vals;
    };

    this.set_checked_state = function(checkbox_selectors,state){
        var i;
        for (i=0; i < checkbox_selectors.length; i++){
            $(checkbox_selectors[i]).prop("checked",state);
        }
    };


    //*********************************************************************
    //Date/Time Functions

   //parse a date in dd-mm-yyy hh:mm format (24 hour clock)
    this.parse_date= function(s){
        try {
            var dt = s.split(" ");
            var date = dt[0].split('-');
            var time = dt[1].split(':');
            var dd = parseInt(date[0]);
            var mm = parseInt(date[1])-1;
            var yy = parseInt(date[2]);
            var hh = parseInt(time[0]);
            var nn = parseInt(time[1]);
            return new Date(yy, mm, dd, hh, nn);
        }catch(err){
            return null;
        }

    };

   //parse a date in dd-mmm-yyyy hh:mm format (24 hour clock) e..g 01 Oct 2019
    this.parse_dd_mmm_yyyy_date= function(s){
        var months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

        try {
            var dt = s.split(" ");

            var dd = parseInt(dt[0]);
            var mm = months.indexOf(dt[1].toLowerCase());
            var yy = parseInt(dt[2]);

            var time = dt[3].split(':');
            var hh = parseInt(time[0]);
            var nn = parseInt(time[1]);
            return new Date(yy, mm, dd, hh, nn);
        }catch(err){
            return null;
        }

    };

    //taken from http://n8v.enteuxis.org/2010/12/parsing-iso-8601-dates-in-javascript/
    this.parse_iso8601_date = function(s){

        // parenthese matches:
        // year month day    hours minutes seconds
        // dotmilliseconds
        // tzstring plusminus hours minutes
        var re = /(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?(Z|([+-])(\d\d):(\d\d))?/;

        var d = [];
        d = s.match(re);

        // "2010-12-07T11:00:00.000-09:00" parses to:
        //  ["2010-12-07T11:00:00.000-09:00", "2010", "12", "07", "11",
        //     "00", "00", ".000", "-09:00", "-", "09", "00"]
        // "2010-12-07T11:00:00.000Z" parses to:
        //  ["2010-12-07T11:00:00.000Z",      "2010", "12", "07", "11",
        //     "00", "00", ".000", "Z", undefined, undefined, undefined]

        if (! d) {
            throw "Couldn't parse ISO 8601 date string '" + s + "'";
        }

        // parse strings, leading zeros into proper ints
        var a = [1,2,3,4,5,6,10,11];
        var i;
        for (i in a) {
            d[a[i]] = parseInt(d[a[i]], 10);
        }
        d[7] = parseFloat(d[7]);

        // Date.UTC(year, month[, date[, hrs[, min[, sec[, ms]]]]])
        // note that month is 0-11, not 1-12
        // see https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Date/UTC
        var ms = Date.UTC(d[1], d[2] - 1, d[3], d[4], d[5], d[6]);

        // if there are milliseconds, add them
        if (d[7] > 0) {
            ms += Math.round(d[7] * 1000);
        }

        // if there's a timezone, calculate it
        if (d[8] !== "Z" && d[10]) {
            var offset = d[10] * 60 * 60 * 1000;
            if (d[11]) {
                offset += d[11] * 60 * 1000;
            }
            if (d[9] === "-") {
                ms -= offset;
            }
            else {
                ms += offset;
            }
        }

        return new Date(ms);
    };


}();

