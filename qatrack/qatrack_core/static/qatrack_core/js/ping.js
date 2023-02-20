require(['jquery', 'bootstrap'], function($) {

    var loggedOutMessage = (
        '<div class="logout-alert direct-chat-message right">' +
        ' <div class="direct-chat-text">' +
        '  Server is not responding or you may have been logged out.' +
        '  To prevent data loss, please log in using' +
        '  a different tab and then return to this tab. ' +
        '  <a class="btn btn-xs btn-default new-tab-link alert-link" target="_blank" href="' + QAURLs.LOGIN + '">' +
        '    Log In  <i class="fa fa-chevron-right" aria-hidden="true"></i>' +
        '  </a>' +
        ' <div>' +
        '</div>'
    );

    var loggedOutMessage2 = (
        '  Server is not responding or you may have been logged out.' +
        '  To prevent data loss, please log in using' +
        '  a different tab and then return to this tab. ' +
        '  <a class="btn btn-xs btn-default new-tab-link alert-link" target="_blank" href="' + QAURLs.LOGIN + '">' +
        '    Log In  <i class="fa fa-chevron-right" aria-hidden="true"></i>' +
        '  </a>'
    );

    var pingInterval = siteConfig.PING_INTERVAL_S*1000;
    var pingRequestTimeout = 1000;
    var consecutiveFailures = 0;
    var maxConsecutiveFailures = 3;
    var loggedOutMessageShown = false;
    var $popOvers = $(".ping-popover").popover({
        container: 'body',
        trigger: 'manual',
        title: false,
        content: loggedOutMessage2,
        html: true,
        placement: 'auto right',
        viewport: function($el){
            var $viewport = $el.parents(".ping-popover-container").parent();
            if ($viewport.length === 0){
                return $el.parent();
            }
            return $viewport;
        }
    });

    window.userIsAuthenticated = true;

    function setAuthenticatedState(authenticated){

        if (!authenticated){
            consecutiveFailures += 1;
        }else {
            consecutiveFailures = 0;
        }

        var wasAuthenticated = (consecutiveFailures === 0) && (!window.userIsAuthenticated);
        var loggedOutOrServerUnreachable = (consecutiveFailures >= maxConsecutiveFailures) && window.userIsAuthenticated;

        var changedState = wasAuthenticated || loggedOutOrServerUnreachable;

        if (wasAuthenticated){
            window.userIsAuthenticated = true;
        }else if (loggedOutOrServerUnreachable){
            window.userIsAuthenticated = false;
        }

        if (changedState){
            setUserStatusIndicators(window.userIsAuthenticated);
            if (window.userIsAuthenticated){
                // update csrf tokens whenever user gets logged back in
                $.qatrack.updateCsrfTokenInputs();
            }
        }
    }

    function setUserStatusIndicators(authenticated){

        var $buttons = $("button[type=submit],.service-save");
        if (authenticated){
            //$(".logged-out-message").html("");
            $popOvers.popover("hide");
            $buttons.each(function(idx, el){
                var $el = $(el);
                $el.attr({
                    'disabled': false,
                    'title': $el.data("orig-title")
                });
            }).toggleClass("btn-danger btn-primary");
        } else {
            //$(".logged-out-message").html(loggedOutMessage);
            $popOvers.popover("show");
            $buttons.each(function(idx, el){
                var $el = $(el);
                $el.data("orig-title", $el.attr("title"));
                $el.attr({
                    'disabled': true,
                    'title': 'Please wait until QATrack+ can reach the server before submitting'
                });
            }).toggleClass("btn-danger btn-primary");
        }
    }


    function ping(){
        $.ajax({
            url: QAURLs.PING,
            type: 'GET',
            timeout: pingRequestTimeout,
            success: function (res) {
                setAuthenticatedState(res.logged_in);
            },
            error: function (res) {
                setAuthenticatedState(false);
            }
        });
    }

    if (pingInterval > 0){
        setInterval(ping, pingInterval);
    }

});
