from django.conf import settings
from django.db.models import Case, CharField, F, IntegerField, Value, When
from django.urls import reverse
from django.utils.translation import gettext as _
from qatrack.qa.models import Category, Frequency, UnitTestCollection
from qatrack.units.models import Site, Unit


class BaseTree:

    def __init__(self, visible_to):
        self.groups = visible_to
        self.setup_qs()
        self.setup_units()
        self.setup_frequencies()

    def setup_units(self):
        self.units = dict(Unit.objects.filter(active=True).values_list("number", "name"))
        self.sites = dict(Site.objects.values_list("slug", "name"))
        self.sites['other'] = _("Other")

    def setup_frequencies(self):
        self.freqs = dict(Frequency.objects.values_list("slug", "name"))
        self.freqs[None] = _("Ad-Hoc")
        self.freqs["ad-hoc"] = _("Ad-Hoc")

    def new_node(self, text, expanded=False, nodes=None):

        node = {
            'text': text,
            'state': {'expanded': int(bool(expanded))},
        }
        if nodes is not False:
            node['nodes'] = nodes or []
        return node

    def site_text(self, site):
        site = site or "other"
        site_name = self.sites[site]
        href = reverse("qa_by_site", kwargs={'site': site})
        title = _("Click to browse QC at Site {site}").format(site=site_name)
        text = '%s <a href="%s" title="%s"><i class="fa fa-cubes"></i></a>' % (site_name, href, title)
        return text

    def unit_text(self, unit_number):
        uname = self.units[unit_number]
        href = reverse("qa_by_unit", kwargs={'unit_number': unit_number})
        title = _("Click to perform QC on Unit {unit}").format(unit=uname)
        text = '%s <a href="%s" title="%s"><i class="fa fa-cube"></i></a>' % (uname, href, title)
        return text

    def unit_frequency_text(self, unit_number, freq_slug):
        freq_slug = freq_slug or "ad-hoc"
        freq_name = self.freqs[freq_slug]
        href = reverse("qa_by_unit_frequency", kwargs={"frequency": freq_slug, 'unit_number': unit_number})
        title = _("Click to peform {frequency} QC on Unit {unit}").format(
            frequency=freq_name, unit=self.units[unit_number]
        )
        text = '%s <a href="%s" title="%s"><i class="fa fa-clock-o"></i></a>' % (freq_name, href, title)
        return text

    def utc_text(self, utc_id, utc_name, unit_name):
        href = reverse("perform_qa", kwargs={"pk": utc_id})
        title = _("Click to peform {tests_collection} on Unit {unit}").format(tests_collection=utc_name, unit=unit_name)
        text = '<a href="%s" title="%s">%s <i class="fa fa-list"></i></a>' % (href, title, utc_name)
        return text


