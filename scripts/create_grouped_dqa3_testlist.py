import json

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils.text import slugify  # noqa: #402

from qatrack.qa import models

from qatrack.qa.testpack import create_testpack
from qatrack.qa.utils import get_internal_user  # noqa: #402

user = get_internal_user()


def run(*args):
    nargs_wrong = len(args) < 2
    if not nargs_wrong:
        mode = args[0]
        beams = ','.join(args[1:])
        beams = [b.strip() for b in beams.strip(" ,").split(",") if b.strip()]

    if nargs_wrong or mode not in ["db", "testpack"]:
        print(
            "Usage python manage.py runscript create_grouped_dqa3_testlist --script-args {testpack,db} {beam1} {beam2} ... {beamN}"
        )  # noqa: E501
        print("To create a test list:")
        print(
            "    python manage.py runscript create_grouped_dqa3_testlist --script-args testpack 6X 6FFF 10X 10FFF 18X \"6X EDW60\""
        )  # noqa: E501
        print("To create a test pack:")
        print(
            "    python manage.py runscript create_grouped_dqa3_testlist --script-args db 6X 6FFF 10X 10FFF 18X \"6X EDW60\" 6E 9E 12E"
        )  # noqa: E501
    else:
        create_dqa3(mode, beams)


class Rollback(Exception):
    pass


def create_dqa3(mode, beams):

    params = [
        "Signature",
        "Temperature",
        "Pressure",
        "Dose",
        "Dose Baseline",
        "Dose Diff",
        "AxSym",
        "AxSym Baseline",
        "AxSym Diff",
        "TrSym",
        "TrSym Baseline",
        "TrSym Diff",
        "QAFlat",
        "QAFlat Baseline",
        "QAFlat Diff",
        "Energy",
        "Energy Baseline",
        "Energy Diff",
        "XSize",
        "XSize Baseline",
        "XSize Diff",
        "XShift",
        "XShift Baseline",
        "XShift Diff",
        "YSize",
        "YSize Baseline",
        "YSize Diff",
        "YShift",
        "YShift Baseline",
        "YShift Diff",
        "Data Key",
    ]
    string_tests = ["Signature", "Data Key"]

    try:
        with transaction.atomic():

            cat = "Daily QA3"
            cat, _ = models.Category.objects.get_or_create(
                name=cat,
                defaults={
                    "slug": slugify(cat),
                    "description": cat,
                },
            )

            parent_test_list_name = f"Daily QA3 Results"
            print(f"Creating Test List: {parent_test_list_name}")
            parent_test_list, _ = models.TestList.objects.get_or_create(
                name=parent_test_list_name,
                slug=slugify(parent_test_list_name),
                defaults={
                    "created_by": user,
                    "modified_by": user,
                },
            )

            for beam_num, beam in enumerate(beams):

                test_list_name = f"Daily QA3 Results: {beam}"
                print(f"Creating Test List: {test_list_name}")
                test_list, _ = models.TestList.objects.get_or_create(
                    name=test_list_name,
                    slug=slugify(test_list_name),
                    defaults={
                        "created_by": user,
                        "modified_by": user,
                    },
                )
                for param_idx, param in enumerate(params):

                    unit = ""
                    if param == "Pressure":
                        unit = "kPa"
                    elif param == "Temperature":
                        unit = "°C"
                    elif param not in string_tests:
                        unit = "%" if 'shift' not in param.lower() and 'size' not in param.lower() else "cm"
                    name = f"{beam}: {param} ({unit})" if unit else f"{beam}: {param}"
                    test_name = f"DQA3 Results: {name}"
                    slug = ("%s_%s" % (slugify(param), slugify(beam))).lower().replace("-", "_")
                    print(f"\tCreating Test: {test_name} ({slug})")
                    test, _ = models.Test.objects.get_or_create(
                        name=test_name,
                        display_name=name,
                        slug=slug,
                        type=models.SIMPLE if param not in string_tests else models.STRING,
                        defaults={
                            "created_by": user,
                            "modified_by": user,
                            "formatting": "%.3f" if param not in string_tests else "",
                            "category": cat,
                            "description": "",
                        },
                    )
                    models.TestListMembership.objects.get_or_create(
                        test=test,
                        test_list=test_list,
                        order=param_idx,
                    )
                models.Sublist.objects.create(parent=parent_test_list, child=test_list, outline=True, order=beam_num)

            if mode == "testpack":
                tp = create_testpack(test_lists=[parent_test_list])
                fname = "grouped-dqa3-qcpump-test-list.tpk" % beam.lower()
                json.dump(tp, open(fname, "w"), indent=2)
                print("Wrote '%s' Test Pack to %s" % (parent_test_list.name, fname))
                raise Rollback("Rollback so we don't actually save the tests")
            else:
                domain = Site.objects.get_current().domain
                url = '%s://%s%s' % (settings.HTTP_OR_HTTPS, domain, parent_test_list.get_absolute_url())
                print("Created '%s' Test List (%s)" % (parent_test_list.name, url))

    except IntegrityError:
        print(
            "\tThere was a conflict with an existing Test List slug or "
            "Test name when trying to create this test list."
        )
    except Rollback:
        pass
