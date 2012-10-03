from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
decorator_with_arguments = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)

@decorator_with_arguments
def custom_permission_required(function, perm):
    def _function(request, *args, **kwargs):
        insufficient_perm_msg = _("Your account does not have the required permissions to view the requested page")
        if request.user.has_perm(perm):
            return function(request, *args, **kwargs)
        else:
            messages.add_message(request,messages.WARNING,insufficient_perm_msg)
            return HttpResponseRedirect(reverse("home"))

    return _function
