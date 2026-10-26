from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from qatrack.qatrack_core.hosts import LOOPBACK_HOSTS

# The Site record Django creates when the sites app is first migrated.
DJANGO_DEFAULT = 'example.com'


def first_public_host(hosts):
    """The first of `hosts` that names a single real host, or None.

    '*' and Django's '.example.com' wildcard form match many hosts, so neither
    can be a link target.
    """
    for host in hosts:
        if host and host != '*' and not host.startswith('.') and host not in LOOPBACK_HOSTS:
            return host
    return None


class Command(BaseCommand):
    help = (
        "Set the Site record's domain and name, which QATrack+ uses for the links in emails and "
        "reports and for the name at the top of each page. A value given here is always applied. "
        "Without one, a record still at Django's default (example.com) is filled in once: the "
        "domain from ALLOWED_HOSTS and the name 'QATrack+'. Otherwise the record is left alone, "
        "so changes made in the admin are kept."
    )

    def add_arguments(self, parser):
        parser.add_argument('--domain', default='', help="Host name people use to reach QATrack+ (SITE_DOMAIN).")
        parser.add_argument('--name', default='', help="Name shown at the top of each page (SITE_NAME).")

    def handle(self, *args, **options):
        domain = options['domain'].strip().rstrip('/')
        name = options['name'].strip()

        site = Site.objects.get_current()
        changed = []

        if domain:
            if site.domain != domain:
                site.domain = domain
                changed.append('domain')
        elif site.domain == DJANGO_DEFAULT:
            host = first_public_host(settings.ALLOWED_HOSTS)
            if host:
                site.domain = host
                changed.append('domain')
            else:
                self.stdout.write(
                    "The site's domain is still example.com, so links in emails and reports point "
                    "there. Set SITE_DOMAIN in .env, or list the host name in ALLOWED_HOSTS."
                )

        if name:
            if site.name != name:
                site.name = name
                changed.append('name')
        elif site.name == DJANGO_DEFAULT:
            site.name = settings.SITE_NAME
            changed.append('name')

        if changed:
            site.save(update_fields=changed)
            self.stdout.write("Site %s set: domain %s, name %s" % (' and '.join(changed), site.domain, site.name))
