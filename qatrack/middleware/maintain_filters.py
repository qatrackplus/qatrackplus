from django import http
from django.conf import settings

# based on http://code.djangoproject.com/ticket/3777#comment:4


class FilterPersistMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if '/admin/' not in request.path:
            return self.get_response(request)

        if not request.headers.get('referer', ""):
            return self.get_response(request)

        popup = 'popup=1' in request.META['QUERY_STRING']
        path = request.path
        path = path[path.find('/admin'):len(path)]
        query_string = request.META['QUERY_STRING']
        if "prefilter=true" in query_string:
            return self.get_response(request)
        session = request.session

        if session.get('redirected', False):  # so that we dont loop once redirected
            del session['redirected']
            return self.get_response(request)

        referrer = request.headers.get('referer', "").split('?')[0]
        referrer = referrer[referrer.find('/admin'):len(referrer)]
        key = 'key' + path.replace('/', '_')

        if popup:
            key = 'popup' + path.replace('/', '_')

        if path == referrer:  # We are in same page as before

            if query_string == '':  # Filter is empty, delete it
                if session.get(key, False):
                    del session[key]
                return self.get_response(request)
            request.session[key] = query_string
        else:  # We are are coming from another page, restore filter if available

            if session.get(key, False):
                query_string = request.session.get(key)
                root = getattr(settings, "FORCE_SCRIPT_NAME", "") or ""
                redirect_to = root + path + '?' + query_string
                request.session['redirected'] = True

                return http.HttpResponseRedirect(redirect_to)

        return self.get_response(request)
