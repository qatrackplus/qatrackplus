import random
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Max
from django_comments.models import Comment

from qatrack.faults.models import Fault, FaultType
from qatrack.parts.models import (
    Part,
    PartCategory,
    PartStorageCollection,
    PartSupplierCollection,
    PartUsed,
    Room,
    Storage,
    Supplier,
)
from qatrack.qa.models import (
    ABSOLUTE,
    BOOLEAN,
    COMPOSITE,
    PERCENT,
    SIMPLE,
    Category,
    Frequency,
    Reference,
    Test,
    TestInstance,
    TestInstanceStatus,
    TestList,
    TestListInstance,
    TestListMembership,
    Tolerance,
    UnitTestCollection,
    UnitTestInfo,
)
from qatrack.reports.models import ReportNote, ReportSchedule, SavedReport
from qatrack.service_log.models import (
    Hours,
    ReturnToServiceQA,
    ServiceArea,
    ServiceEvent,
    ServiceEventSchedule,
    ServiceEventStatus,
    ServiceEventTemplate,
    ServiceType,
    UnitServiceArea,
)
from qatrack.units.models import Modality, Unit, UnitAvailableTime, UnitClass, UnitType, Vendor
from qatrack.units.models import Site as ClinicalSite

from .base import BaseSampleDataGenerator


