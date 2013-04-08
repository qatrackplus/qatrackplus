/**************************************************************************/
$(document).ready(function(){

	//(de)select checkboxes for child tests when user clicks on header checkbox
	$("input.test-selected-toggle").live("change",function(e){
		$(this).closest("table").find("input.test-selected").attr("checked",$(this).is(":checked"))
	});

	$("#test-list-info-toggle").click(function(){
		$("#test-list-info").toggle(600);
	});
	$("#bulk-status").live('change',function(){
		var val = $("#bulk-status").val();
		if (val !== ""){
			$("input.test-selected:checked").parents("tr").find("select").val(val);
		}
		return false;
	});

});
