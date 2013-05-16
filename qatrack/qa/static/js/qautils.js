"use strict";

var QAUtils = new function() {

    this.ACT_LOW = "act_low";
    this.TOL_LOW = "tol_low";
    this.TOL_HIGH = "tol_high";
    this.ACT_HIGH = "act_high";

    this.TOL_TYPES = [this.ACT_LOW,this.TOL_LOW,this.ACT_HIGH,this.TOL_HIGH];

    this.WITHIN_TOL = "ok";
    this.TOLERANCE = "tolerance";
    this.ACTION = "action";
    this.NOT_DONE = "not_done";
    this.NO_TOL = "no_tol";

    this.WITHIN_TOL_DISP =  "OK";
    this.TOLERANCE_DISP = "TOL";
    this.ACTION_DISP = "ACT";
    this.FAIL_DISP = "FAIL";
    this.NOT_DONE_DISP = "Not Done";
    this.NO_TOL_DISP = "No Tol Set";

    this.PERCENT = "percent";
    this.ABSOLUTE = "absolute";

    this.NUMERICAL = "numerical";
    this.BOOLEAN = "boolean";
    this.MULTIPLE_CHOICE = "multchoice";

    this.NUMERIC_WHITELIST_REGEX = /[^0-9\.eE\-]/g;
    this.NUMERIC_REGEX = /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/;

    //value equality tolerance
    this.EPSILON = 1E-10;
    this.COMPARISON_SIGNIFICANT = 7;

    this.API_VERSION = "v1";
    this.API_URL = QAURLs.base+"/qa/api/"+this.API_VERSION+"/";
    this.COMPOSITE_URL = QAURLs.base+"/qa/composite/";
    this.UPLOAD_URL = QAURLs.base+"/qa/upload/";
    this.CHARTS_URL = QAURLs.base+"/qa/charts/";
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

        return Math.abs(sc_b - sc_a) <= Math.pow(10.,-(this.COMPARISON_SIGNIFICANT-1));

    };

    this.percent_difference = function(measured, reference){
        //reference = 0. is a special case
        if (reference === 0.){
            return this.absolute_difference(measured,reference);
        }
        return 100.*(measured-reference)/reference;
    };

    this.absolute_difference = function(measured,reference){
        return measured - reference;
    };

    this.test_tolerance = function(value, reference, tolerances, test_type, pass_fail_only){
        //compare a value to a reference value and check whether it is
        //within tolerances or not.
        //Return an object with a 'diff' and 'result' value
        var diff;
        var status, gen_status;
        var message;
        var result;

        if (test_type === this.BOOLEAN){
            result = this.test_bool(value, reference);
        }else if  (test_type === this.MULTIPLE_CHOICE){
            result = this.test_multi(value,tolerances)
        }else{

            if ( !_.isNumber(reference) || !tolerances.type){
                result = {
                    status:this.NO_TOL,
                    gen_status:this.NO_TOL,
                    diff:"",
                    message: this.NO_TOL_DISP
                };
            }else{

                if (tolerances.type === this.PERCENT){
                    diff = this.percent_difference(value,reference);
                    message = "(" + diff.toFixed(1)+"%)";

                }else{
                    diff = this.absolute_difference(value,reference);
                    message = "(" + diff.toFixed(2)+")";
                }

                var right_at_tolerance = this.almost_equal(tolerances.tol_low,diff) || this.almost_equal(tolerances.tol_high,diff);
                var right_at_low_action = this.almost_equal(tolerances.act_low,diff);
                var right_at_high_action = this.almost_equal(tolerances.act_high,diff);

                if ( right_at_tolerance || ((tolerances.tol_low <= diff) && (diff <= tolerances.tol_high))){
                    status = this.WITHIN_TOL;
                    gen_status = this.WITHIN_TOL;
                    message = this.WITHIN_TOL_DISP + message;
                }else if (right_at_low_action || ((tolerances.act_low <= diff) && (diff <= tolerances.tol_low))){
                    status = this.TOL_LOW;
                    gen_status = this.TOLERANCE;
                    message = this.TOLERANCE_DISP + message;
                }else if (right_at_high_action || ((tolerances.tol_high <= diff) && (diff <= tolerances.act_high))){
                    status = this.TOL_HIGH;
                    message = this.TOLERANCE_DISP + message;
                    gen_status = this.TOLERANCE;
                }else if (diff <= tolerances.act_low){
                    status = this.ACT_LOW;
                    message = this.ACTION_DISP + message;
                    gen_status = this.ACTION;
                }else{
                    status = this.ACT_HIGH;
                    message = this.ACTION_DISP + message;
                    gen_status = this.ACTION;
                }

                result = {status:status, gen_status:gen_status, diff:diff, message:message};
            }
        }
        if (pass_fail_only){
            if (result.gen_status === this.ACTION){
                result.message = this.FAIL_DISP;
            }else if (result.gen_status === this.TOLERANCE || result.gen_status === this.NO_TOL){
                result.message = this.WITHIN_TOL_DISP;
                result.gen_status = this.WITHIN_TOL;
            }else{
                result.message = this.WITHIN_TOL_DISP;
            }

        }
        return result;
    };

    this.test_bool = function(value,reference){
        if ( !_.isNumber(reference)){
            return {
                status:this.NO_TOL,
                gen_status:this.NO_TOL,
                diff:"",
                message: this.NO_TOL_DISP
            };
        }

        var status, gen_status;
        var diff = value-reference;
        var message;

        if (Math.abs(diff)> this.EPSILON){
            if (reference > 0){
                status = this.ACT_LOW;
            }else{
                status = this.ACT_HIGH;
            }
            message = this.ACTION_DISP;
            gen_status = this.ACTION;
        }else{
            message = this.WITHIN_TOL_DISP;
            gen_status = this.WITHIN_TOL;
        }

        return {status:status, gen_status:gen_status, diff:diff, message:message};
    };


    this.test_multi = function(value,tolerance){
        if ( tolerance.mc_pass_choices.length == 0){
            return {
                status:this.NO_TOL,
                gen_status:this.NO_TOL,
                diff:"",
                message: this.NO_TOL_DISP
            };
        }

        var status, gen_status,diff;

        var message;

        if (tolerance.mc_pass_choices.indexOf(value)>=0){
            gen_status = this.WITHIN_TOL;
            message = this.WITHIN_TOL_DISP;
        }else if (tolerance.mc_tol_choices.indexOf(value)>=0){
            gen_status = this.TOLERANCE;
            message = this.TOLERANCE_DISP;
        }else{
            gen_status = this.ACTION;
            message = this.ACTION_DISP;
        }

        return {status:status, gen_status:gen_status, diff:diff, message:message};
    };


    //convert a tolerance from relative to absolute values based on reference
    this.convert_tol_to_abs = function(ref_val,tol){
        if (tol.type === this.ABSOLUTE){
            return {
                act_low  : ref_val + tol.act_low,
                tol_low  : ref_val + tol.tol_low,
                tol_high : ref_val + tol.tol_high,
                act_high : ref_val +tol.act_high
            };
        }

        return {
            act_low : ref_val*(100.+tol.act_low)/100.,
            tol_low : ref_val*(100.+tol.tol_low)/100.,
            tol_high : ref_val*(100.+tol.tol_high)/100.,
            act_high : ref_val*(100.+tol.act_high)/100.
        };
    };

    //return a string representation of a reference and tolerance
    this.format_ref = function(reference,test){
        var t,v,s;

        if (reference !== null){
            v = reference.value;
            if (reference.type === this.BOOLEAN){
                d = Math.abs(instance.value -1.) < this.EPSILON ? "Yes" : "No";
            }else if (reference.type === this.MULTIPLE_CHOICE){
                s = test.choices.split(',')[reference.value];
            }else{
                s = this.format_float(v);
            }
        }else{
            s = "No Ref";
        }

        return s;

    };

    //return a string representation of a reference and tolerance
    this.format_ref_tol = function(reference, tolerance,test){
        var t,v,s;

        if ((tolerance !== null) && (reference !== null)){
            t = this.convert_tol_to_abs(reference.value,tolerance);
            v = reference.value;

            if (reference.type === this.BOOLEAN){
                s = Math.abs(instance.value -1.) < this.EPSILON ? "Yes" : "No";
            }else if (reference.type === this.MULTIPLE_CHOICE){
                s = test.choices.split(',')[instance.value];
            }else{
                var f = this.format_float;
                s = [f(t.act_low),f(t.tol_low), f(v), f(t.tol_high), f(t.act_high)].join(" &le; ");
            }
        }else if (reference !== null){
            s = this.format_ref(reference,test);
        }else{
            s = "No Ref";
        }

        return s;

    };

    this.format_float = function(val){
        if (Math.abs(val)<this.EPSILON){
            return "0";
        }else if ((Math.abs(val) < 0.01) || (Math.abs(val) >= 10000.)){
            return val.toExponential(4);
        }
        return parseFloat(val).toPrecision(6);
    }


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


    /********************************************************************/
    //AJAX calls

    this.call_api = function(url,method,data,success_callback,error_callback){
        return $.ajax({
            type:method,
            url:url,
            data:data,
            contentType:"application/json",
            dataType:"json",
            success: function(result,status,jqXHR){
                success_callback(result,status, jqXHR,this.url);
            },
            traditional:true,
            error: function(result,status,jqXHR){
                error_callback(result,status, jqXHR,this.url);
            }
        });
    };


    //*************************************************************
    //General


    /*************************************************************************/
    this.get_checked = function(container){
        var vals =  [];
        $(container+" input[type=checkbox]:checked").each(function(i,cb){
            vals.push(cb.value);
        });
        return vals;
    };

    this.set_checked_state = function(checkbox_selectors,state){
        var i;
        for (i=0; i < checkbox_selectors.length; i++){
            $(checkbox_selectors[i]).attr("checked",state);
        }
    };


    this.options_from_url_hash = function(hash){
        var options = [];
        if (hash.slice(0,1) === "#"){
            hash = hash.slice(1);
        }
        var that = this;
        $.each(hash.split(this.OPTION_SEP),function(i,elem){
            var k_v = elem.split(that.OPTION_DELIM);
            options.push([k_v[0],k_v[1]]);
        });
        return options;
    };


    this.unit_test_chart_url = function(unit,test){
        var unit_option = 'unit'+this.OPTION_DELIM+unit.number;
        var test_option = 'slug'+this.OPTION_DELIM+test.slug;
        return this.CHARTS_URL+'#'+[unit_option,test_option].join(this.OPTION_SEP);
    };
    this.unit_test_chart_link = function(unit,test,text,title){
        var url = this.unit_test_chart_url(unit,test);
        if (title === undefined){
            title = ["View Data for", unit.name, test.name, "data"].join(" ");
        }
        return '<a href="'+url+'" title="'+title+'">'+text+'</a>';
    };


    //*********************************************************************
    //Date/Time Functions

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