class BootstrapCategoryTree(BaseTree):

    def __init__(self, visible_to):
        super().__init__(visible_to)
        self.setup_categories()

    def setup_qs(self):

        self.qs = UnitTestCollection.objects.filter(
            unit__active=True,
            active=True,
            visible_to__in=self.groups,
        ).annotate(
            cat_tree_id=Case(
                When(
                    test_list__testlistmembership__test__category__tree_id__isnull=False,
                    then=F("test_list__testlistmembership__test__category__tree_id")
                ),
                When(
                    test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,
                    then=F("test_list__children__child__testlistmembership__test__category__tree_id")
                ),
                When(
                    test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                    then=F("test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id")  # noqa: E501
                ),
                When(
                    test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                    then=F(
                        "test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id"  # noqa: E501
                    )
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
            cat_name=Case(
                When(
                    test_list__testlistmembership__test__category__tree_id__isnull=False,
                    then=F("test_list__testlistmembership__test__category__name")
                ),
                When(
                    test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,
                    then=F("test_list__children__child__testlistmembership__test__category__name")
                ),
                When(
                    test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                    then=F("test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__name")  # noqa: E501
                ),
                When(
                    test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                    then=F(
                        "test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__name"  # noqa: E501
                    )
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            cat_level=Case(
                When(
                    test_list__testlistmembership__test__category__tree_id__isnull=False,
                    then=F("test_list__testlistmembership__test__category__level")
                ),
                When(
                    test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,
                    then=F("test_list__children__child__testlistmembership__test__category__level")
                ),
                When(
                    test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                    then=F("test_list_cycle__testlistcyclemembership__test_list__testlistmembership__test__category__level")  # noqa: E501
                ),
                When(
                    test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__tree_id__isnull=False,  # noqa: E501
                    then=F(
                        "test_list_cycle__testlistcyclemembership__test_list__children__child__testlistmembership__test__category__level"  # noqa: E501
                    )
                ),
                default=Value(-1),
                output_field=IntegerField(),
            ),
        ).order_by(
            "unit__site__name",
            "unit__%s" % settings.ORDER_UNITS_BY,
            "frequency__nominal_interval",
            "cat_tree_id",
            "cat_level",
            "cat_name",
            "name",
        ).values_list(
            "id",
            "name",
            "unit__site__slug",
            "unit__number",
            "unit__name",
            "frequency__slug",
            "cat_tree_id",
            "cat_name",
        ).distinct()  # yapf: disable

    def setup_categories(self):
        """Set up category maps for use generating the tree"""

        self.root_cats = {}
        self.all_cats = {}
        self.cat_name_to_id = {}
        qs = Category.objects.order_by("tree_id", "level", "name").values_list("id", "tree_id", "level", "slug", "name")
        for cat_id, tree_id, level, slug, name in qs:
            self.cat_name_to_id[name] = cat_id
            self.all_cats[cat_id] = {'tree_id': tree_id, 'level': level, 'slug': slug, 'name': name}
            if level == 0:
                self.root_cats[tree_id] = cat_id

    def generate(self):

        seen_sites = set()

        tree = [self.new_node(_("QC by Unit, Frequency, & Category"))]
        root_nodes = tree[-1]['nodes']

        for utc_id, utc_name, site, unum, uname, freq_slug, cat_tree_id, cat_name in self.qs:

            if site not in seen_sites:
                seen_sites.add(site)
                seen_units = set()
                text = self.site_text(site)
                root_nodes.append(self.new_node(text))
                site_nodes = root_nodes[-1]['nodes']

            if unum not in seen_units:
                seen_units.add(unum)
                seen_freqs = set()
                text = self.unit_text(unum)
                site_nodes.append(self.new_node(text, 0))
                unit_nodes = site_nodes[-1]['nodes']

            if freq_slug not in seen_freqs:
                seen_freqs.add(freq_slug)
                seen_trees = set()
                text = self.unit_frequency_text(unum, freq_slug)
                unit_nodes.append(self.new_node(text, 0))
                freq_nodes = unit_nodes[-1]['nodes']

            try:
                cat_id = self.cat_name_to_id[cat_name]
            except KeyError:
                # handle case where no categories exist
                continue

            cat_level = self.all_cats[cat_id]['level']

            if cat_tree_id not in seen_trees:
                # we want to add a new category tree to frequency
                # note in this case cat_id == root_cat_id
                seen_trees.add(cat_tree_id)
                seen_subs = set()
                seen_names = set()

                root_id = self.root_cats[cat_tree_id]
                text = self.unit_category_text(unum, root_id)
                freq_nodes.append(self.new_node(text, 1))
                cat_nodes = freq_nodes[-1]['nodes']
                cur_root = cat_nodes

            #if cat_level == 1 and cat_id not in seen_subs:
            #    # add a new sub category and start appending to it
            #    seen_subs.add(cat_id)
            #    seen_names = set()
            #    text = self.unit_category_text(unum, cat_id)
            #    cur_root.append(self.new_node(text, 1))
            #    cat_nodes = cur_root[-1]['nodes']

            if utc_name not in seen_names:
                seen_names.add(utc_name)
                text = self.utc_text(utc_id, utc_name, uname)
                cat_nodes.append(self.new_node(text, 1, nodes=False))

        return tree

    def unit_category_text(self, unit_number, category_id):
        if not category_id:
            return _("No categories defined")

        cat = self.all_cats[category_id]
        href = reverse("qa_by_unit_category", kwargs={"unit_number": unit_number, "category": cat['slug']})
        title = _("Click to peform {category} QC on {unit}").format(category=cat['name'], unit=self.units[unit_number])
        text = '%s <a href="%s" title="%s"><i class="fa fa-tag fa-fw"></i></a>' % (cat['name'], href, title)
        return text


class BootstrapFrequencyTree(BaseTree):

    def setup_qs(self):

        self.qs = UnitTestCollection.objects.filter(
            visible_to__in=self.groups,
            unit__active=True,
            active=True,
        ).order_by(
            "unit__site__name",
            "unit__%s" % settings.ORDER_UNITS_BY,
            "frequency__nominal_interval",
            "name",
        ).values_list(
            "id",
            "name",
            "frequency__slug",
            "unit__site__slug",
            "unit__number",
            "unit__name",
        )

    def generate(self):

        seen_sites = set()
        seen_freqs = set()
        seen_sites = set()
        seen_units = set()
        seen_names = set()

        tree = [self.new_node(_("QC by Unit & Frequency"))]
        root_nodes = tree[-1]['nodes']
        for utc_id, utc_name, freq_slug, site, unum, uname in self.qs:

            if site not in seen_sites:
                seen_sites.add(site)
                seen_units = set()
                text = self.site_text(site)
                root_nodes.append(self.new_node(text))
                site_nodes = root_nodes[-1]['nodes']

            if unum not in seen_units:
                seen_units.add(unum)
                seen_freqs = set()
                text = self.unit_text(unum)
                site_nodes.append(self.new_node(text, 0))
                unit_nodes = site_nodes[-1]['nodes']

            if freq_slug not in seen_freqs:
                seen_freqs.add(freq_slug)
                seen_names = set()
                text = self.unit_frequency_text(unum, freq_slug)
                unit_nodes.append(self.new_node(text))
                freq_nodes = unit_nodes[-1]['nodes']

            if utc_name not in seen_names:
                seen_names.add(utc_name)
                text = self.utc_text(utc_id, utc_name, uname)
                freq_nodes.append(self.new_node(text, 1, nodes=False))

        return tree
