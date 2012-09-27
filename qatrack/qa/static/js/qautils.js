"use strict";

var QAUtils = new function() {

    this.ACT_COLOR = "#b94a48";
    this.TOL_COLOR = "#f89406";
    this.OK_COLOR = "#468847";
	this.NOT_DONE_COLOR = "#3a87ad";
	this.REVIEW_COLOR = "#D9EDF7";

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

    this.API_VERSION = "v1";
    this.API_URL = "/qa/api/"+this.API_VERSION+"/";
	this.COMPOSITE_URL = "/qa/composite/";
	this.CHARTS_URL = "/qa/charts/";
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
    this.percent_difference = function(measured, reference){
        //reference = 0. is a special case
        if (Math.abs(reference) < this.EPSILON){
            return this.absolute_difference(measured,reference);
        }
        return 100.*(measured-reference)/reference;
    };

    this.absolute_difference = function(measured,reference){
        return measured - reference;
    };

    this.test_tolerance = function(value, reference, tolerances, test_type){
        //compare a value to a reference value and check whether it is
        //within tolerances or not.
        //Return an object with a 'diff' and 'result' value
        var diff;
        var status, gen_status;
        var message;


        if (test_type === this.BOOLEAN){
            return this.test_bool(value, reference);
        }else if  (test_type === this.MULTIPLE_CHOICE){
			return this.test_multi(value,tolerances)
		}

		if ( !this.is_number(reference) || !tolerances.type){
            return {
                status:this.NO_TOL,
                gen_status:this.NO_TOL,
                diff:"",
                message: this.NO_TOL_DISP
            };
		}

        if (tolerances.type === this.PERCENT){
            diff = this.percent_difference(value,reference);
            message = "(" + diff.toFixed(1)+"%)";

        }else{
            diff = this.absolute_difference(value,reference);
            message = "(" + diff.toFixed(2)+")";
        }

        if ((tolerances.tol_low <= diff) && (diff <= tolerances.tol_high)){
            status = this.WITHIN_TOL;
            gen_status = this.WITHIN_TOL;
            message = this.WITHIN_TOL_DISP + message;
        }else if ((tolerances.act_low <= diff) && (diff <= tolerances.tol_low)){
            status = this.TOL_LOW;
            gen_status = this.TOLERANCE;
            message = this.TOLERANCE_DISP + message;
        }else if ((tolerances.tol_high <= diff) && (diff <= tolerances.act_high)){
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

        return {status:status, gen_status:gen_status, diff:diff, message:message};
    };

    this.test_bool = function(value,reference){
		if ( !this.is_number(reference)){
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
            message = "FAIL";
            gen_status = this.ACTION;
        }else{
            message = "PASS";
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
			message = "PASS";
		}else if (tolerance.mc_tol_choices.indexOf(value)>=0){
			gen_status = this.TOLERANCE;
			message = "TOL";
		}else{
			gen_status = this.ACTION;
			message = "FAIL";
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
		return parseFloat(val).toPrecision(6);
	}

	//return a string representation of an instance value
	this.format_instance_value= function(instance){
		var s;
		if (instance.skipped){
			s = "<em>Skipped</em>";
		}else if (instance.test.type === this.BOOLEAN){
			s = Math.abs(instance.value -1.) < this.EPSILON ? "Yes" : "No";
		}else if (instance.test.type === this.MULTIPLE_CHOICE){
			s = instance.test.choices.split(',')[instance.value];
		}else{
			s = this.format_float(instance.value);
		}
		return s;
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

    //return an appropriate display for a given pass_fail status
    this.qa_displays = {};
    this.qa_displays[this.ACTION] = this.ACTION_DISP;
    this.qa_displays[this.TOLERANCE] = this.TOLERANCE_DISP;
    this.qa_displays[this.WITHIN_TOL] = this.WITHIN_TOL_DISP;
	this.qa_displays[this.NOT_DONE] = this.NOT_DONE_DISP;
	this.qa_displays[this.NO_TOL] = this.NO_TOL_DISP;
    this.qa_display = function(pass_fail){
        return this.qa_displays[pass_fail.toLowerCase()] || "";
    };

    //return an appropriate colour for a given pass_fail status
    this.qa_colors = {};
    this.qa_colors[this.ACTION] = this.ACT_COLOR;
    this.qa_colors[this.TOLERANCE] = this.TOL_COLOR;
    this.qa_colors[this.WITHIN_TOL] = this.OK_COLOR;
	this.qa_colors[this.NOT_DONE] = this.NOT_DONE_COLOR;
	this.qa_colors[this.NO_TOL] = this.NOT_DONE_COLOR;
	this.qa_colors[""] = this.NOT_DONE_COLOR;
    this.qa_color = function(pass_fail){
        return this.qa_colors[pass_fail.toLowerCase()] || "";

    };
    /********************************************************************/
    //AJAX calls

    /********************************************************************/
    //API calls
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

    //update all instances in instance_uris with a given status
    this.set_test_instances_status = function(instance_uris,status,callback){
        var objects = $.map(instance_uris,function(uri){
            return {resource_uri:uri,status:status};
        });

        return this.call_api(
            this.API_URL+"values/",
            "PATCH",
            JSON.stringify({objects:objects}),
            callback
        );
    };

    //get resources for a given resource name
    this.get_resources = function(resource_name,callback, data){

        //make sure limit option is set
        if (data === null || data === undefined){
            data = {limit:0};
        }else if (!data.hasOwnProperty("limit")){
            data["limit"] = 0;
        }

        //default to json format
        if (!data.hasOwnProperty("format")){
            data["format"] = "json";
        }

	    return this.call_api(this.API_URL+resource_name,"GET",data,callback );
    };

    //values for a group of tests
    this.test_values = function(options,callback){
        if (!options.hasOwnProperty("limit")){
            options["limit"] = 0;
        }
        return this.call_api(this.API_URL+"grouped_values","GET",options,callback );
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

	this.get_selected_option_vals = function(select_id){
		var selected = [];

		$(select_id).find(":selected").each(function(){
			selected.push(parseInt($(this).val()));
		});
		return selected;
	};

    this.zip = function(a1,a2){
        var ii;
        var zipped = [];
        for (ii=0;ii<a1.length;ii++){
            zipped.push([a1[ii],a2[ii]]);
        }
        return zipped;
    };

	this.non_empty = function(arr){
		return	arr.filter(function(elem,idx){return elem !== "";});
	};
    this.intersection = function(a1,a2){
        return $(a1).filter(function(idx,elem){return $.inArray(elem,a2)>=0;});
    };

	this.is_number = function(n){
		return !isNaN(parseFloat(n)) && isFinite(n);
	};

	this.options_from_url_hash = function(hash){
		var options = [];
		if (hash[0] === "#"){
			hash = hash.substring(1,hash.length);
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

	this.instance_has_ref_tol = function(instance){
		return (instance.reference !== null) && (instance.tolerance !== null);
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

    this.format_date = function(d,with_time){
        var date = [d.getDate(), this.MONTHS[d.getMonth()], d.getFullYear()];
        if (with_time){
            date.push(d.getHours()+':'+d.getMinutes());
        }
        return date.join(" ");
    };
	this.milliseconds_to_days = function(ms){
		return ms/(1000*60*60*24);
	};
	this.compare_due_date_delta = function(delta,due,overdue){
		if (delta < due){
			return this.NOT_DUE;
		}else if ((delta == due) || (delta < overdue )){
			return this.DUE;
		}
		return this.OVERDUE;
	};
	this.due_status = function(last_done,test_frequency){
		last_done.setHours(0,0,0,0)

		var today = new Date().setHours(0,0,0,0);
		var delta_time = last_done - today; //in ms
		if (delta_time > 0){
			return this.NOT_DUE;
		}
		var delta_days = Math.floor(Math.abs(this.milliseconds_to_days(delta_time)));
		var due,overdue;

		var frequency = this.FREQUENCIES[test_frequency];

		return this.compare_due_date_delta(delta_days,frequency.due_interval,frequency.overdue_interval);
	};

	this.set_due_status_color = function(elem,last_done,frequency){
		var status;

		if (last_done === null){
			status = this.OK;
		}else{
			status = this.due_status(last_done,frequency);
		}

		$(elem).removeClass([this.ACTION, this.TOLERANCE, this.OK].join(" "));
		$(elem).addClass(status);
	};

	this.make_select = function(id,cls,options){
		var l = [];
		var idx;

		l.push('<select id="'+id+'" class="'+cls+'">');
		for (idx = 0; idx < options.length; idx +=1){
			l.push('<option value="'+options[idx][0]+'">'+options[idx][1]+'</option>');
		}
		l.push("</select>");

		return l.join("");
	};


	this.default_exported_statuses = function(){
		var exported = [];
		var status;
		for (status in this.STATUSES){
			if (this.STATUSES[status].export_by_default){
				exported.push(status)
			}
		}
		return exported;
	};

	//call using $.when() before using QAUTils in any scripts
	//e.g. in a script where you want to use QAUTils you would do
	// $.when(QAUTils.init()).done(function(){
	//	   do_things_requiring_QAUtils();
	//})
	this.init = function(){
		var that = this;

		this.get_resources("status",function(results){
			$.each(results.objects,function(idx,status){
				that.STATUSES[status.slug] = status;
			});
		});

		return this.get_resources("frequency",function(results){
			$.each(results.objects,function(idx,freq){
				that.FREQUENCIES[freq.slug] = freq;
			});
		});

	};
}();

