import datetime
import django
import random
from qatrack.units.models import UnitType, Unit, Modality
from qatrack.qa import models

import create_sample_db

tomo_morning = (
    ("Sagittal Bore Red-Green DTA [mm]","sag_bore_dta","mechanical_safety"),
    ("Sagittal Ceiling Red-Green DTA [mm]","sag_ceil_dta","mechanical_safety"),
    ("Right Transverse Red-Green DTA [mm]","rt_trans_dta","mechanical_safety"),
    ("Right Coronal Red-Green DTA [mm]","rt_cor_dta","mechanical_safety"),
    ("Left Transverse Red-Green DTA [mm]","lt_trans_dta","mechanical_safety"),
    ("Left Coronal Red-Green DTA [mm]","lt_cor_dta","mechanical_safety"),
    ("PCP Couch X","pcp_couch_x","mechanical_safety"),
    ("PCP Couch Y","pcp_couch_y","mechanical_safety"),
    ("PCP Couch Z","pcp_couch_z","mechanical_safety"),
    ("Solid Water Temperature [degrees Celsius]","t_solid_water","dosimetry","mechanical_safety"),
    ("Air Pressure (mm Hg)","air_pressure","dosimetry","mechanical_safety"),
    ("Thermal Correction for Barometer [mm Hg]","thermal_corr","dosimetry","mechanical_safety"),
    ("FtP","ftp","dosimetry","composite"),
    ("Couch in the bore PCP  Y Value","couch_in_y","mechanical_safety"),
    ("Couch in the bore PCP  Z Value","couch_in_z","mechanical_safety"),
    ("Couch in Bore Control Console Y Value","couch_in_y_console","mechanical_safety"),
    ("Couch in Bore Control Console Z Value","couch_in_z_console","mechanical_safety"),
    ("Reading from MVCT [pC]","mvct_read","dosimetry","mechanical_safety"),
    ("Couch Retracted Console Y Value","couch_ret_y_console","mechanical_safety"),
    ("Couch Retracted Console Z Value","couch_ret_z_console","mechanical_safety"),
    ("X shift required by manual registration ","x_shift_req", "mechanical_safety"),
    ("Y shift required by manual registration ","y_shift_req","mechanical_safety"),
    ("Z shift required by manual registration ","z_shift_req","mechanical_safety"),
    ("Post Shift Sag red laser - DTA [mm]","sag_red_dta_post_shift","mechanical_safety"),
    ("Post Shift Pt RT Transverse Red Laser - DTA [mm]","rt_trans_red_dta_post_shift","mechanical_safety"),
    ("Post Shift Pt RT Coronal Red Laser - DTA [mm]","rt_cor_red_dta_post_shift","mechanical_safety"),
    ("Post Shift Pt LT Transverse Red Laser - DTA [mm]","lt_trans_red_dta_post_shift","mechanical_safety"),
    ("Post Shift Pt LT Coronal Red Laser - DTA [mm]","lt_cor_red_dta_post_shift","mechanical_safety"),
    ("Post Shift green sagittal laser   DTA [mm]","sag_green_dta_post_shift","mechanical_safety"),
    ("Post Shift green coronal laser   DTA [mm]","cor_green_post_shift","mechanical_safety"),
    ("Post Shift green transverse laser   DTA [mm]","trans_green_post_shift","mechanical_safety"),
    ("Post Shift PCP Couch X display","pcp_couch_x_ps","mechanical_safety"),
    ("Post Shift PCP Couch Y display","pcp_couch_y_ps","mechanical_safety"),
    ("Post Shift PCP Couch Z display","pcp_couch_z_ps","mechanical_safety"),
    ("Post 2nd scan  - X shift required by registration","x_shift_req_p2s","mechanical_safety"),
    ("Post 2nd scan  - Y shift required by registration","y_shift_req_p2s","mechanical_safety"),
    ("Post 2nd scan  - Z shift required by registration","z_shift_req_p2s","mechanical_safety"),
    ("Electrometer Reading -  2 Min. at 15mm [nC]","reading_2min","dosimetry"),
    ("Control Console Display Rate 1","display_rate1_2min","dosimetry"),
    ("Control Console Display Rate 2","display_rate2_2min","dosimetry"),
    ("Dose 2 minute dmax","dose_2min","dosimetry","composite"),
    ("Electrometer Reading  -  30 Sec. at 15mm [nC]","reading_30s","dosimetry"),
    ("Control Console Display Rate 1","display_rate1_30s","dosimetry"),
    ("Control Console Display Rate 2","display_rate2_30s","dosimetry"),
    ("Dose 30s Dmax","dosimetry","dose_30s","composite"),
    ("Electrometer Reading  -  30 Sec. at 200mm [nC]","reading_30s_d20","dosimetry"),
    ("Control Console Display Rate 1","display_rate1_30s_d20","dosimetry"),
    ("Control Console Display Rate 2","display_rate2_30s_d20","dosimetry"),
    ("Dose 30s D20","dosimetry","dose_30s_d20","composite"),
    ("Output Consistency 2min delivery","consistency_2min","dosimetry","composite"),
    ("Output consistency 30 sec delivery","consistency_30s","dosimetry","composite"),
    ("2 min to 30 sec dose consistency","consistency_2min_to_30s","dosimetry","composite"),
    ("Ratio 200 mm to 15 mm depth","dose_ration_d20_dmax","dosimetry","composite"),
)


#----------------------------------------------------------------------
def create_task_list_items():
    """"""
    user = django.contrib.auth.models.User.objects.get(pk=1)
    for test in tomo_morning:
        if len(test) > 3:
            continue
        else:
            tli = models.Test(
                name = test[0],
                slug = test[1],
                description = test[0],
                procedure = "",
                task_type = "numerical",
                category = models.Category.objects.get(slug=test[2]),
                created_by = user,
                modified_by = user,
            )
            try:
                tli.save()
            except django.db.IntegrityError:
                pass



if __name__ == "__main__":
    create_sample_db.create_modalities(),
    create_sample_db.create_unit_types()
    create_sample_db.create_units()
    create_sample_db.create_users()
    create_sample_db.create_tolerances()
    create_sample_db.create_categories()
    create_task_list_items()