require(['jquery', 'moment', 'autosize'], function($, moment, autosize) {

    var $comment = $('#id_comment'),
        $comments = $('#comments'),
        $comment_form = $('#comment-form'),
        $post_comment = $('#post-comment');

    autosize($comment);

    $comment.keyup(function () {
        if ($(this).val().trim() === '') {
            $post_comment.prop('disabled', true).addClass('disabled');
        } else {
            $post_comment.prop('disabled', false).removeClass('disabled');
        }
    });

    $post_comment.click(function () {

        if ($(this).hasClass('disabled')) {
            return false;
        }
        var data;
        if ($comment_form.is('form')) {
            data = $comment_form.serialize();
        } else {
            data = $comment_form.find('select, textarea, input').serialize();
        }

        $.ajax({
            data: data,
            url: QAURLs.AJAX_COMMENT,
            type: 'POST',
            success: function (res) {
                $comment.val('').trigger('keyup');
                display_comment(res);
            },
            error: function (res) {
                console.log(res);
                console.log(res.responseJSON.message);
            }
        })
    });

    function display_comment(res) {

        $comments.append(res.template);
        $($comments).find('#c' + res.c_id).slideDown('fast');
    }

});