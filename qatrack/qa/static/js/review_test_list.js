/**************************************************************************/
$(document).ready(function(){

	//(de)select checkboxes for child tests when user clicks on header checkbox
	$("input.test-selected-toggle").live("change",function(e){
		$(this).closest("table").find("input.test-selected").attr("checked",$(this).is(":checked"))
	});


	$("#apply-status").live("click",function(){
		var val = $("#bulk-status").val();
		if (val !== ""){
			$("td.review-status select").val(val);
		}
		return false;
	});

});
