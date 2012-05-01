var QAUtils = new function() {

    this.ACT_COLOR = "#da4f49";
    this.TOL_COLOR = "#c67605";
    this.OK_COLOR = "#5bb75b";

    this.ACT_LOW = "act_low";
    this.TOL_LOW = "tol_low";
    this.TOL_HIGH = "tol_high";
    this.ACT_HIGH = "act_high";

    this.WITHIN_TOL = "ok";
    this.TOLERANCE = "tolerance";
    this.ACTION = "action";

    this.PERCENT = "percent";
    this.ABSOLUTE = "absolute";

    //value equality tolerance
    this.EPSILON = 1E-10;

    this.API_VERSION = "v1";
    this.API_URL = "/qa/api/"+this.API_VERSION+"/";


    this.UNREVIEWED = "unreviewed";
    this.APPROVED = "approved";
    this.SCRATCH = "scratch";
    this.REJECTED = "rejected";


    /***************************************************************/
    /* Tolerance functions
    value is floating point number to be tested
    reference is a floating point number
    while tolerances must be an object with act_low, tol_low, tol_high,
    act_high and tol_type attributes.
    */
    this.percent_difference = function(measured, reference){
        //reference = 0. is a special case
        if (Math.abs(reference) < this.EPSILON){
            return absolute_difference(measured,reference);
        }
        return 100.*(measured-reference)/reference;
    };

    this.absolute_difference = function(measured,reference){
        return measured - reference;
    };

    this.test_tolerance = function(value, reference, tolerances, is_bool){
        //compare a value to a reference value and check whether it is
        //within tolerances or not.
        //Return an object with a 'diff' and 'result' value
        var diff;
        var status;
        var message;

        if (is_bool){
            return this.test_bool(value, reference)
        }

        if (!tolerances.type){
            return {
                status:this.WITHIN_TOL,
                gen_status:this.WITHIN_TOL,
                diff:"",
                message: "OK"
            };
        }

        if (tolerances.type == this.PERCENT){
            diff = this.percent_difference(value,reference);
            message = "(" + diff.toFixed(1)+")";

        }else{
            diff = this.absolute_difference(value,reference);
            message = "(" + diff.toFixed(2)+")";
        }

        if ((tolerances.tol_low <= diff) && (diff <= tolerances.tol_high)){
            status = this.WITHIN_TOL;
            gen_status = this.WITHIN_TOL;
            message = "OK" + message;
        }else if ((tolerances.act_low <= diff) && (diff <= tolerances.tol_low)){
            status = this.TOL_LOW;
            gen_status = this.TOLERANCE;
            message = "TOL" + message;
        }else if ((tolerances.tol_high <= diff) && (diff <= tolerances.act_high)){
            status = this.TOL_HIGH;
            message = "TOL" + message;
            gen_status = this.TOLERANCE;
        }else if (diff <= tolerances.act_low){
            status = this.ACT_LOW;
            message = "ACT" + message;
            gen_status = this.ACTION;
        }else{
            status = this.ACT_HIGH;
            message = "ACT" + message;
            gen_status = this.ACTION;
        }

        return {status:status, gen_status:gen_status, diff:diff, message:message};
    };

    this.test_bool = function(value,reference){
        var status, gen_status;
        var diff = value-reference;
        var message;

        if (Math.abs(diff)> this.EPSILON){
            if (reference > 0){
                status = this.ACT_LOW;
            }else{
                status = this.ACT_HIGH;
            }
            message = "FAIL";
            gen_status == this.ACTION;
        }else{
            message = "PASS";
            gen_status = this.WITHIN_TOL;
        }

        return {status:status, gen_status:gen_status, diff:diff, message:message}
    };

    //convert an percent difference to absolute based on reference
    this.convert_tol_to_abs = function(ref,tol){
        return {
            act_low : ref*(100.+tol.act_low)/100.,
            tol_low : ref*(100.+tol.tol_low)/100.,
            tol_high : ref*(100.+tol.tol_high)/100.,
            act_high : ref*(100.+tol.act_high)/100.
        };
    };

    /********************************************************************/
    //API calls

    this.call_api = function(url,method,data,callback){
        $.ajax({
            type:method,
            url:url,
            data:data,
            success: function(result){
                callback(result);
            },
            error: function(error){
                return false;
            }
        });
    };


    //get resources for a given resource name
    this.get_resources = function(resource_name,callback, data){

        //make sure limit option is set
        if (data == null){
            data = {limit:0};
        }else if (!data.hasOwnProperty("limit")){
            data["limit"] = 0;
        }

        //default to json format
        if (!data.hasOwnProperty("format")){
            data["format"] = "json";
        }

        this.call_api(this.API_URL+resource_name,"GET",data,callback );
    };

    //values for a group of task_list_items
    this.task_list_item_values = function(options,callback){
        if (!options.hasOwnProperty("limit")){
            options["limit"] = 0;
        }
        this.call_api(this.API_URL+"grouped_values","GET",options,callback );
    };

    //*************************************************************
    //General
    this.zip = function(a1,a2){
        var ii;
        var zipped = [];
        for (ii=0;ii<a1.length;ii++){
            zipped.push([a1[ii],a2[ii]]);
        }
        return zipped;
    };

    this.intersection = function(a1,a2){
        return $(a1).filter(function(idx,elem){console.log(elem);return $.inArray(elem,a2)>=0;})
    };

    //taken from http://n8v.enteuxis.org/2010/12/parsing-iso-8601-dates-in-javascript/
    this.parse_iso8601_date = function(s){

        // parenthese matches:
        // year month day    hours minutes seconds
        // dotmilliseconds
        // tzstring plusminus hours minutes
        var re = /(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?(Z|([+-])(\d\d):(\d\d))/;

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
        for (var i in a) {
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
        if (d[8] != "Z" && d[10]) {
            var offset = d[10] * 60 * 60 * 1000;
            if (d[11]) {
                offset += d[11] * 60 * 1000;
            }
            if (d[9] == "-") {
                ms -= offset;
            }
            else {
                ms += offset;
            }
        }

        return new Date(ms);
    };

    this.get_time = function(s){
        return QAUtils.parse_iso8601_date(s).getTime();
    };

}();