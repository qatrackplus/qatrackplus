/**************************************************************************/
$(document).ready(function(){

	//(de)select checkboxes for child tests when user clicks on header checkbox
	$("input.test-selected-toggle").on("change",function(e){
		$(this).closest("table").find("input.test-selected").prop("checked",$(this).is(":checked"))
	});

	$("#test-list-info-toggle").click(function(){
		$("#test-list-info").toggle(600);
	});
	$("#bulk-status").on('change',function(){
		var val = $("#bulk-status").val();
		if (val !== ""){
			$("input.test-selected:checked").parents("tr").find("select").val(val);
		}
		return false;
	});
	
	$('.qa-showcmt > a.revealcomment').click(function() {
		var comment_row = $(this).parent().parent().next();
		comment_row.toggle('fast');
        comment_row.find('.comment-div').slideToggle('fast');
        return false;
	});

});
