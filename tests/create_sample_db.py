import django
from qatrack.units.models import UnitType, Unit, Modality
from qatrack.qa import models
def create_modalities():
    modality_types = (
        ("photon", [6, 10, 15, 18]),
        ("electron", [6, 9, 11, 12, 13, 15, 17]),
    )
    for t,energies in modality_types:
        for e in energies:
            m = Modality(type=t,energy=e)
            try:
                m.save()
            except django.db.utils.IntegrityError:
                pass


#----------------------------------------------------------------------
def create_unit_types():
    unit_types = (
        ("Tomotherapy","Accuray", "Hi Art"),
        ("BM", "Elekta", "Beam Modulator"),
        ("Synergy", "Elekta", "Synergy"),
        ("Primus", "Siemens", "Primus"),        
        ("Cyberknife", "Accuray", "Cyberknife"), 
    )
    
    for name,vendor, model in unit_types:
        ut = UnitType(name=name,vendor=vendor,model=model)
        try:
            ut = ut.save()
        except django.db.utils.IntegrityError:
            pass

#----------------------------------------------------------------------
def create_units():
    units = (
        (1,"Unit01","Tomotherapy",[6],[]),
        (2,"Unit02","Tomotherapy",[6],[]),
        (4,"Unit04","Primus",[6,18],[6,9,11,13,17]),
        (7,"Unit07","Primus",[6,18],[6,9,11,13,17]),
        (5,"Unit05","Synergy",[6,10],[]),
        (6,"Unit06","Synergy",[6,10],[]),
        (21,"Unit21","Synergy",[6,10],[]),
        (22,"Unit22","Synergy",[6,10],[]),
        (23,"Unit23","Synergy",[6,10],[]),
        (8,"Unit08","BM",[6,15],[]),
        (9,"Unit09","BM",[6,15],[]),
        (11,"Cyberknife","Cyberknife",[6],[]),
    )
    
    for num, name, utype, xe, ee in units:
        unit = Unit(number=num, name=name)
        unit.type = UnitType.objects.get(name=utype)
        try:
            unit.save()
            unit.modalities.add(*(Modality.objects.filter(type="photon").filter(energy__in=xe)))
            unit.modalities.add(*(Modality.objects.filter(type="electron").filter(energy__in=ee)))
            unit.save()           
        except django.db.utils.IntegrityError:
            pass
 
#----------------------------------------------------------------------
def create_users():
    users = (
        ("bobw","Bob", "Wilson"),
        ("sallyt","Sally","Thomson"),
    )
    for uname,fn,ln in users:
        user = django.contrib.auth.models.User(username=uname,first_name=fn, last_name=ln)
        try:
            user.save()
        except django.db.utils.IntegrityError:
            pass
#----------------------------------------------------------------------
def create_references():
    sally = django.contrib.auth.models.User.objects.get(username="sallyt")
    bob = django.contrib.auth.models.User.objects.get(username="bobw")
    refs = (
        ("Yes Expected", "yes_no",1,sally),
        ("No Expected", "yes_no",0,sally),
        ("Zero Expected", "numerical",0,sally),
        ("One Expected", "numerical", 1, bob),
        ("Output reference","numerical",100,bob),
        ("Standard T (deg C)", "numerical", 22,bob),
        ("Standard P (mmHg)", "numerical", 760, bob),
    )
    
    for name, rtype, value, user in refs:
        r = models.Reference(name=name,ref_type=rtype, value=value, created_by=user, modified_by=user)
        try:
            r.save()
        except django.db.IntegrityError:
            pass
        
#----------------------------------------------------------------------
def create_tolerances():
    sally = django.contrib.auth.models.User.objects.get(username="sallyt")
    bob = django.contrib.auth.models.User.objects.get(username="bobw")

    tolerances = (
        ("+- 2mm/3mm", "absolute",-3,-2,2,3,bob),
        ("+2mm/3mm", "absolute",0,0,2,3,bob),
        ("+- 2%/3%", "percentage", -3,-2,2,3, bob),
        ("+2%/3%", "percentage", 0,0,2,3, bob),
        ("+- 2/2", "absolute",-2,-2,2,2,sally),
        ("Temperature Tol", "absolute", -10, -10,10,10,sally),
        ("Pressure Tol", "absolute", -30, -30,30,30,sally),            
    )

    for name,ttype, al, tl, th, ah, user in tolerances:
        t = models.Tolerance(name=name,type=ttype,act_low=al, tol_low=tl, tol_high=th, act_high=ah, created_by=user, modified_by=user)
        try:
            t.save()
        except django.db.IntegrityError:
            pass
        
