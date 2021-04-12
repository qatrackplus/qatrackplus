define(["jquery"], function ($){

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = $.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    $.qatrack = $.qatrack || {
        getCookie: getCookie,
        getCsrfToken: function(){
            return getCookie(siteConfig.CSRF_COOKIE_NAME);
        },
        updateCsrfTokenInputs: function(){
            // Update all CSRF Token inputs on the page
            // Necessary in order to submit a form after a user was logged out/back in
            // in a different tab
            var token = $.qatrack.getCsrfToken();
            $("input[name=csrfmiddlewaretoken]").val(token);
        }
    };

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    function sameOrigin(url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            /* note we grab the token before every request rather than at load
             * time in case we're logged out with say a perform QA page still loaded.
             * If the user logs back in in another tab then we can grab the fresh
             * csrftoken from the cookie so our ajax requests on the perform QA
             * tab won't get 403'd due to csrf token validation failing */
            var csrf_token = getCookie(siteConfig.CSRF_COOKIE_NAME);
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });

    return $;
});
