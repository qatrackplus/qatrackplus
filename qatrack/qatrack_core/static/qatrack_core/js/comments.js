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

    var $err_comment = $('<div class="err-comment box-comment" style="display: none;"></div>');
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

        $err_comment.hide().remove();

        $.ajax({
            data: data,
            url: QAURLs.AJAX_COMMENT,
            type: 'POST',
            success: function (res) {
                $comment.val('').trigger('keyup');
                display_comment(res);
            },
            error: function (res) {
                display_error(res)
            }
        })
    });

    function display_comment(res) {

        $comments.append(res.template);
        $($comments).find('#c' + res.c_id).slideDown('fast');
    }
    function display_error(res) {

        var extra_string = '';
        $.each(res.responseJSON.extra, function(k, v) {
            extra_string += '<span class="comment">' + k + ': ' + v + '</span>';
        });
        $comments.append($err_comment);
        $err_comment.html(
            '<div class="comment-text"><span class="username">' + res.responseJSON.message +
            '<span class="text-muted pull-right"><i class="fa fa-error"></i></span></span>' + extra_string +
            '</div>'
        );
        $err_comment.slideDown('fast');
    }

});