class SmallCenterGenerator(BaseSampleDataGenerator):
    """Generates realistic sample data for a Small Radiation Oncology Centre:
    - 2 Linacs (Varian TrueBeam & Elekta Versa HD)
    - 1 CT Simulator (Siemens SOMATOM Confidence)
    - Complete AAPM TG-142 / TG-51 / TG-66 aligned QA protocols
    - Rolling historical QA instances (90 days)
    - Service log events with RTS QA & service hours
    - Faults, parts inventory, and saved reports with schedules.
    """

    def generate(self):
        self.log("Starting Small Centre generation...", lambda s: s)
        self.ensure_default_fixtures()
        self.site = self.ensure_site()

        with transaction.atomic():
            self.create_groups_and_users()
            self.create_units_and_modalities()
            self.create_qa_protocols()
            self.create_service_and_parts_infrastructure()
            self.generate_qa_history()
            self.generate_service_and_fault_history()
            self.create_reports_and_schedules()

        self.log("Small Centre generation completed successfully!", lambda s: s)

    def create_groups_and_users(self):
        self.log("Creating user groups and staff accounts...", lambda s: s)

        # Groups
        self.grp_rtts, _ = Group.objects.get_or_create(name="Radiation Therapists")
        self.grp_physics, _ = Group.objects.get_or_create(name="Medical Physicists")
        self.grp_engineers, _ = Group.objects.get_or_create(name="Service Engineers")
        self.grp_admins, _ = Group.objects.get_or_create(name="QA Administrators")

        # Assign relevant permissions to groups
        all_perms = Permission.objects.all()
        qa_perms = all_perms.filter(content_type__app_label='qa')
        sl_perms = all_perms.filter(content_type__app_label='service_log')
        fault_perms = all_perms.filter(content_type__app_label='faults')
        part_perms = all_perms.filter(content_type__app_label='parts')
        report_perms = all_perms.filter(content_type__app_label='reports')

        # RTTs
        self.grp_rtts.permissions.set(
            qa_perms.filter(codename__in=['add_testlistinstance', 'can_view_history', 'can_choose_frequency'])
            | fault_perms.filter(codename__in=['add_fault', 'change_fault'])
            | sl_perms.filter(codename__in=['view_serviceevent', 'view_returntoserviceqa', 'perform_returntoserviceqa'])
        )

        # Medical Physicists
        self.grp_physics.permissions.set(
            qa_perms
            | sl_perms
            | fault_perms
            | report_perms
            | part_perms.filter(codename__in=['view_part', 'view_supplier'])
        )

        # Service Engineers
        self.grp_engineers.permissions.set(
            sl_perms
            | part_perms
            | fault_perms
            | qa_perms.filter(codename__in=['add_testlistinstance', 'can_view_history', 'view_unittestcollection'])
            | report_perms.filter(codename__in=['can_run_reports'])
        )

        # QA Administrators
        self.grp_admins.permissions.set(all_perms)

        # Users
        def create_user(username, email, first, last, groups, is_staff=True, is_superuser=False):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'is_staff': is_staff,
                    'is_superuser': is_superuser,
                }
            )
            user.set_password("password123")
            user.save()
            user.groups.set(groups)
            return user

        self.user_admin = create_user("admin", "admin@qatrackplus.com", "System", "Admin", [self.grp_admins], is_superuser=True)
        self.user_jane = create_user("jane.physicist", "jane.physicist@example.com", "Jane", "Physicist", [self.grp_physics, self.grp_admins])
        self.user_mark = create_user("mark.physicist", "mark.physicist@example.com", "Mark", "Davis", [self.grp_physics])
        self.user_sarah = create_user("sarah.therapist", "sarah.therapist@example.com", "Sarah", "Connor", [self.grp_rtts])
        self.user_dave = create_user("dave.engineer", "dave.engineer@example.com", "Dave", "Miller", [self.grp_engineers])
        self.user_alex = create_user("alex.resident", "alex.resident@example.com", "Alex", "Taylor", [self.grp_physics])

    def create_units_and_modalities(self):
        self.log("Configuring clinical site, vendors, modalities, and units...", lambda s: s)

        self.clinical_site, _ = ClinicalSite.objects.get_or_create(
            slug="main_campus",
            defaults={"name": "Main Campus"}
        )

        # Vendors
        vendor_varian, _ = Vendor.objects.get_or_create(name="Varian Medical Systems")
        vendor_elekta, _ = Vendor.objects.get_or_create(name="Elekta")
        vendor_siemens, _ = Vendor.objects.get_or_create(name="Siemens Healthineers")

        # Unit Classes
        uc_linac, _ = UnitClass.objects.get_or_create(name="Linac")
        uc_ct, _ = UnitClass.objects.get_or_create(name="CT Simulator")

        # Modalities
        mod_names = [
            "6MV", "10MV", "15MV", "6FFF", "10FFF",
            "6MeV", "9MeV", "12MeV", "15MeV", "18MeV",
            "OBI", "PortalVision", "CBCT", "XVI", "iViewGT",
            "CT", "4D-CT", "LAP Lasers"
        ]
        self.modalities = {}
        for m in mod_names:
            obj, _ = Modality.objects.get_or_create(name=m)
            self.modalities[m] = obj

        # Unit Types
        ut_truebeam, _ = UnitType.objects.get_or_create(
            name="TrueBeam",
            vendor=vendor_varian,
            unit_class=uc_linac,
            defaults={"model": "TrueBeam v2.7"}
        )
        ut_versa, _ = UnitType.objects.get_or_create(
            name="Versa HD",
            vendor=vendor_elekta,
            unit_class=uc_linac,
            defaults={"model": "Versa HD Agility"}
        )
        ut_somatom, _ = UnitType.objects.get_or_create(
            name="SOMATOM Confidence",
            vendor=vendor_siemens,
            unit_class=uc_ct,
            defaults={"model": "SOMATOM Confidence RT Pro"}
        )

        # Units
        self.unit_tb1 = self._get_or_create_unit(
            name="TB-1 (TrueBeam)",
            number=1,
            defaults={
                "type": ut_truebeam,
                "site": self.clinical_site,
                "serial_number": "TB-4521",
                "location": "Vault 1",
                "install_date": (self.now - timedelta(days=365*3)).date(),
                "date_acceptance": (self.now - timedelta(days=365*3 - 30)).date(),
                "active": True,
                "is_serviceable": True,
            }
        )
        self.unit_tb1.modalities.set([
            self.modalities["6MV"], self.modalities["10MV"], self.modalities["6FFF"], self.modalities["10FFF"],
            self.modalities["6MeV"], self.modalities["9MeV"], self.modalities["12MeV"], self.modalities["15MeV"], self.modalities["18MeV"],
            self.modalities["OBI"], self.modalities["PortalVision"], self.modalities["CBCT"]
        ])

        self.unit_versa = self._get_or_create_unit(
            name="Versa-HD",
            number=2,
            defaults={
                "type": ut_versa,
                "site": self.clinical_site,
                "serial_number": "V-154082",
                "location": "Vault 2",
                "install_date": (self.now - timedelta(days=365*2)).date(),
                "date_acceptance": (self.now - timedelta(days=365*2 - 30)).date(),
                "active": True,
                "is_serviceable": True,
            }
        )
        self.unit_versa.modalities.set([
            self.modalities["6MV"], self.modalities["10MV"], self.modalities["15MV"],
            self.modalities["6MeV"], self.modalities["9MeV"], self.modalities["12MeV"],
            self.modalities["XVI"], self.modalities["iViewGT"]
        ])

        self.unit_ct = self._get_or_create_unit(
            name="CT-Sim (SOMATOM)",
            number=3,
            defaults={
                "type": ut_somatom,
                "site": self.clinical_site,
                "serial_number": "CT-99120",
                "location": "CT Room 1",
                "install_date": (self.now - timedelta(days=365*4)).date(),
                "date_acceptance": (self.now - timedelta(days=365*4 - 30)).date(),
                "active": True,
                "is_serviceable": True,
            }
        )
        self.unit_ct.modalities.set([
            self.modalities["CT"], self.modalities["4D-CT"], self.modalities["LAP Lasers"]
        ])

        # Available time schedules (11 hrs Mon-Fri)
        for unit in [self.unit_tb1, self.unit_versa, self.unit_ct]:
            UnitAvailableTime.objects.get_or_create(
                unit=unit,
                date_changed=unit.date_acceptance,
                defaults={
                    "hours_sunday": timedelta(0),
                    "hours_monday": timedelta(hours=11),
                    "hours_tuesday": timedelta(hours=11),
                    "hours_wednesday": timedelta(hours=11),
                    "hours_thursday": timedelta(hours=11),
                    "hours_friday": timedelta(hours=11),
                    "hours_saturday": timedelta(0),
                }
            )

    def _get_or_create_unit(self, name, number, defaults):
        """Fetch or create a sample Unit.

        Unit.number is unique, so when the requested number is already taken by
        a pre-existing unit (i.e. the command was run without --clear) fall back
        to the next free number rather than raising an IntegrityError.
        """
        unit = Unit.objects.filter(name=name).first()
        if unit:
            return unit

        if Unit.objects.filter(number=number).exists():
            number = (Unit.objects.aggregate(Max("number"))["number__max"] or 0) + 1

        return Unit.objects.create(name=name, number=number, **defaults)

    def create_qa_protocols(self):
        self.log("Configuring QA Categories, Tolerances, Tests, and Test Lists...", lambda s: s)

        # Categories
        self.cat_safety, _ = Category.objects.get_or_create(name="Safety & Interlocks", defaults={"slug": "safety_interlocks", "description": "Door interlocks, audiovisual monitors, and emergency switches"})
        self.cat_dosimetry, _ = Category.objects.get_or_create(name="Dosimetry & Output", defaults={"slug": "dosimetry_output", "description": "Photon and electron beam constancy and calibration"})
        self.cat_mechanical, _ = Category.objects.get_or_create(name="Mechanical & Alignment", defaults={"slug": "mechanical_alignment", "description": "Lasers, ODI, collimator, gantry, and couch positioners"})
        self.cat_imaging, _ = Category.objects.get_or_create(name="Imaging & Guidance", defaults={"slug": "imaging_guidance", "description": "kV/MV planar alignment, CBCT image quality, and spatial resolution"})
        self.cat_ct, _ = Category.objects.get_or_create(name="CT Simulation", defaults={"slug": "ct_simulation", "description": "CT number accuracy, noise, laser isocenter, and table travel"})

        # Tolerances
        def get_or_create_tol(tol_type, act_low=None, tol_low=None, tol_high=None, act_high=None, bool_warning=False):
            tol = Tolerance.objects.filter(
                type=tol_type,
                act_low=act_low,
                tol_low=tol_low,
                tol_high=tol_high,
                act_high=act_high,
                bool_warning_only=bool_warning,
            ).first()
            if not tol:
                tol = Tolerance.objects.create(
                    type=tol_type,
                    act_low=act_low,
                    tol_low=tol_low,
                    tol_high=tol_high,
                    act_high=act_high,
                    bool_warning_only=bool_warning,
                    created_by=self.user_admin,
                    modified_by=self.user_admin,
                )
            return tol

        self.tol_1mm = get_or_create_tol(ABSOLUTE, act_low=-2.0, tol_low=-1.0, tol_high=1.0, act_high=2.0)
        self.tol_2mm = get_or_create_tol(ABSOLUTE, act_low=-3.0, tol_low=-2.0, tol_high=2.0, act_high=3.0)
        self.tol_pct2 = get_or_create_tol(PERCENT, act_low=-3.0, tol_low=-2.0, tol_high=2.0, act_high=3.0)
        self.tol_pct3 = get_or_create_tol(PERCENT, act_low=-5.0, tol_low=-3.0, tol_high=3.0, act_high=5.0)
        self.tol_hu = get_or_create_tol(ABSOLUTE, act_low=-10.0, tol_low=-5.0, tol_high=5.0, act_high=10.0)
        self.tol_bool = get_or_create_tol(BOOLEAN, bool_warning=False)

        # Frequencies
        self.freq_daily = Frequency.objects.get(slug="daily")
        self.freq_monthly = Frequency.objects.get(slug="monthly")
        # Ad-hoc QC is represented by a null frequency in QATrack+. Return to
        # service test lists must not be scheduled, so never fall back to a
        # real frequency here.
        self.freq_adhoc = Frequency.objects.filter(slug="ad-hoc").first()

        # Helper for creating tests
        def create_test(name, slug, category, test_type=SIMPLE, calc_proc=None, formatting="", display_name=""):
            test, _ = Test.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slug,
                    "display_name": display_name or name,
                    "category": category,
                    "type": test_type,
                    "calculation_procedure": calc_proc,
                    "formatting": formatting,
                    "created_by": self.user_admin,
                    "modified_by": self.user_admin,
                }
            )
            return test

        # Helper for creating test lists
        def create_test_list(name, slug, description, tests_with_order):
            tl, _ = TestList.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "created_by": self.user_admin,
                    "modified_by": self.user_admin,
                }
            )
            TestListMembership.objects.filter(test_list=tl).delete()
            for idx, test in enumerate(tests_with_order):
                TestListMembership.objects.create(test_list=tl, test=test, order=idx + 1)
            return tl

        # --- 1. Linac Daily QA Tests ---
        t_door = create_test("Door Interlock & Audiovisual", "door_interlock", self.cat_safety, test_type=BOOLEAN)
        t_beam_on = create_test("Beam-On Indicators & Radiation Signs", "beam_on_indicator", self.cat_safety, test_type=BOOLEAN)
        t_temp = create_test("Temperature (°C)", "temp", self.cat_dosimetry, formatting="%.1f")
        t_press = create_test("Pressure (kPa)", "press", self.cat_dosimetry, formatting="%.1f")
        t_ktp = create_test(
            "Temperature-Pressure Correction (kTP)",
            "ktp",
            self.cat_dosimetry,
            test_type=COMPOSITE,
            calc_proc="result = ((273.15 + temp) / 295.15) * (101.33 / press)",
            formatting="%.4f"
        )
        t_laser_x = create_test("Laser Lateral (X) [mm]", "laser_x", self.cat_mechanical, formatting="%.2f")
        t_laser_y = create_test("Laser Longitudinal (Y) [mm]", "laser_y", self.cat_mechanical, formatting="%.2f")
        t_laser_z = create_test("Laser Vertical (Z) [mm]", "laser_z", self.cat_mechanical, formatting="%.2f")
        t_odi = create_test("ODI at 100 cm [cm]", "odi_100", self.cat_mechanical, formatting="%.1f")
        t_raw_6mv = create_test("6MV Raw Electrometer Reading (nC)", "raw_6mv", self.cat_dosimetry, formatting="%.2f")
        t_dose_6mv = create_test(
            "6MV Output Constancy (cGy)",
            "dose_6mv",
            self.cat_dosimetry,
            test_type=COMPOSITE,
            calc_proc="result = raw_6mv * ktp * 1.002",
            formatting="%.2f"
        )
        t_raw_10mv = create_test("10MV Raw Electrometer Reading (nC)", "raw_10mv", self.cat_dosimetry, formatting="%.2f")
        t_dose_10mv = create_test(
            "10MV Output Constancy (cGy)",
            "dose_10mv",
            self.cat_dosimetry,
            test_type=COMPOSITE,
            calc_proc="result = raw_10mv * ktp * 0.998",
            formatting="%.2f"
        )
        t_dose_6mev = create_test("6MeV Electron Output (cGy)", "dose_6mev", self.cat_dosimetry, formatting="%.2f")

        self.tl_linac_daily = create_test_list(
            "Linac Daily Morning QA",
            "linac_daily_qa",
            "Standard AAPM TG-142 morning quality control test list for medical linear accelerators.",
            [t_door, t_beam_on, t_temp, t_press, t_ktp, t_laser_x, t_laser_y, t_laser_z, t_odi, t_raw_6mv, t_dose_6mv, t_raw_10mv, t_dose_10mv, t_dose_6mev]
        )

        # --- 2. Linac Monthly QA Tests ---
        t_gantry = create_test("Gantry Rotation Readout (0/90/180/270 deg)", "gantry_rot", self.cat_mechanical, formatting="%.2f")
        t_collimator = create_test("Collimator Rotation Readout (deg)", "collimator_rot", self.cat_mechanical, formatting="%.2f")
        t_couch = create_test("Couch Position Readout (mm)", "couch_pos", self.cat_mechanical, formatting="%.2f")
        t_light_rad = create_test("Light vs Radiation Field Congruence (mm)", "light_rad_field", self.cat_mechanical, formatting="%.2f")
        t_flatness = create_test("6MV Beam Flatness (%)", "flatness_6mv", self.cat_dosimetry, formatting="%.2f")
        t_symmetry = create_test("6MV Beam Symmetry (%)", "symmetry_6mv", self.cat_dosimetry, formatting="%.2f")
        t_kv_mv = create_test("kV/MV Isocenter Coincidence (mm)", "kv_mv_iso", self.cat_imaging, formatting="%.2f")
        t_cbct_align = create_test("CBCT Geometric Alignment (mm)", "cbct_align", self.cat_imaging, formatting="%.2f")

        self.tl_linac_monthly = create_test_list(
            "Linac Monthly Mechanical & Imaging QA",
            "linac_monthly_qa",
            "Monthly comprehensive mechanical, dosimetric constancy, and onboard imaging QA.",
            [t_gantry, t_collimator, t_couch, t_light_rad, t_flatness, t_symmetry, t_kv_mv, t_cbct_align]
        )

        # --- 3. Linac Return To Service (RTS) QA ---
        t_rts_interlock = create_test("Post-Maintenance Interlocks Check", "rts_interlocks", self.cat_safety, test_type=BOOLEAN)
        t_rts_dose = create_test("Post-Maintenance 6MV Output Constancy (cGy)", "rts_output_6mv", self.cat_dosimetry, formatting="%.2f")
        t_rts_laser = create_test("Post-Maintenance Laser Alignment (mm)", "rts_lasers", self.cat_mechanical, formatting="%.2f")

        self.tl_linac_rts = create_test_list(
            "Linac Return To Service QA",
            "linac_rts_qa",
            "Return to service verification following preventative or corrective engineering maintenance.",
            [t_rts_interlock, t_rts_dose, t_rts_laser]
        )

        # --- 4. CT Sim Daily QA ---
        t_ct_door = create_test("CT Room Door Interlock & Audio", "ct_door_interlock", self.cat_safety, test_type=BOOLEAN)
        t_ct_laser = create_test("External LAP Laser Alignment (mm)", "ct_laser_align", self.cat_ct, formatting="%.2f")
        t_ct_water = create_test("Water Phantom CT Number (HU)", "ct_water_hu", self.cat_ct, formatting="%.1f")

        self.tl_ct_daily = create_test_list(
            "CT Simulator Daily QA",
            "ct_sim_daily_qa",
            "Daily quality assurance check for radiotherapy CT Simulator.",
            [t_ct_door, t_ct_laser, t_ct_water]
        )

        # --- 5. CT Sim Monthly QA ---
        t_ct_water_m = create_test("Water Insert (0 HU nominal)", "ct_hu_water_m", self.cat_ct, formatting="%.1f")
        t_ct_air_m = create_test("Air Insert (-1000 HU nominal)", "ct_hu_air_m", self.cat_ct, formatting="%.1f")
        t_ct_bone_m = create_test("Teflon/Bone Insert (990 HU nominal)", "ct_hu_bone_m", self.cat_ct, formatting="%.1f")
        t_ct_acrylic_m = create_test("Acrylic Insert (120 HU nominal)", "ct_hu_acrylic_m", self.cat_ct, formatting="%.1f")
        t_ct_noise_m = create_test("Image Noise / Standard Deviation (HU)", "ct_noise_m", self.cat_ct, formatting="%.2f")
        t_ct_slice_m = create_test("Slice Thickness Accuracy (mm)", "ct_slice_m", self.cat_ct, formatting="%.2f")
        t_ct_table_m = create_test("Table Travel Accuracy (mm)", "ct_table_m", self.cat_ct, formatting="%.2f")

        self.tl_ct_monthly = create_test_list(
            "CT Simulator Monthly Quality Assurance",
            "ct_sim_monthly_qa",
            "Monthly CT Number linearity, image noise, slice thickness, and geometric accuracy.",
            [t_ct_water_m, t_ct_air_m, t_ct_bone_m, t_ct_acrylic_m, t_ct_noise_m, t_ct_slice_m, t_ct_table_m]
        )

        # --- UnitTestCollections & UnitTestInfo references ---
        self.utcs = {}
        tl_content_type = ContentType.objects.get_for_model(TestList)

        def assign_tl(unit, test_list, freq, assigned_to_group):
            utc, _ = UnitTestCollection.objects.get_or_create(
                unit=unit,
                frequency=freq,
                content_type=tl_content_type,
                object_id=test_list.id,
                defaults={
                    "assigned_to": assigned_to_group,
                    "auto_schedule": freq is not None,
                    "active": True,
                }
            )
            utc.visible_to.set([self.grp_rtts, self.grp_physics, self.grp_admins])
            self.utcs[(unit.id, test_list.id)] = utc
            return utc

        # Assign to Linacs
        self.utc_tb1_daily = assign_tl(self.unit_tb1, self.tl_linac_daily, self.freq_daily, self.grp_rtts)
        self.utc_tb1_monthly = assign_tl(self.unit_tb1, self.tl_linac_monthly, self.freq_monthly, self.grp_physics)
        self.utc_tb1_rts = assign_tl(self.unit_tb1, self.tl_linac_rts, self.freq_adhoc, self.grp_physics)

        self.utc_versa_daily = assign_tl(self.unit_versa, self.tl_linac_daily, self.freq_daily, self.grp_rtts)
        self.utc_versa_monthly = assign_tl(self.unit_versa, self.tl_linac_monthly, self.freq_monthly, self.grp_physics)
        self.utc_versa_rts = assign_tl(self.unit_versa, self.tl_linac_rts, self.freq_adhoc, self.grp_physics)

        # Assign to CT Sim
        self.utc_ct_daily = assign_tl(self.unit_ct, self.tl_ct_daily, self.freq_daily, self.grp_rtts)
        self.utc_ct_monthly = assign_tl(self.unit_ct, self.tl_ct_monthly, self.freq_monthly, self.grp_physics)

        # Configure references & tolerances in UnitTestInfo
        self.utis = {}
        for unit in [self.unit_tb1, self.unit_versa]:
            # Linac Daily
            self._set_uti(unit, t_door, ref_val=1.0, tol=self.tol_bool, is_bool=True)
            self._set_uti(unit, t_beam_on, ref_val=1.0, tol=self.tol_bool, is_bool=True)
            self._set_uti(unit, t_temp, ref_val=22.0)
            self._set_uti(unit, t_press, ref_val=101.3)
            self._set_uti(unit, t_ktp, ref_val=1.0)
            self._set_uti(unit, t_laser_x, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_laser_y, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_laser_z, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_odi, ref_val=100.0, tol=self.tol_1mm)
            self._set_uti(unit, t_raw_6mv, ref_val=99.8)
            self._set_uti(unit, t_dose_6mv, ref_val=100.0, tol=self.tol_pct2)
            self._set_uti(unit, t_raw_10mv, ref_val=100.2)
            self._set_uti(unit, t_dose_10mv, ref_val=100.0, tol=self.tol_pct2)
            self._set_uti(unit, t_dose_6mev, ref_val=100.0, tol=self.tol_pct2)

            # Linac Monthly
            self._set_uti(unit, t_gantry, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_collimator, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_couch, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_light_rad, ref_val=0.0, tol=self.tol_1mm)
            self._set_uti(unit, t_flatness, ref_val=1.02, tol=self.tol_pct2)
            self._set_uti(unit, t_symmetry, ref_val=1.01, tol=self.tol_pct2)
            self._set_uti(unit, t_kv_mv, ref_val=0.5, tol=self.tol_1mm)
            self._set_uti(unit, t_cbct_align, ref_val=0.0, tol=self.tol_1mm)

            # Linac RTS
            self._set_uti(unit, t_rts_interlock, ref_val=1.0, tol=self.tol_bool, is_bool=True)
            self._set_uti(unit, t_rts_dose, ref_val=100.0, tol=self.tol_pct2)
            self._set_uti(unit, t_rts_laser, ref_val=0.0, tol=self.tol_1mm)

        # CT Sim
        self._set_uti(self.unit_ct, t_ct_door, ref_val=1.0, tol=self.tol_bool, is_bool=True)
        self._set_uti(self.unit_ct, t_ct_laser, ref_val=0.0, tol=self.tol_1mm)
        self._set_uti(self.unit_ct, t_ct_water, ref_val=0.0, tol=self.tol_hu)

        self._set_uti(self.unit_ct, t_ct_water_m, ref_val=0.0, tol=self.tol_hu)
        self._set_uti(self.unit_ct, t_ct_air_m, ref_val=-1000.0, tol=self.tol_hu)
        self._set_uti(self.unit_ct, t_ct_bone_m, ref_val=990.0, tol=self.tol_hu)
        self._set_uti(self.unit_ct, t_ct_acrylic_m, ref_val=120.0, tol=self.tol_hu)
        self._set_uti(self.unit_ct, t_ct_noise_m, ref_val=3.5, tol=self.tol_pct3)
        self._set_uti(self.unit_ct, t_ct_slice_m, ref_val=2.0, tol=self.tol_1mm)
        self._set_uti(self.unit_ct, t_ct_table_m, ref_val=0.1, tol=self.tol_1mm)

    def _set_uti(self, unit, test, ref_val=None, tol=None, is_bool=False):
        ref = None
        if ref_val is not None:
            ref_type = BOOLEAN if is_bool else "numerical"
            ref, _ = Reference.objects.get_or_create(
                name=f"{unit.name} - {test.name} Ref",
                type=ref_type,
                value=ref_val,
                defaults={
                    "created_by": self.user_admin,
                    "modified_by": self.user_admin,
                }
            )

        uti, _ = UnitTestInfo.objects.get_or_create(
            unit=unit,
            test=test,
            defaults={
                "reference": ref,
                "tolerance": tol,
                "active": True,
            }
        )
        if ref or tol:
            uti.reference = ref
            uti.tolerance = tol
            uti.save()
        self.utis[(unit.id, test.id)] = uti
        return uti

    def create_service_and_parts_infrastructure(self):
        self.log("Setting up service areas, parts catalog, suppliers, and storage...", lambda s: s)

        # Service Areas
        sa_accel = ServiceArea.objects.get(name="Accelerator")
        sa_lasers = ServiceArea.objects.get(name="Lasers")
        sa_ctsim = ServiceArea.objects.get(name="CTSim")
        sa_table = ServiceArea.objects.get(name="Treatment Table")

        self.usa_tb1, _ = UnitServiceArea.objects.get_or_create(unit=self.unit_tb1, service_area=sa_accel)
        self.usa_tb1_lasers, _ = UnitServiceArea.objects.get_or_create(unit=self.unit_tb1, service_area=sa_lasers)
        self.usa_versa, _ = UnitServiceArea.objects.get_or_create(unit=self.unit_versa, service_area=sa_accel)
        self.usa_versa_table, _ = UnitServiceArea.objects.get_or_create(unit=self.unit_versa, service_area=sa_table)
        self.usa_ct, _ = UnitServiceArea.objects.get_or_create(unit=self.unit_ct, service_area=sa_ctsim)

        # Service Event Statuses
        self.stat_pending = ServiceEventStatus.objects.get(name="Service Pending")
        self.stat_complete = ServiceEventStatus.objects.get(name="Service Complete")
        self.stat_approved = ServiceEventStatus.objects.get(name="Approved")

        # Service Types
        self.st_preventive = ServiceType.objects.get(name="Preventive")
        self.st_minor = ServiceType.objects.get(name="Minor")
        self.st_extensive = ServiceType.objects.get(name="Extensive")

        # Fault Types
        self.ft_mlc, _ = FaultType.objects.get_or_create(code="MLC-01", defaults={"description": "MLC Leaf Drive Motor / Encoder Stall Interlock"})
        self.ft_vac, _ = FaultType.objects.get_or_create(code="VAC-02", defaults={"description": "Ion Pump / Waveguide Vacuum Pressure Transient"})
        self.ft_chiller, _ = FaultType.objects.get_or_create(code="H2O-01", defaults={"description": "Target Cooling / Chiller Flow Rate Interlock"})
        self.ft_gun, _ = FaultType.objects.get_or_create(code="GUN-01", defaults={"description": "Electron Gun Filament Current Overload"})
        self.ft_img, _ = FaultType.objects.get_or_create(code="IMG-01", defaults={"description": "KV Tube Pre-Heating / Communication Timeout"})

        # Parts Suppliers
        self.sup_varian, _ = Supplier.objects.get_or_create(name="Varian Medical Systems", defaults={"website": "https://www.varian.com", "phone_number": "1-800-555-0199"})
        self.sup_elekta, _ = Supplier.objects.get_or_create(name="Elekta AB", defaults={"website": "https://www.elekta.com", "phone_number": "1-800-555-0188"})
        self.sup_siemens, _ = Supplier.objects.get_or_create(name="Siemens Healthineers", defaults={"website": "https://www.siemens-healthineers.com", "phone_number": "1-800-555-0177"})
        self.sup_standard, _ = Supplier.objects.get_or_create(name="Standard Imaging", defaults={"website": "https://www.standardimaging.com", "phone_number": "1-800-555-0166"})

        # Storage Rooms & Shelves
        room_vault1, _ = Room.objects.get_or_create(name="Vault 1 Tech Room", site=self.clinical_site)
        room_vault2, _ = Room.objects.get_or_create(name="Vault 2 Tech Room", site=self.clinical_site)
        room_physics, _ = Room.objects.get_or_create(name="Physics Laboratory", site=self.clinical_site)

        self.storage_tb1, _ = Storage.objects.get_or_create(room=room_vault1, location="Cabinet A", defaults={"description": "TrueBeam Fast-Replacement Parts"})
        self.storage_versa, _ = Storage.objects.get_or_create(room=room_vault2, location="Rack 2", defaults={"description": "Versa HD Spare Components"})
        self.storage_physics, _ = Storage.objects.get_or_create(room=room_physics, location="Dosimetry Shelf 1", defaults={"description": "Chambers, Cables, and Phantoms"})

        # Part Categories & Parts
        cat_linac, _ = PartCategory.objects.get_or_create(name="Linac Spares")
        cat_dosimetry, _ = PartCategory.objects.get_or_create(name="Dosimetry & QA Equipment")
        cat_lasers, _ = PartCategory.objects.get_or_create(name="Laser Components")

        def create_part(name, part_num, cat, supplier, cost, qty_init, qty_min, storage):
            part, _ = Part.objects.get_or_create(
                part_number=part_num,
                new_or_used="new",
                defaults={
                    "name": name,
                    "part_category": cat,
                    "cost": Decimal(str(cost)),
                    "quantity_min": qty_min,
                }
            )
            PartSupplierCollection.objects.get_or_create(part=part, supplier=supplier, defaults={"part_number": part_num})
            psc, _ = PartStorageCollection.objects.get_or_create(part=part, storage=storage, defaults={"quantity": qty_init})
            psc.quantity = qty_init
            psc.save()
            return part

        self.part_mlc_motor = create_part("Millennium 120 MLC Motor", "MLC-MTR-120", cat_linac, self.sup_varian, 450.00, 4, 2, self.storage_tb1)
        self.part_elekta_motor = create_part("Agility Leaf Drive Motor", "AG-MTR-160", cat_linac, self.sup_elekta, 520.00, 3, 2, self.storage_versa)
        self.part_triax_cable = create_part("Triaxial BNC Chamber Cable 15m", "CBL-TRX-15", cat_dosimetry, self.sup_standard, 280.00, 1, 2, self.storage_physics) # Low stock alert
        self.part_laser_diode = create_part("LAP Red Laser Replacement Diode", "LAP-RED-D6", cat_lasers, self.sup_siemens, 175.00, 5, 2, self.storage_physics)
        self.part_target_oring = create_part("Target Cooling O-Ring Kit", "ORING-TGT-KIT", cat_linac, self.sup_varian, 45.00, 8, 3, self.storage_tb1)

        # Service Event Templates
        self.tpl_beam_steering, _ = ServiceEventTemplate.objects.get_or_create(
            name="Linac Beam Steering & Output Recalibration",
            defaults={
                "service_area": sa_accel,
                "service_type": self.st_minor,
                "problem_description": "Beam symmetry or output constancy drift observed during routine QA.",
                "work_description": "Adjusted magnetron frequency / beam steering parameters and verified RF tuning.",
                "is_review_required": True,
                "created_by": self.user_admin,
                "modified_by": self.user_admin,
            }
        )
        self.tpl_beam_steering.return_to_service_test_lists.set([self.tl_linac_rts])

        self.tpl_ct_tube, _ = ServiceEventTemplate.objects.get_or_create(
            name="CT Tube Seasoning & Detector Calibration",
            defaults={
                "service_area": sa_ctsim,
                "service_type": self.st_preventive,
                "problem_description": "Routine monthly tube conditioning and air calibration.",
                "work_description": "Performed filament seasoning, gain calibration, and air reference scan.",
                "is_review_required": True,
                "created_by": self.user_admin,
                "modified_by": self.user_admin,
            }
        )
        self.tpl_ct_tube.return_to_service_test_lists.set([self.tl_ct_daily])

        # Cross-modality / Polymorphic Templates (Demonstrating Issue #829):
        # 1. Facility-wide Laser Alignment (Cross-modality RTS for Linac & CT)
        self.tpl_laser_align, _ = ServiceEventTemplate.objects.get_or_create(
            name="Laser Alignment & Optical Field Calibration",
            defaults={
                "service_area": sa_lasers,
                "service_type": self.st_preventive,
                "problem_description": "Positioning laser deviation noted during daily QA.",
                "work_description": "Realigned sagittal/coronal/transverse lasers and verified mechanical isocenter crosshair alignment.",
                "is_review_required": True,
                "created_by": self.user_admin,
                "modified_by": self.user_admin,
            }
        )
        self.tpl_laser_align.return_to_service_test_lists.set([self.tl_linac_rts, self.tl_ct_daily])

        # 2. Quarterly Preventative Maintenance (Cross-modality RTS for Linac & CT)
        self.tpl_quarterly_pm, _ = ServiceEventTemplate.objects.get_or_create(
            name="Quarterly Comprehensive PM",
            defaults={
                "service_type": self.st_preventive,
                "problem_description": "Scheduled quarterly engineering preventative maintenance.",
                "work_description": "Completed electrical safety, mechanical checks, interlocks inspection, and dosimetry/imaging verification.",
                "is_review_required": True,
                "created_by": self.user_admin,
                "modified_by": self.user_admin,
            }
        )
        self.tpl_quarterly_pm.return_to_service_test_lists.set([self.tl_linac_monthly, self.tl_ct_monthly])

        # Service Event Schedules
        sch_tb1_pm, _ = ServiceEventSchedule.objects.get_or_create(
            unit_service_area=self.usa_tb1,
            service_event_template=self.tpl_quarterly_pm,
            defaults={
                "frequency": self.freq_monthly,
                "assigned_to": self.grp_engineers,
                "auto_schedule": True,
                "active": True,
            }
        )
        sch_tb1_pm.visible_to.set([self.grp_engineers, self.grp_physics, self.grp_admins])

        sch_versa_pm, _ = ServiceEventSchedule.objects.get_or_create(
            unit_service_area=self.usa_versa,
            service_event_template=self.tpl_quarterly_pm,
            defaults={
                "frequency": self.freq_monthly,
                "assigned_to": self.grp_engineers,
                "auto_schedule": True,
                "active": True,
            }
        )
        sch_versa_pm.visible_to.set([self.grp_engineers, self.grp_physics, self.grp_admins])

    def generate_qa_history(self):
        self.log(f"Generating {self.days} days of rolling QA execution history...", lambda s: s)

        status_approved = TestInstanceStatus.objects.get(slug="Approved")
        status_unreviewed = TestInstanceStatus.objects.get(slug="unreviewed")

        # Generate weekday runs
        for day_idx in range(self.days, -1, -1):
            dt_morning = self.rel_dt(day_idx, hour=7, minute=15)
            # Skip weekends for routine daily QA
            if dt_morning.weekday() >= 5:
                continue

            # Review status: past days are approved, last 2 days unreviewed
            is_approved = day_idx >= 3
            ti_status = status_approved if is_approved else status_unreviewed
            reviewer = self.user_jane if is_approved else None

            # --- Linac 1 Daily ---
            self._generate_linac_daily_instance(self.unit_tb1, self.tl_linac_daily, self.utc_tb1_daily, dt_morning, ti_status, reviewer, day_idx)

            # --- Linac 2 Daily ---
            self._generate_linac_daily_instance(self.unit_versa, self.tl_linac_daily, self.utc_versa_daily, dt_morning + timedelta(minutes=15), ti_status, reviewer, day_idx)

            # --- CT Sim Daily ---
            self._generate_ct_daily_instance(self.unit_ct, self.tl_ct_daily, self.utc_ct_daily, dt_morning + timedelta(minutes=30), ti_status, reviewer, day_idx)

            # Monthly QA runs on roughly day 75, day 45, day 15
            if day_idx in (75, 45, 15):
                dt_monthly = self.rel_dt(day_idx, hour=17, minute=0)
                self._generate_linac_monthly_instance(self.unit_tb1, self.tl_linac_monthly, self.utc_tb1_monthly, dt_monthly, status_approved, self.user_jane)
                self._generate_linac_monthly_instance(self.unit_versa, self.tl_linac_monthly, self.utc_versa_monthly, dt_monthly + timedelta(hours=1), status_approved, self.user_jane)
                self._generate_ct_monthly_instance(self.unit_ct, self.tl_ct_monthly, self.utc_ct_monthly, dt_monthly + timedelta(hours=2), status_approved, self.user_jane)

        # Generate 1 in-progress test list instance for today on Linac 2 to test resuming sessions
        dt_today = self.rel_dt(0, hour=8, minute=30)
        tli_inprog = TestListInstance.objects.create(
            unit_test_collection=self.utc_versa_daily,
            test_list=self.tl_linac_daily,
            work_started=dt_today,
            work_completed=None,
            modified=dt_today,
            created_by=self.user_sarah,
            modified_by=self.user_sarah,
            in_progress=True,
            all_reviewed=False,
        )
        tests = {t.slug: t for t in self.tl_linac_daily.tests.all()}
        for t_slug, is_bool, val in [("door_interlock", True, 1.0), ("beam_on_indicator", True, 1.0), ("temp", False, 22.0), ("press", False, 101.4)]:
            test = tests[t_slug]
            uti = self.utis[(self.unit_versa.id, test.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=tli_inprog,
                created_by=self.user_sarah,
                modified_by=self.user_sarah,
                status=status_unreviewed,
                value=val,
                reference=uti.reference,
                tolerance=uti.tolerance,
                work_started=dt_today,
                work_completed=dt_today,
            )
            ti.calculate_pass_fail()
            ti.save()

    def _generate_linac_daily_instance(self, unit, tl, utc, dt_completed, status, reviewer, day_idx):
        tli = TestListInstance.objects.create(
            unit_test_collection=utc,
            test_list=tl,
            work_started=dt_completed - timedelta(minutes=18),
            work_completed=dt_completed,
            modified=dt_completed,
            created_by=self.user_sarah,
            modified_by=self.user_sarah,
            reviewed_by=reviewer,
            reviewed=dt_completed + timedelta(hours=2) if reviewer else None,
            all_reviewed=bool(reviewer),
            in_progress=False,
        )

        # Temp & Press with seasonal/daily slight variation
        temp = round(21.5 + random.uniform(-0.8, 1.2), 1)
        press = round(101.1 + random.uniform(-0.6, 0.7), 1)
        ktp = ((273.15 + temp) / 295.15) * (101.33 / press)

        # Check for injected deviations
        laser_offset = 0.0
        dose_mult = 1.0
        comment_tli = ""
        ti_laser_comment = ""

        if unit == self.unit_tb1 and day_idx == 42:
            # Action level excursion on day 42
            dose_mult = 1.034
            comment_tli = "6MV Output high on initial morning beam check (+3.4%). Contacted physics."
        elif unit == self.unit_versa and day_idx == 22:
            # Tolerance warning on day 22
            laser_offset = 1.4
            ti_laser_comment = "Lateral laser reading +1.4mm from phantom crosshair. Within clinical tolerance."

        # Tests
        tests = {t.slug: t for t in tl.tests.all()}

        # Values
        raw_6mv = round((100.0 * dose_mult / (ktp * 1.002)) + random.gauss(0, 0.2), 2)
        dose_6mv = round(raw_6mv * ktp * 1.002, 2)
        raw_10mv = round((100.0 / (ktp * 0.998)) + random.gauss(0, 0.2), 2)
        dose_10mv = round(raw_10mv * ktp * 0.998, 2)
        dose_6mev = round(100.0 + random.gauss(0, 0.3), 2)

        def add_ti(test_slug, val=None, str_val="", is_bool=False, cmt=""):
            test = tests[test_slug]
            uti = self.utis[(unit.id, test.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=tli,
                created_by=self.user_sarah,
                modified_by=self.user_sarah,
                status=status,
                value=float(val) if val is not None else (1.0 if is_bool else None),
                string_value=str_val,
                reference=uti.reference,
                tolerance=uti.tolerance,
                comment=cmt,
                work_started=tli.work_started,
                work_completed=tli.work_completed,
            )
            ti.calculate_pass_fail()
            ti.save()

        add_ti("door_interlock", is_bool=True)
        add_ti("beam_on_indicator", is_bool=True)
        add_ti("temp", val=temp)
        add_ti("press", val=press)
        add_ti("ktp", val=round(ktp, 4))
        add_ti("laser_x", val=round(random.gauss(0, 0.2) + laser_offset, 2), cmt=ti_laser_comment)
        add_ti("laser_y", val=round(random.gauss(0, 0.2), 2))
        add_ti("laser_z", val=round(random.gauss(0, 0.2), 2))
        add_ti("odi_100", val=round(100.0 + random.gauss(0, 0.15), 1))
        add_ti("raw_6mv", val=raw_6mv)
        add_ti("dose_6mv", val=dose_6mv)
        add_ti("raw_10mv", val=raw_10mv)
        add_ti("dose_10mv", val=dose_10mv)
        add_ti("dose_6mev", val=dose_6mev)

        if comment_tli:
            Comment.objects.create(
                content_object=tli,
                site=self.site,
                user=self.user_sarah,
                user_name=self.user_sarah.username,
                comment=comment_tli,
                submit_date=tli.work_completed,
            )

    def _generate_ct_daily_instance(self, unit, tl, utc, dt_completed, status, reviewer, day_idx):
        tli = TestListInstance.objects.create(
            unit_test_collection=utc,
            test_list=tl,
            work_started=dt_completed - timedelta(minutes=10),
            work_completed=dt_completed,
            modified=dt_completed,
            created_by=self.user_sarah,
            modified_by=self.user_sarah,
            reviewed_by=reviewer,
            reviewed=dt_completed + timedelta(hours=2) if reviewer else None,
            all_reviewed=bool(reviewer),
            in_progress=False,
        )
        tests = {t.slug: t for t in tl.tests.all()}

        water_hu = round(random.gauss(0, 1.2), 1)
        cmt = ""
        if day_idx == 12:
            water_hu = 4.8
            cmt = "Water HU value slightly elevated (+4.8 HU) but within tolerance (-5 to +5 HU)."

        def add_ti(test_slug, val=None, is_bool=False, comment=""):
            test = tests[test_slug]
            uti = self.utis[(unit.id, test.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=tli,
                created_by=self.user_sarah,
                modified_by=self.user_sarah,
                status=status,
                value=float(val) if val is not None else (1.0 if is_bool else None),
                reference=uti.reference,
                tolerance=uti.tolerance,
                comment=comment,
                work_started=tli.work_started,
                work_completed=tli.work_completed,
            )
            ti.calculate_pass_fail()
            ti.save()

        add_ti("ct_door_interlock", is_bool=True)
        add_ti("ct_laser_align", val=round(random.gauss(0, 0.25), 2))
        add_ti("ct_water_hu", val=water_hu, comment=cmt)

    def _generate_linac_monthly_instance(self, unit, tl, utc, dt_completed, status, reviewer):
        tli = TestListInstance.objects.create(
            unit_test_collection=utc,
            test_list=tl,
            work_started=dt_completed - timedelta(minutes=45),
            work_completed=dt_completed,
            modified=dt_completed,
            created_by=self.user_mark,
            modified_by=self.user_mark,
            reviewed_by=reviewer,
            reviewed=dt_completed + timedelta(hours=1),
            all_reviewed=True,
            in_progress=False,
        )
        tests = {t.slug: t for t in tl.tests.all()}

        def add_ti(test_slug, val):
            test = tests[test_slug]
            uti = self.utis[(unit.id, test.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=tli,
                created_by=self.user_mark,
                modified_by=self.user_mark,
                status=status,
                value=float(val),
                reference=uti.reference,
                tolerance=uti.tolerance,
                work_started=tli.work_started,
                work_completed=tli.work_completed,
            )
            ti.calculate_pass_fail()
            ti.save()

        add_ti("gantry_rot", round(random.gauss(0, 0.2), 2))
        add_ti("collimator_rot", round(random.gauss(0, 0.2), 2))
        add_ti("couch_pos", round(random.gauss(0, 0.2), 2))
        add_ti("light_rad_field", round(random.gauss(0, 0.2), 2))
        add_ti("flatness_6mv", round(1.02 + random.gauss(0, 0.003), 3))
        add_ti("symmetry_6mv", round(1.01 + random.gauss(0, 0.003), 3))
        add_ti("kv_mv_iso", round(0.48 + random.gauss(0, 0.04), 2))
        add_ti("cbct_align", round(random.gauss(0, 0.15), 2))

    def _generate_ct_monthly_instance(self, unit, tl, utc, dt_completed, status, reviewer):
        tli = TestListInstance.objects.create(
            unit_test_collection=utc,
            test_list=tl,
            work_started=dt_completed - timedelta(minutes=40),
            work_completed=dt_completed,
            modified=dt_completed,
            created_by=self.user_alex,
            modified_by=self.user_alex,
            reviewed_by=reviewer,
            reviewed=dt_completed + timedelta(hours=1),
            all_reviewed=True,
            in_progress=False,
        )
        tests = {t.slug: t for t in tl.tests.all()}

        def add_ti(test_slug, val):
            test = tests[test_slug]
            uti = self.utis[(unit.id, test.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=tli,
                created_by=self.user_alex,
                modified_by=self.user_alex,
                status=status,
                value=float(val),
                reference=uti.reference,
                tolerance=uti.tolerance,
                work_started=tli.work_started,
                work_completed=tli.work_completed,
            )
            ti.calculate_pass_fail()
            ti.save()

        add_ti("ct_hu_water_m", round(random.gauss(0, 0.8), 1))
        add_ti("ct_hu_air_m", round(-1000.0 + random.gauss(0, 1.5), 1))
        add_ti("ct_hu_bone_m", round(990.0 + random.gauss(0, 2.1), 1))
        add_ti("ct_hu_acrylic_m", round(120.0 + random.gauss(0, 1.2), 1))
        add_ti("ct_noise_m", round(3.48 + random.gauss(0, 0.08), 2))
        add_ti("ct_slice_m", round(2.0 + random.gauss(0, 0.05), 2))
        add_ti("ct_table_m", round(0.1 + random.gauss(0, 0.03), 2))

    def generate_service_and_fault_history(self):
        self.log("Creating realistic service events, maintenance history, faults, and RTS records...", lambda s: s)

        # Event 1: Linac 1 Quarterly PM (Day 40)
        dt_pm = self.rel_dt(40, hour=18, minute=0)
        se_pm = ServiceEvent.objects.create(
            unit_service_area=self.usa_tb1,
            service_type=self.st_preventive,
            service_status=self.stat_approved,
            datetime_created=dt_pm - timedelta(hours=8),
            datetime_service=dt_pm,
            problem_description="Scheduled 100-hour Quarterly Preventative Maintenance.",
            work_description="Cleaned waveguide window, checked chiller cooling lines, lubricated gantry bearings, verified beam interlocks and safety switches.",
            safety_precautions="Lock-out tag-out applied during interior cabinet cleaning.",
            duration_service_time=timedelta(hours=6, minutes=30),
            duration_lost_time=timedelta(hours=2),
            user_created_by=self.user_dave,
            is_review_required=True,
            is_active=True,
        )
        Hours.objects.create(service_event=se_pm, user=self.user_dave, time=timedelta(hours=6, minutes=30))

        # RTS QA for PM
        rts_tli_pm = TestListInstance.objects.create(
            unit_test_collection=self.utc_tb1_rts,
            test_list=self.tl_linac_rts,
            work_started=dt_pm + timedelta(minutes=10),
            work_completed=dt_pm + timedelta(minutes=35),
            modified=dt_pm + timedelta(minutes=35),
            created_by=self.user_mark,
            modified_by=self.user_mark,
            reviewed_by=self.user_jane,
            reviewed=dt_pm + timedelta(hours=1),
            all_reviewed=True,
            in_progress=False,
        )
        for t in self.tl_linac_rts.tests.all():
            uti = self.utis[(self.unit_tb1.id, t.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=rts_tli_pm,
                created_by=self.user_mark,
                modified_by=self.user_mark,
                status=TestInstanceStatus.objects.get(slug="Approved"),
                value=1.0 if t.is_boolean() else (100.1 if "output" in t.slug else 0.1),
                reference=uti.reference,
                tolerance=uti.tolerance,
                work_started=rts_tli_pm.work_started,
                work_completed=rts_tli_pm.work_completed,
            )
            ti.calculate_pass_fail()
            ti.save()

        ReturnToServiceQA.objects.create(
            unit_test_collection=self.utc_tb1_rts,
            test_list_instance=rts_tli_pm,
            service_event=se_pm,
            user_assigned_by=self.user_dave,
            datetime_assigned=dt_pm,
        )

        # Event 2: Linac 2 MLC Leaf Motor Replacement (Day 25)
        dt_mlc = self.rel_dt(25, hour=14, minute=30)
        fault_mlc = Fault.objects.create(
            unit=self.unit_versa,
            modality=self.modalities["6MV"],
            occurred=dt_mlc - timedelta(hours=3),
            created_by=self.user_sarah,
            modified_by=self.user_sarah,
        )
        fault_mlc.fault_types.set([self.ft_mlc])

        se_mlc = ServiceEvent.objects.create(
            unit_service_area=self.usa_versa,
            service_type=self.st_extensive,
            service_status=self.stat_approved,
            datetime_created=dt_mlc - timedelta(hours=2),
            datetime_service=dt_mlc,
            problem_description="MLC Leaf #34 motor stall interlock during patient treatment preparation.",
            work_description="Replaced Agility leaf #34 motor and optical encoder assembly. Re-calibrated leaf positions.",
            safety_precautions="Couch rotated 90 degrees and beam key disabled during head access.",
            duration_service_time=timedelta(hours=3, minutes=15),
            duration_lost_time=timedelta(hours=1, minutes=45),
            user_created_by=self.user_dave,
            is_review_required=True,
            is_active=True,
        )
        fault_mlc.related_service_events.set([se_mlc])
        Hours.objects.create(service_event=se_mlc, user=self.user_dave, time=timedelta(hours=3, minutes=15))
        PartUsed.objects.create(service_event=se_mlc, part=self.part_elekta_motor, from_storage=self.storage_versa, quantity=1)

        # RTS QA for MLC repair
        rts_tli_mlc = TestListInstance.objects.create(
            unit_test_collection=self.utc_versa_rts,
            test_list=self.tl_linac_rts,
            work_started=dt_mlc + timedelta(minutes=15),
            work_completed=dt_mlc + timedelta(minutes=40),
            modified=dt_mlc + timedelta(minutes=40),
            created_by=self.user_jane,
            modified_by=self.user_jane,
            reviewed_by=self.user_jane,
            reviewed=dt_mlc + timedelta(hours=1),
            all_reviewed=True,
            in_progress=False,
        )
        for t in self.tl_linac_rts.tests.all():
            uti = self.utis[(self.unit_versa.id, t.id)]
            ti = TestInstance(
                unit_test_info=uti,
                test_list_instance=rts_tli_mlc,
                created_by=self.user_jane,
                modified_by=self.user_jane,
                status=TestInstanceStatus.objects.get(slug="Approved"),
                value=1.0 if t.is_boolean() else (99.9 if "output" in t.slug else 0.0),
                reference=uti.reference,
                tolerance=uti.tolerance,
                work_started=rts_tli_mlc.work_started,
                work_completed=rts_tli_mlc.work_completed,
            )
            ti.calculate_pass_fail()
            ti.save()

        ReturnToServiceQA.objects.create(
            unit_test_collection=self.utc_versa_rts,
            test_list_instance=rts_tli_mlc,
            service_event=se_mlc,
            user_assigned_by=self.user_dave,
            datetime_assigned=dt_mlc,
        )

        # Event 3: CT Sim Laser Realignment (Day 15)
        dt_ct_serv = self.rel_dt(15, hour=17, minute=30)
        ServiceEvent.objects.create(
            unit_service_area=self.usa_ct,
            service_type=self.st_minor,
            service_status=self.stat_approved,
            datetime_created=dt_ct_serv - timedelta(hours=1),
            datetime_service=dt_ct_serv,
            problem_description="Right wall LAP laser deviated +1.5mm during monthly QA verification.",
            work_description="Adjusted LAP laser micrometric prism and locked mounting bolts. Crosshair aligned to phantom isocenter.",
            duration_service_time=timedelta(hours=1, minutes=15),
            duration_lost_time=timedelta(0),
            user_created_by=self.user_dave,
            is_review_required=True,
            is_active=True,
        )

        # Event 4: Active / Open Service Event on Linac 1 (Day 1)
        dt_active = self.rel_dt(1, hour=16, minute=0)
        fault_chiller = Fault.objects.create(
            unit=self.unit_tb1,
            modality=self.modalities["6MV"],
            occurred=dt_active - timedelta(minutes=30),
            created_by=self.user_sarah,
            modified_by=self.user_sarah,
        )
        fault_chiller.fault_types.set([self.ft_chiller])

        se_active = ServiceEvent.objects.create(
            unit_service_area=self.usa_tb1,
            service_type=self.st_minor,
            service_status=self.stat_pending,
            datetime_created=dt_active,
            datetime_service=dt_active,
            problem_description="Target water cooling flow rate warning interlock during afternoon treatment.",
            work_description="Investigating water strainer filter and temperature sensors.",
            user_created_by=self.user_dave,
            is_review_required=True,
            is_active=True,
        )
        fault_chiller.related_service_events.set([se_active])

    def create_reports_and_schedules(self):
        self.log("Configuring Saved Reports, clinical report notes, and email schedules...", lambda s: s)

        # 1. Weekly Daily QA Compliance Report
        rep_weekly = SavedReport.objects.create(
            title="Weekly Daily QA Compliance & Sign-off",
            report_type="testlistinstance_summary",
            report_format="pdf",
            paper_size="letter",
            include_signature=True,
            include_logo=True,
            filters={"unit": [self.unit_tb1.id, self.unit_versa.id, self.unit_ct.id], "frequency": [self.freq_daily.id]},
            created_by=self.user_jane,
            modified_by=self.user_jane,
        )
        rep_weekly.visible_to.set([self.grp_physics, self.grp_rtts, self.grp_admins])

        ReportNote.objects.create(
            report=rep_weekly,
            heading="Department QA Sign-off Protocol",
            content="This report summarizes daily machine checks in accordance with AAPM TG-142 compliance guidelines. All flagged tolerances must have written physicist commentary."
        )

        # 2. Output Constancy 90-Day Trending
        rep_trend = SavedReport.objects.create(
            title="Linac Photon & Electron Output 90-Day Constancy",
            report_type="testinstance_details",
            report_format="xlsx",
            paper_size="letter",
            include_signature=False,
            include_logo=True,
            filters={"unit": [self.unit_tb1.id, self.unit_versa.id]},
            created_by=self.user_jane,
            modified_by=self.user_jane,
        )
        rep_trend.visible_to.set([self.grp_physics, self.grp_admins])

        # 3. Machine Downtime & Service Hours
        rep_service = SavedReport.objects.create(
            title="Monthly Equipment Downtime & Service Hours",
            report_type="service-times",
            report_format="pdf",
            paper_size="letter",
            include_signature=True,
            include_logo=True,
            filters={"unit": [self.unit_tb1.id, self.unit_versa.id, self.unit_ct.id]},
            created_by=self.user_dave,
            modified_by=self.user_dave,
        )
        rep_service.visible_to.set([self.grp_engineers, self.grp_physics, self.grp_admins])

        # 4. Machine Faults & Subsystem Reliability Report
        rep_faults = SavedReport.objects.create(
            title="Machine Fault Log & Interlock Reliability",
            report_type="fault_summary",
            report_format="pdf",
            paper_size="letter",
            include_signature=False,
            include_logo=True,
            filters={},
            created_by=self.user_jane,
            modified_by=self.user_jane,
        )
        rep_faults.visible_to.set([self.grp_physics, self.grp_engineers, self.grp_admins])

        # 5. Schedules
        # Schedule Weekly Compliance Report every Monday at 07:00 AM
        ReportSchedule.objects.create(
            report=rep_weekly,
            schedule="DTSTART:20240101T070000Z\nRRULE:FREQ=WEEKLY;BYDAY=MO",
            time=time(7, 0),
            created_by=self.user_jane,
            modified_by=self.user_jane,
        ).groups.set([self.grp_physics])

        # Schedule Monthly Service Report on the 1st of every month at 08:00 AM
        ReportSchedule.objects.create(
            report=rep_service,
            schedule="DTSTART:20240101T080000Z\nRRULE:FREQ=MONTHLY;BYMONTHDAY=1",
            time=time(8, 0),
            created_by=self.user_dave,
            modified_by=self.user_dave,
        ).groups.set([self.grp_engineers, self.grp_physics])
