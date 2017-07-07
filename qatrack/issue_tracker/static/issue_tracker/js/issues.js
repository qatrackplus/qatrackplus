require(['jquery', 'moment', 'autosize', 'select2', 'sl_utils'], function ($, moment, autosize) {

    $(document).ready(function () {

        var $priority = $('#id_issue_priority'),
            $tags = $('#id_issue_tags'),
            $pic_click = $('.pic_click'),
            $comments = $('#comments > dd > p');

        $comments.addClass('padding-left-10 white-space-pre');

        autosize($('textarea.autosize'));

        $tags.select2({
            minimumResultsForSearch: 10,
            width: '100%',
            templateResult: function(res) {
                if (res.id) {
                    return $('<div class="select2-result-repository clearfix" title="' + tags[res.id][1] + '"><span class="pull-left">' + res.text + '</span><span class="pull-right no-wrap">' + tags[res.id][1] + '</span></div>');
                } else {
                    return res.text;
                }
            }
        });

        $pic_click.click(function() {
            $('.pic_display').slideToggle('fast');
        });


        function generate_status_label(priority) {
            if (priority.id) {
                var colour = colours[priority.id];
                var $label = $('<span class="label" style="background-color: ' + colour + '">' + priority.text + '</span>');
                $label.css('background-color', colour);
                $label.css('border-color', colour);
                if (isTooBright(rgbaStringToArray(colour))) {
                    $label.css('color', 'black').children().css('color', 'black');
                }
                return $label;
            }
            return priority.text;
        }
        $priority.select2({
            templateResult: generate_status_label,
            templateSelection: generate_status_label,
            minimumResultsForSearch: 10,
            width: '100%'
        });

    });




});
