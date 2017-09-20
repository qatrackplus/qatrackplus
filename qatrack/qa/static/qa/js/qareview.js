require(['jquery', 'sl_utils'], function($) {
	$(document).ready(function () {

		//(de)select checkboxes for child tests when user clicks on header checkbox
		$("input.test-selected-toggle").on("change", function (e) {
			$(this).closest("table").find("input.test-selected").prop("checked", $(this).is(":checked"))
		});

		$("#test-list-info-toggle").click(function () {
			$("#test-list-info").toggle(600);
		});
		$("#bulk-status").on('change', function () {
			var val = $("#bulk-status").val();
			if (val !== "") {
				$("input.test-selected:checked").parents("tr").find("select").val(val);
			}
			return false;
		});

		$('.qa-showcmt > a.revealcomment').click(function () {
			var comment_row = $(this).parent().parent().next();
			comment_row.toggle('fast');
			comment_row.find('.comment-div').slideToggle('fast');
			return false;
		});

		var $service_events = $('.service-event-btn');
		$.each($service_events, function(i, v) {
			var $service_event = $(this);
            var colour = $service_event.attr('data-bgcolour');
            $service_event.css('background-color', colour);
            $service_event.css('border-color', colour);
            if ($service_event.length > 0) {
                if (isTooBright(rgbaStringToArray($service_event.css('background-color')))) {
                    $service_event.css('color', 'black').children().css('color', 'black');
                }
                else {
                    $service_event.css('color', 'white').children().css('color', 'white');
                }
            }

            $service_event.hover(
                function () {
                    $(this).css(
                        'background-color',
                        lightenDarkenColor(rgbaStringToArray($(this).css('background-color')), -15)
                    )
                },
                function () {
                    $(this).css('background-color', $(this).attr('data-bgcolour'))
                }
            );
        });

	});
});