require(['jquery', 'moment', 'autosize'], function($, moment, autosize) {

    var $comment = $('#id_comment'),
        $comments = $('#comments'),
        $comment_form = $('#comment-form'),
        $post_comment = $('#post-comment');

    autosize($comment);

    $comment.keyup(function () {
        $post_comment.prop('disabled', $(this).val().trim() === '');
    });

    $post_comment.click(function () {
        var data = $comment_form.serialize();
        $.ajax({
            data: data,
            url: QAURLs.AJAX_COMMENT,
            type: 'POST',
            success: function (res) {
                $comment.val('');
                display_comment(res);
            },
            error: function (res) {
                console.log(res);
                console.log(res.responseJSON.message);
            }
        })
    });

    function display_comment(res) {
        var $dt = $('<dt id="' + res.c_id + '" style="display: none;">' + moment(res.submit_date).format('D MMM YYYY h:mm A') + ' - ' + res.user_name + '</dt>'),
            $dd = $('<dd style="display: none;"><p>' + res.comment + '</p></dd>');

        $comments.append($dt);
        $comments.append($dd);

        $dt.slideDown('fast', function () {
            $dd.slideDown('fast');
        })
    }

});