#----------------------------------------------------------------------
def create_categories():
    categories = (
        ("Dosimetry", "dosimetry", "Anything related to do with dosimetry"),
        ("Mechanical & Safety", "mechanical_safety", "Lasers, couch motion, e-stops, etc"),
    )
    
    for name, slug, desc in categories:
        c = models.Category(name=name,slug=slug,description=desc)
        try:
            c.save()
        except django.db.IntegrityError:
            pass
        
    
#----------------------------------------------------------------------
def create_task_lists():
    units = dict([(u.number,u) for u in Unit.objects.all()])
    sally = django.contrib.auth.models.User.objects.get(username="sallyt")
    bob = django.contrib.auth.models.User.objects.get(username="bobw")
        
    task_lists = (
        ("Tomo morning","tomo_morning","Morning QA", "daily", True, [units[1],units[2]],sally),
        ("Tomo electronics morning","tomo_elecronics_morning","Electronics morning QA", "daily", True, [units[1],units[2]],sally),
        ("Tomo therapists morning","tomo_therapists_morning","Therapists morning QA", "daily", True, [units[1],units[2]],bob),                
        ("Elekta morning QA","elekta_morning_qa","QA for Elekta machines", "daily", True, [units[x] for x in (5,6,8,9,21,22,23)],bob),
        ("Siemens morning QA","siemens_morning_qa","QA for Siemens machines", "daily", True, [units[x] for x in (4,7)],bob),        
    )
        
    for name,slug,desc,freq,act,units,user in task_lists:
        for unit in units:
            tl = models.TaskList(
                name="%s %s"%(unit.name,name),
                slug="%s_%s"%(unit.name,slug),
                description=desc,
                frequency=freq,
                unit = unit,
                created_by=user,
                modified_by=user,                
            )
            
            try:
                tl.save()
            except django.db.IntegrityError:
                pass
            
#----------------------------------------------------------------------
def create_task_list_items():
    sally = django.contrib.auth.models.User.objects.get(username="sallyt")
    bob = django.contrib.auth.models.User.objects.get(username="bobw")
    dosimetry = models.Category.objects.get(slug="dosimetry")
    mech = models.Category.objects.get(slug="mechanical_safety")
    
    task_list_items = (
        ("Temperature", "temperature", "Ambient Temperature", "Measure temperature","simple",None,dosimetry,sally),
        ("Pressure", "pressure", "Air Temperature", "Measure pressure","simple",None,dosimetry,sally),
        ("Ftp","ftp","Temperature Pressure Correction","Calculated","composite","result= (273.2+temperature)/(273.2+22.)*(101.33/pressure)",dosimetry,sally),
        ("Output","output","Machine Output","Deliver 100MU","simple",None,dosimetry,sally),
        ("Sag Laser DTA", "sag_laser", "Sagittal laser agreement", "measure dta", "simple", None, mech, bob),        
    )
    
    for name, slug, desc, proc, ttype,calc, cat,user in task_list_items:
        if models.TaskListItem.objects.filter(short_name=slug).count()>0:
            continue
        tli = models.TaskListItem(
            name=name,
            short_name=slug,
            description=desc,
            procedure=proc,
            task_type=ttype,
            calculation_procedure=calc,
            category=cat,
            created_by=user,
            modified_by=user,            
        )
        try:
            tli.save()
        except django.db.IntegrityError:
            pass
#----------------------------------------------------------------------
def create_memberships():
    tomos = Unit.objects.filter(type__name="Tomotherapy")
    task_lists = models.TaskList.objects.filter(unit__in=tomos)
        
    
    members = (
        ("temperature", "Standard T (deg C)", "Temperature Tol"),
        ("pressure", "Standard P (mmHg)", "Pressure Tol"),
        ("ftp", "One Expected", "+- 2%/3%"),
        ("output","Output reference","+- 2%/3%"),        
        ("sag_laser","Zero Expected", "+- 2mm/3mm"),
    )
    
    for order, (item_name, ref_name, tol_name) in enumerate(members):
        item = models.TaskListItem.objects.get(short_name=item_name)
        ref = models.Reference.objects.get(name=ref_name)
        tol = models.Tolerance.objects.get(name=tol_name)
    
        for task_list in task_lists:
            m = models.TaskListMembership(
                task_list_item=item,
                task_list=task_list,
                task_list_item_order = order,
                reference = ref,
                tolerance=tol,
                active=True
                
            )
            try:
                m.save()
            except django.db.IntegrityError:
                pass 
    

    
        
    
if __name__ == "__main__":
    create_modalities()
    create_unit_types()
    create_units()
    create_users()
    create_references()
    create_tolerances()
    create_categories()
    create_task_lists()
    create_task_list_items()
    create_memberships()
    
    print models.TaskListMembership.objects.all()