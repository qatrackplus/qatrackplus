from qatrack.qa.models import User


def fix_ldap_passwords():
    for user in User.objects.all():
        if user.check_password("ldap authenticated"):
            user.set_unusable_password()
            user.save()
