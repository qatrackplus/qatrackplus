require(['jquery', 'sl_utils', 'comments'], function($) {
    $(document).ready(function () {

        //(de)select checkboxes for child tests when user clicks on header checkbox
        $("input.test-selected-toggle").on("change", function (e) {
            $("input.test-selected-toggle").not($(this)).prop("checked", $(this).is(":checked"));
            $(this).closest("table").find("input.test-selected").prop("checked", $(this).is(":checked"));
        });

        $("#test-list-info-toggle").click(function () {
            $("#test-list-info").toggle(600);
        });
        $(".bulk-status").on('change', function () {
            var val = $(this).val();
            $(".bulk-status").not($(this)).val(val);
            if (val !== "") {
                $("input.test-selected:checked").parents("tr").find("select").val(val);
            }
            return false;
        });

        $('.qa-showcmt > a.revealcomment').click(function () {
            var this_row = $(this).parent().parent();
            var comment_row = this_row.next('.qa-comment');
            comment_row.toggle('fast');
            comment_row.find('.comment-bar').slideToggle('fast');
            comment_row.find('.comment-bar').toggleClass('in');
            this_row.find('.comment-bar').toggleClass('in');
            return false;
        });

        $('a.revealtext').click(function () {
            var this_row = $(this).parent().parent().parent();
            var comment_row = this_row.nextAll(".qa-text-display").eq(0);
            comment_row.toggleClass('hidden');
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
                    );
                },
                function () {
                    $(this).css('background-color', $(this).attr('data-bgcolour'));
                }
            );
        });
        var $form = $('#qa-review');
        $('#submit-review-ajax').one('click', function (e) {
            e.preventDefault();

            var data = $form.serialize();

            $.ajax({
                type: 'POST',
                url: QAURLs.TLI_REVIEW + rtsqa_form + '/' + tli_id + '/',
                data: data,
                success: function (res) {
                    QAURLs.returnYourChoice(res.rtsqa_form, res.tli_id);
                }
            });
            return false;
        });

    });
});
