from django.db import migrations


def repair_empty_slugs(apps, schema_editor):
    """Give a usable slug to any fault type that has none (#677).

    A code written wholly in a script with no ASCII form slugified to "", and
    both URL patterns that take a fault type slug require at least one
    character - so the fault type's own page was a 500 and every row of "All
    Fault Types" failed to render. Those records cannot be reached to be
    repaired by hand, which is why this runs.

    `slug` is unique, so on an engine that enforces it there is at most one such
    row; the loop is here because 4.0 is known to have lost unique constraints
    on MS SQL Server, where there may be several.

    Only empty slugs are repaired. The uniqueness loop gave the *second* such
    code a bare number - `1`, `2` - which is meaningless but is a working
    address that may already be linked or bookmarked, and is indistinguishable
    from the slug of a fault type legitimately coded "1". Those are left alone;
    they regenerate on their own the next time the record is saved.
    """

    FaultType = apps.get_model("faults", "FaultType")

    broken = list(FaultType.objects.filter(slug="").order_by("pk"))
    if not broken:
        return

    taken = set(FaultType.objects.exclude(slug="").values_list("slug", flat=True))
    base = FaultType._meta.model_name  # "faulttype", and ASCII by construction

    for fault_type in broken:
        append = 0
        while True:
            slug = base if append == 0 else "%s-%d" % (base, append)
            if slug not in taken:
                break
            append += 1

        taken.add(slug)
        fault_type.slug = slug
        fault_type.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ('faults', '0015_v4_0_final'),
    ]

    operations = [
        # Reversing would mean putting back the empty slugs that raise
        # NoReverseMatch, so this deliberately does nothing on the way down. The
        # slugs it writes are valid for the earlier code as well, so an older
        # QATrack+ runs against them unchanged.
        migrations.RunPython(repair_empty_slugs, migrations.RunPython.noop),
    ]
