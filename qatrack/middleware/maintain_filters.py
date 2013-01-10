from django import http
from django.conf import settings

# based on http://code.djangoproject.com/ticket/3777#comment:4
class FilterPersistMiddleware(object):

    def process_request(self, request):

        if '/admin/' not in request.path:
            return None

        if not request.META.has_key('HTTP_REFERER'):
            return None

        popup = 'pop=1' in request.META['QUERY_STRING']
        path = request.path
        path = path[path.find('/admin'):len(path)]
        query_string = request.META['QUERY_STRING']
        if "prefilter=true" in query_string:
            return None
        session = request.session

        if session.get('redirected', False):#so that we dont loop once redirected
            del session['redirected']
            return None

        referrer = request.META['HTTP_REFERER'].split('?')[0]
        referrer = referrer[referrer.find('/admin'):len(referrer)]
        key = 'key'+path.replace('/','_')

        if popup:
            key = 'popup'+path.replace('/','_')

        if path == referrer: #We are in same page as before

            if query_string == '': #Filter is empty, delete it
                if session.get(key,False):
                    del session[key]
                return None
            request.session[key] = query_string
        else: #We are are coming from another page, restore filter if available

            if session.get(key, False):
                query_string=request.session.get(key)
                redirect_to = getattr(settings,"FORCE_SCRIPT_NAME","")+path+'?'+query_string
                request.session['redirected'] = True

                return http.HttpResponseRedirect(redirect_to)
        return None
