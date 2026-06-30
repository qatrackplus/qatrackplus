from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse


def updateCombo(request, id):
    model_class = ContentType.objects.get(id=id).model_class()

    #    print "appa", model_class

    a = model_class.objects.all()
    use_name = (
        not model_class._meta.ordering and 'name' in [x.name for x in model_class._meta.fields] and
        model_class._meta.get_field("name").concrete
    )
    if use_name:
        a = a.order_by("name")
    out = ""
    for b in a:
        out = "%s<option value='%s'>%s" % (
            out,
            b.id,
            b,
        )
    out = "<option></option>" + out
    return HttpResponse(out)
