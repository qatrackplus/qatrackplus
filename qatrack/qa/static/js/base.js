/**************************************************************************/
//Initialize sortable/filterable test list table data types
function init_test_collection_tables(){
	var selector;
	if (arguments.length === 0){
		selector = ".test-collection-table";
	}else{
		selector = arguments[0];
	}
	$(selector).each(function(idx,table){

		if ($(this).find("tr.empty-table")){
			continue;
		}
		
		var cols ;

		if ($(table).hasClass("review-table")){
			cols = [
				null, //Unit
				null, //Freq
				null,  // Test list name
				{"sType":"day-month-year-sort"}, //date completed
				{"sType":"span-day-month-year-sort"}, //due date
				null, //status of test list tests
				null,  //review status of list
				null  //history
			];
			filter_cols =  [
				{type: "select"}, //Unit
				{type: "select"}, //Freq
				{type: "text" }, // Test list name
				{type: "text" }, //date completed
				{type: "text" }, //due date
				{ type: "text" }, //status of test list tests
				null, //review status of list
				null  //history
			];
		}else{
			cols = [
				null, //Unit
				null, //Freq
				null,  // Test list name
				{"sType":"day-month-year-sort"}, //date completed
				{"sType":"span-day-month-year-sort"}, //due date
				null, //qa status
				null,//assigned to
				null //perform link
			];
			filter_cols = [
				{type: "select"}, //Unit
				{type: "select"}, //Freq
				{type: "text" }, // Test list name
				{type: "text" }, //date completed
				{type: "text" }, //due date
				null, //qa status
				{type: "select"},//assigned to
				null //perform link
			];
		}

		$(table).dataTable( {
			"sDom": "t<'row-fluid'<'span3'><'span3' l><'span6'p>>",

			"bStateSave":false, //save filter/sort state between page loads
			"bFilter":true,
			"bPaginate": false,

			aoColumns: cols

		}).columnFilter({
			sPlaceHolder: "head:after",
			aoColumns: filter_cols
		});

		$(table).find("select, input").addClass("input-small");

	});

}

/**************************************************************************/
$(document).ready(function(){

	$.when(QAUtils.init()).done(function(){
		init_test_collection_tables();

		$(".test-collection-table tbody tr.has-due-date").each(function(idx,row){
			var date_string = $(this).data("last_done");
			var last_done = null;
			if (date_string){
				last_done = QAUtils.parse_iso8601_date(date_string);
			}
			var freq = $(this).data("frequency");
			//QAUtils.set_due_status_color($(this).find(".due-status"),last_done,freq);
		});
	});
});


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