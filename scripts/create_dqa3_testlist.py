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
    nargs_wrong = len(args) != 3
    if not nargs_wrong:
        mode, tl_name, beam = args

    if nargs_wrong or mode not in ["db", "testpack"]:
        print("Usage 'python manage.py runscript create_dqa3_testlist --script-args {testpack,db} \"{test_list_name}\" {beam}")
        print("To create a test list:")
        print("    'python manage.py runscript create_dqa3_testlist --script-args testpack \"Daily QA Results: 6X\" 6X'")
        print("To create a test pack:")
        print("    'python manage.py runscript create_dqa3_testlist --script-args db \"Daily QA Results: 12E\" 12E'")
    else:
        create_dqa3(mode, tl_name, beam)


class Rollback(Exception):
    pass


def create_dqa3(mode, tl_name, beam):

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

            test_list_name = tl_name
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
                test_name = f"{test_list_name}: {name}"
                slug = slugify(param).lower().replace("-", "_")
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

            if mode == "testpack":
                tp = create_testpack(test_lists=[test_list])
                fname = "dqa3-qcpump-%s-test-list.tpk" % beam.lower()
                json.dump(tp, open(fname, "w"), indent=2)
                print("Wrote '%s' Test Pack to %s" % (test_list.name, fname))
                raise Rollback("Rollback so we don't actually save the tests")
            else:
                domain = Site.objects.get_current().domain
                url = '%s://%s%s' % (settings.HTTP_OR_HTTPS, domain, test_list.get_absolute_url())
                print("Created '%s' Test List (%s)" % (test_list.name, url))

    except IntegrityError:
        print(
            "\tThere was a conflict with an existing Test List slug or "
            "Test name when trying to create this test list."
        )
    except Rollback:
        pass
