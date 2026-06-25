from django.contrib.auth.models import Group, Permission, User

from qatrack.qatrack_core.tests.utils import get_next_id


def create_user(is_staff=True, is_superuser=True, uname="user", pwd="password", is_active=True):
    try:
        u = User.objects.get(username=uname)
    except User.DoesNotExist:
        if is_superuser:
            u = User.objects.create_superuser(
                uname, "super@qatrackplus.com", pwd, is_staff=is_staff, is_active=is_active
            )
        else:
            u = User.objects.create_user(
                uname, "user@qatrackplus.com", password=pwd, is_staff=is_staff, is_active=is_active
            )
    finally:
        from django.contrib.contenttypes.models import ContentType

        from qatrack.qa.models import TestListInstance
        ct = ContentType.objects.get_for_model(TestListInstance)
        perm, _ = Permission.objects.get_or_create(
            codename="add_testlistinstance", content_type=ct, defaults={"name": "Can add test list instance"}
        )
        u.user_permissions.add(perm)
    return u


def create_group(name=None):
    if name is None:
        name = 'group_%04d' % get_next_id(Group.objects.order_by('id').last())
    g = Group(name=name)
    g.save()
    from django.contrib.contenttypes.models import ContentType

    from qatrack.qa.models import TestListInstance
    ct = ContentType.objects.get_for_model(TestListInstance)
    perm, _ = Permission.objects.get_or_create(
        codename="add_testlistinstance", content_type=ct, defaults={"name": "Can add test list instance"}
    )
    g.permissions.add(perm)
    return g
