
import getpass
import pyodbc
import re
import warnings

from django.conf import settings as qat_settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils import timezone

from qatrack.service_log import models as sl_models
from qatrack.units import models as u_models
from qatrack.qa import models as qa_models

from ... import accel_migration_settings as amt_settings

use_ldap = amt_settings.USE_LDAP
if use_ldap:
    import ldap

warnings.filterwarnings("ignore", category=RuntimeWarning)


def user_select_from_list_of_numbers(message, num_list):

    to_return = -1
    while to_return == -1:
        try:
            to_return = input('\n>>> ' + message + ': ')
            to_return = int(to_return)
        except ValueError:
            print('--- "' + str(to_return) + '" not valid choice.')
            to_return = -1
        else:
            if to_return not in num_list:
                print('--- "' + str(to_return) + '" not valid choice.')
                to_return = -1

    return to_return


def user_select_yes_no(message):

    to_return = -1
    while to_return == -1:

        to_return = input('\n>>> ' + message + ' (y/n): ')
        to_return = str(to_return)
        if to_return.lower() in ['y', 'yes']:
            to_return = True
        elif to_return.lower() in ['n', 'no']:
            to_return = False
        else:
            print('--- "' + str(to_return) + '" not valid choice.')
            to_return = -1

    return to_return


def pad_string(string, length=25):
    len_pad = length - len(string)
    return str(string) + len_pad * ' '


name_change_map = {}
employees = {}


class Command(BaseCommand):

    conn = None
    updating_cursor = None
    iterating_cursor = None

    # employees_list = {}

    def add_edit_user_accel(self, id, qa_user, is_new=False, third_party=None):

        if third_party:
            third_party = str(third_party)

        if not is_new:
            self.updating_cursor.execute(
                """
                UPDATE employees
                SET winlogon = ?, third_party = ?, user_id = ?
                WHERE employee_id = ?
                """,
                str(qa_user.username),
                third_party,
                str(qa_user.id),
                str(id)
            )
        else:
            self.updating_cursor.execute(
                ' INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                str(id),
                str(qa_user.first_name + ' ' + qa_user.last_name),
                str('autopass'),
                False,
                False,
                False,
                str(qa_user.email),
                str(qa_user.username),
                third_party,
                str(qa_user.id)
            )

    def handle(self, *args, **kwargs):
        # handlers = {
        #     "migrate-accel": self.migrate_accel,
        # }
        #
        # if not args or args[0] not in list(handlers.keys()):
        #     valid = ', '.join(["'%s'" % x for x in list(handlers.keys())])
        #     raise CommandError("Valid arguments are %s" % (valid))
        #
        # handlers[args[0]]()
        self.migrate_accel()

    def setup_connection(self):

        odbc_conn_str = 'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=%s;UID=%s;PWD=%s' % (
            amt_settings.ACCEL_DB_LOCATION, amt_settings.DB_USER, amt_settings.DB_PASS
        )

        self.conn = pyodbc.connect(odbc_conn_str)
        self.updating_cursor = self.conn.cursor()
        self.iterating_cursor = self.conn.cursor()

    def migrate_accel(self):

        print('\n /------------------------------------------------------------------\\\n'
              '<              Accel > QaTrack+ migration tool                       >\n'
              ' \__________________________________________________________________/')

        print('\n---\tWelcome to the Accel > QaTrack+ migration tool. Make sure tables in Accel are properly organized\n'
              '\tbefore continuing (Employee names and ids in service and workload tables are listed in emplpyee table,\n'
              '\tand service types listed in service are in service type table and named correctly).')

        self.setup_connection()

        done = False
        while not done:
            print('\n---\tOptions:')
            print('\t1: Migrate users')
            print('\t2: Migrate service types to service areas')
            print('\t3: Migrate equipment')
            print('\t4: Migrate service events (Complete 1 - 3 first)')
            print('\t5: Migrate workload (Complete 4 first)')
            print('\t8: Commit changes to Accel database')
            print('\t9: Commit changes to Accel database and Exit')

            choices = {
                1: self.migrate_users,
                2: self.migrate_service_types,
                3: self.migrate_equipment,
                4: self.migrate_service,
                5: self.migrate_workload,
                8: self.commit_to_accel,
                9: self.done_exit
            }

            choice = user_select_from_list_of_numbers('Select option', [1, 2, 3, 4, 5, 8, 9])

            done = choices[choice]()

        self.conn.close()

    def migrate_users(self):

        print('\n---\tMigrating users. This will iterate through users in Accel database "employee" table and\n'
              '\talter the values to match what is in QaTracks database. These will be used in later migrations.\n'
              '\tIt will also add new users, third parties, and vendors to the QaTrack database when needed. ')

        if use_ldap:
            print('\n---\tEnter your network credentials')
            ldap_username = input('>>> username: ')
            ldap_pw = getpass.getpass('>>> password: ')

        cursor = self.conn.cursor()

        try:
            cursor.execute('select third_party from employees')
        except pyodbc.Error:
            cursor.execute('ALTER TABLE employees ADD COLUMN third_party INT, user_id INT')
            # cursor.execute('ALTER TABLE employees ADD COLUMN user_id INT')

        # clean up name fields
        cursor.execute('update service set physicist_reported = ltrim(rtrim(physicist_reported)) where ltrim(rtrim(physicist_reported)) is not null')
        cursor.execute('update service set physics_approval = ltrim(rtrim(physics_approval)) where ltrim(rtrim(physics_approval)) is not null')
        cursor.execute('update service set edited_by = ltrim(rtrim(edited_by)) where ltrim(rtrim(edited_by)) is not null')

        # TODO: clean up employees in service and Workload tables

        cursor.execute('select employee_id, staff_name, ADMIN, active, physics, email, winlogon, PASSWORD from employees')

        while 1:
            row = cursor.fetchone()
            if not row:
                break

            user_is_ldap = use_ldap
            done_with_user = False

            while not done_with_user:

                print('\n---\tAccel user entry: ')
                print('\t> Winlogon:\t' + str(row.winlogon))
                print('\t> Name:\t\t' + str(row.staff_name))
                print('\t> Is active:\t' + str(row.active))
                print('\t> Is admin:\t' + str(row.ADMIN))
                print('\t> Email:\t\t' + str(row.email))
                print('\t> Accel ID:\t' + str(row.employee_id))

                try:
                    suggested = User.objects.get(username=row.winlogon)
                except User.DoesNotExist:
                    suggested = None

                if suggested:
                    print('\n---\tFound user from QaTrack database: ')
                    print('\t> Username:\t' + suggested.username)
                    print('\t> First name:\t' + suggested.first_name)
                    print('\t> Last name:\t' + suggested.last_name)
                    print('\t> Is active:\t' + str(suggested.is_active))

                    correct = user_select_yes_no('Is this the correct match?')

                    if correct:
                        self.add_edit_user_accel(row.employee_id, suggested)
                        done_with_user = True
                        continue

                print('\n---\tWould you like to select qatrack user/third party, or create a new one?')
                print('\t1: Select another user')
                print('\t2: Create new user')
                print('\t3: Third Party')
                print('\t4: Skip this user')
                print('\t9: Return ')

                select_or_new = user_select_from_list_of_numbers('Select option', [1, 2, 3, 4, 9])

                if select_or_new == 1:

                    print('\n---\tChoose the user from the list:')
                    users = User.objects.all().order_by('username')
                    for user in users:
                        print('\t' + str(user.id) + ':\t' + str(user))
                    print('\n\t0: Return')

                    user_list = list(users.values_list('id', flat=True))
                    user_list.append(0)
                    user_id = user_select_from_list_of_numbers('Select user number', user_list)
                    if user_id == 0:
                        continue
                    qa_user = User.objects.get(id=user_id)

                    self.add_edit_user_accel(row.employee_id, qa_user)

                    done_with_user = True

                elif select_or_new == 2:

                    if user_is_ldap:
                        ldap.set_option(ldap.OPT_REFERRALS, 0)
                        l = ldap.initialize(qat_settings.AD_LDAP_URL)
                        l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                        binddn = "%s@%s" % (ldap_username, qat_settings.AD_NT4_DOMAIN)
                        try:
                            l.bind_s(binddn, ldap_pw)
                            try:
                                first_name = row.staff_name.split(' ')[0]
                                last_name = row.staff_name.split(' ')[1]
                                result = l.search_ext_s(qat_settings.AD_SEARCH_DN, ldap.SCOPE_SUBTREE, "(&(%s=%s)(%s=%s))" % (qat_settings.AD_LU_GIVEN_NAME, first_name, qat_settings.AD_LU_SURNAME, last_name), qat_settings.AD_SEARCH_FIELDS)[0][1]

                                if result.get(qat_settings.AD_LU_ACCOUNT_NAME, None):

                                    print('\n---\tUser ' + first_name + ' ' + last_name + ' found in ldap directory (username: ' + result.get(qat_settings.AD_LU_ACCOUNT_NAME)[0].decode('ascii') + ')')
                                    if user_select_yes_no('Correct match?'):
                                        qa_user = User(username=result.get(qat_settings.AD_LU_ACCOUNT_NAME)[0].decode('ascii'), first_name=first_name, last_name=last_name, email=result.get(qat_settings.AD_LU_MAIL)[0].decode('ascii'))
                                        qa_user.set_password('ldap authenticated')
                                        qa_user.save()
                                        self.add_edit_user_accel(row.employee_id, qa_user)
                                        print('\n---\tUser ' + qa_user.username + ' created successfully!')
                                        done_with_user = True
                                        continue
                                    else:
                                        user_is_ldap = not user_select_yes_no('Failed creating ldap user. Create user anyways using Accel credentials?')
                                else:
                                    user_is_ldap = not user_select_yes_no('User ' + first_name + ' ' + last_name + ' not found in ldap. Create user anyways using Accel credentials?')
                            except (AttributeError, IndexError):
                                print('\n---\tCreation of new ldap user failed! User ' + first_name + ' ' + last_name + ' not found in ldap directory')
                                user_is_ldap = not user_select_yes_no('Create user anyways using Accel credentials?')

                        except ldap.INVALID_CREDENTIALS:
                            user_is_ldap = not user_select_yes_no('Could not bind to ldap (check credentials you entered earlier). Create user anyways using Accel credentials?')

                    if not user_is_ldap:

                        # username = ''
                        # while username == '':
                        #     if row.winlogon is not None and row.winlogon.strip() != '':
                        #         username = input('\n>>> Enter new username or leave blank to use ' + row.winlogon + ': ')
                        #         if username == '':
                        #             username = row.winlogon
                        #     else:
                        #         username = input('\n>>> Enter new username: ')
                        #
                        #     if User.objects.filter(username=username).exists():
                        #         print('\n---\tThat username already exists in the Qatrack database!')
                        #         username = ''
                        #         continue
                        username = row.staff_name.replace(' ', '').lower()

                        f_name = row.staff_name.split(' ')[0]
                        try:
                            l_name = row.staff_name.split(' ')[1]
                        except (AttributeError, IndexError):
                            l_name = ''
                        qa_user = User(username=username, email=row.email, first_name=f_name, last_name=l_name)
                        qa_user.set_password(row.PASSWORD)
                        qa_user.save()

                        self.add_edit_user_accel(row.employee_id, qa_user)
                        done_with_user = True

                    else:
                        print('\n---\tOut of options, going back to menu for this user')

                elif select_or_new == 3:

                    print('\n---\tCurrent Third Parties in QaTrack: ')
                    for tp in sl_models.ThirdParty.objects.all():
                        print('\t- ' + tp.first_name + ' ' + tp.last_name + ' - ' + tp.vendor.name)

                    print('\n\tCurrent Vendors in QaTrack: ')
                    for v in sl_models.Vendor.objects.all():
                        print('\t- ' + v.name)

                    v_name = input('\n>>> Enter vendor name (Can be new one not listed above): ')
                    pf_name = input('>>> Enter third party\'s first name (Can be new person not listed above): ')
                    pl_name = input('>>> Enter third party\'s last name (Can be new person not listed above): ')

                    vendor, v_is_new = sl_models.Vendor.objects.get_or_create(name=v_name)
                    third_party, tp_is_new = sl_models.ThirdParty.objects.get_or_create(vendor=vendor, first_name=pf_name, last_name=pl_name)

                    users = User.objects.all().order_by('username')
                    user_list = list(users.values_list('id', flat=True))
                    user_list.append(0)
                    another_loop = False
                    while not another_loop:
                        print('\n---\tExisting third parties in Accel need an associated QaTrack logon.')
                        print('\t1: Create new user')
                        print('\t2: Select existing user\'s logon')

                        choice = user_select_from_list_of_numbers('Select option', [1, 2])

                        if choice == 1:
                            qa_user, tpu_is_new = User.objects.get_or_create(
                                first_name=third_party.first_name,
                                last_name=third_party.last_name,
                                username=third_party.first_name.lower().replace(' ', '') + third_party.last_name.lower().replace(' ', ''),
                                email='email',
                                is_active=False
                            )
                            qa_user.set_password(row.PASSWORD)
                            qa_user.save()
                            another_loop = True

                        elif choice == 2:

                            for u in users:
                                print('\t' + str(u.id) + ':\t' + str(u))
                            print('\n\t0: Return')
                            tpu_id = user_select_from_list_of_numbers('Select user to use as thirdparty logon', user_list)
                            if tpu_id == 0:
                                continue
                            another_loop = True
                            qa_user = User.objects.get(pk=tpu_id)

                        self.add_edit_user_accel(row.employee_id, qa_user, third_party=third_party.id)
                    done_with_user = True

                elif select_or_new == 4:
                    print('\n---\tUsers should only be skipped if they are not linked to any existing service events, or \n'
                          '\tservice events and workloads related to this user can be deleted or changed to another user later.')
                    if user_select_yes_no('Skip anyways?'):
                        done_with_user = True

                elif select_or_new == 9:
                    return False

        print('\n---\tUser migration complete')
        return False

    def migrate_service_types(self):

        print('\n---\tMigrating service types. This will iterate through service types in Accel database and\n'
              '\tadd new service areas in the QaTrack database if they are not already.\n')

        try:
            self.updating_cursor.execute('select service_area from service_types')
        except pyodbc.Error:
            self.updating_cursor.execute(""" ALTER TABLE service_types ADD COLUMN service_area INT """)

        self.iterating_cursor.execute('select headings from service_types')

        while 1:
            row = self.iterating_cursor.fetchone()
            if not row:
                break

            done_with_service_type = False
            while not done_with_service_type:
                qa_service_area = None

                print('\n---\tAccel service type entry: ')
                print('\t> Service Type:\t' + str(row.headings))

                try:
                    suggested = sl_models.ServiceArea.objects.get(name=row.headings)
                    print('\n---\tFound service area from QaTrack database: ')
                    print('\t> Service area:\t' + suggested.name)

                    if user_select_yes_no('Is this the correct match'):
                        done_with_service_type = True

                        self.updating_cursor.execute(
                            """
                            UPDATE service_types
                            SET service_area = ?
                            WHERE headings = ?
                            """,
                            str(suggested.id),
                            row.headings
                        )

                        continue

                except ObjectDoesNotExist:
                    pass

                print('\n---\tWould you like to select qatrack service area, or create a new one?')
                print('\t1: Select another service area')
                print('\t2: Create new service area')
                print('\t3: Skip this service type')
                print('\t9: Return ')

                select_or_new = user_select_from_list_of_numbers('Select option', [1, 2, 3, 9])

                if select_or_new == 1:

                    print('\n---\tChoose the service area from the list:')
                    service_areas = sl_models.ServiceArea.objects.all().order_by('name')
                    for sa in service_areas:
                        print('\t' + str(sa.id) + ':\t' + str(sa.name))
                    print('\n\t0: Return')

                    service_area_list = list(service_areas.values_list('id', flat=True))
                    service_area_list.append(0)
                    service_area_id = user_select_from_list_of_numbers('Select problem type number', service_area_list)
                    if service_area_id == 0:
                        continue
                    qa_service_area = sl_models.ServiceArea.objects.get(id=service_area_id)

                    self.updating_cursor.execute(
                        """
                        UPDATE service_types
                        SET service_area = ?
                        WHERE headings = ?
                        """,
                        str(qa_service_area.id),
                        row.headings
                    )
                    done_with_service_type = True

                elif select_or_new == 2:

                    sa_name = ''
                    while sa_name == '':
                        if row.headings is not None and row.headings.strip() != '':
                            sa_name = input('\n>>> Enter problem type name (leave blank to use ' + row.headings + '): ')
                            if sa_name == '':
                                sa_name = row.headings
                        else:
                            sa_name = input('\n>>> Enter problem type name: ')

                    qa_service_area, qa_sa_is_new = sl_models.ServiceArea.objects.get_or_create(name=sa_name)

                    self.updating_cursor.execute(
                        """
                        UPDATE service_types
                        SET service_area = ?
                        WHERE headings = ?
                        """,
                        str(qa_service_area.id),
                        row.headings
                    )
                    done_with_service_type = True

                elif select_or_new == 3:
                    print(
                        '\n---\tService types should only be skipped if they are not linked to any existing service events.\n'
                        '\tskipped service types in service events will be set to None during service event migration.')
                    if user_select_yes_no('Skip anyways?'):
                        done_with_service_type = True

                elif select_or_new == 9:
                    return False

        return False

    def migrate_equipment(self):

        print('\n---\tMigrating equipment. This will iterate through equipment in Accel database and\n'
              '\tadd new units and models in the QaTrack database as needed.\n')

        try:
            self.updating_cursor.execute('select unit_id from equipment')
        except pyodbc.Error:
            self.updating_cursor.execute(""" ALTER TABLE equipment ADD COLUMN unit_id INT """)

        self.iterating_cursor.execute('select id_key, type_of_eq, model, serial_no, unit_no, acceptancedate, active from equipment')

        while 1:
            row = self.iterating_cursor.fetchone()
            if not row:
                break

            done_with_unit = False
            while not done_with_unit:
                u_unit = None
                tz_date_acceptance = None
                if row.acceptancedate:
                    tz_date_acceptance = row.acceptancedate.date()

                print('\n---\tAccel equipment entry: ')
                print('\t' + pad_string("> Unit:", 20) + str(row.unit_no))
                print('\t' + pad_string("> Type of eq:", 20) + str(row.type_of_eq))
                print('\t' + pad_string("> Model:", 20) + str(row.model))
                print('\t' + pad_string("> Serial #:", 20) + str(row.serial_no))
                print('\t' + pad_string("> Acceptance Date:", 20) + str(row.acceptancedate))
                print('\t' + pad_string("> Is active:", 20) + str(row.active))

                print('\n---\tWould you like to select qatrack unit, or create a new one?')
                print('\t1: Select existing unit')
                print('\t2: Create new unit')
                print('\t3: Skip this unit')
                print('\t9: Return ')

                select_or_new = user_select_from_list_of_numbers('Select option', [1, 2, 3, 9])

                if select_or_new == 1:

                    print('\n---\tChoose the unit from the list:')
                    units = u_models.Unit.objects.all().order_by('name')
                    for u in units:
                        print(
                            '\t' +
                            pad_string(str(u.id) + ':', 7) +
                            pad_string(u.name, 20) + ' | ' +
                            pad_string("Active(" + str(u.active) + ")", 16) + ' | ' +
                            pad_string("Type(" + u.type.name + ", " + str(u.type.model) + ", " + u.type.vendor.name + ")", 40)
                        )
                    print('\n\t0: Return')

                    unit_list = list(units.values_list('id', flat=True))
                    unit_list.append(0)
                    unit_id = user_select_from_list_of_numbers('Select unit number', unit_list)
                    if unit_id == 0:
                        continue

                    u_unit = u_models.Unit.objects.get(id=unit_id)
                    u_unit.date_acceptance = tz_date_acceptance
                    u_unit.serial_number = row.serial_no
                    u_unit.save()

                    u_class, uc_is_new = u_models.UnitClass.objects.get_or_create(name=row.type_of_eq)
                    u_unit.type.unit_class = u_class
                    u_unit.type.save()

                    self.updating_cursor.execute(
                        """
                        UPDATE equipment
                        SET unit_id = ?
                        WHERE id_key = ?
                        """,
                        str(u_unit.id),
                        str(row.id_key)
                    )
                    done_with_unit = True

                if select_or_new == 2:

                    print('\n---\tExisting units for reference:')
                    units = u_models.Unit.objects.all().order_by('name')
                    for u in units:
                        print(
                            '\t' +
                            pad_string(u.name, 22) + ' | ' +
                            pad_string("Active(" + str(u.active) + ")", 15) + ' | ' +
                            pad_string("Number(" + str(u.number) + ")", 18) + ' | ' +
                            pad_string("Type(" + u.type.name + ", " + u.type.model + ", " + u.type.vendor.name + ")", 40)
                        )

                    u_name = ''
                    while u_name == '':
                        u_name = input('\n>>> Enter new unit name: ')
                    u_number = 1
                    while u_models.Unit.objects.filter(number=u_number).exists():
                        u_number += 1

                    print('\n---\tSetting up unit type...')
                    print('\n---\tExisting unit types for reference:')
                    unit_types = u_models.UnitType.objects.all().order_by('name')
                    for ut in unit_types:
                        print(
                            '\t' +
                            pad_string("Name: " + ut.name, 30) + ' | ' +
                            pad_string("Model: " + ut.model, 30) + ' | ' +
                            pad_string("Vendor: " + ut.vendor.name)
                        )

                    print('\n---\tEnter unit type name and model. Entering the same name-model combination as an entry on the list above will select\n'
                          '\tan existing unit type, otherwise you will be prompted for a vendor name and a new unit type will be created.')
                    unit_type_name = input('>>> Enter unit type name: ')
                    unit_type_model = input('>>> Enter unit type model (can be blank): ')
                    try:
                        u_unit_type = u_models.UnitType.objects.get(name=unit_type_name, model=unit_type_model)
                    except ObjectDoesNotExist:

                        print('\n---\tCreating new unit type...')
                        print('\n---\tExisting vendors for reference:')
                        vendors = u_models.Vendor.objects.all().order_by('name')
                        for v in vendors:
                            print('\t' + v.name)

                        vendor_name = input('\n>>> Enter vendor name (can be new one not listed above): ')
                        ut_vendor, v_is_new = u_models.Vendor.objects.get_or_create(name=vendor_name)
                        ut_vendor.save()

                        u_unit_type = u_models.UnitType(name=unit_type_name, model=unit_type_model, vendor=ut_vendor)
                        u_unit_type.save()

                    u_unit = u_models.Unit.objects.create(number=u_number, name=u_name, type=u_unit_type)
                    u_unit.serial_number = row.serial_no
                    u_unit.active = row.active
                    u_unit.location = ''
                    u_unit.date_acceptance = tz_date_acceptance
                    u_unit.save()

                    u_class, uc_is_new = u_models.UnitClass.objects.get_or_create(name=row.type_of_eq)
                    u_unit.type.unit_class = u_class
                    u_unit.type.save()

                    self.updating_cursor.execute(
                        """
                        UPDATE equipment
                        SET unit_id = ?
                        WHERE id_key = ?
                        """,
                        str(u_unit.id),
                        str(row.id_key)
                    )
                    done_with_unit = True

                if select_or_new == 3:
                    print(
                        '\n---\tEquipment should only be skipped if they are not linked to any existing service events. Service events\n.'
                        '\ton skipped equipment will not be migrated.'
                    )
                    if user_select_yes_no('Skip anyways?'):
                        done_with_unit = True

                if select_or_new == 9:
                    return False

        print('\n---\tDone migrating equipment')

    def migrate_service(self):

        print(
            '\n---\tMigrating service. This will iterate through service table in Accel database and\n'
            '\tadd new service events in the QaTrack database as needed.\n'
            '\n\t**************************************************************************************************'
            '\n\tNote. Please make sure you have the following properly configured in QaTrack before continuing:'
            '\n\n\t\tGroup linkers\n\t\tService event statuses\n\t\tService types\n\t\t'
            '\n\t**************************************************************************************************'
        )

        # Set up GroupLinkers
        print('\n---\tCurrent group linkers in QaTrack database:')
        gl_q = sl_models.GroupLinker.objects.all()
        for gl in gl_q:
            print('\t' + str(gl.id) + ': ' + gl.name)

        gl_ids = list(gl_q.values_list('id', flat=True))
        gl_for_physicist_id = user_select_from_list_of_numbers('Select group linker for Accel field "Physicist Reported To"', gl_ids)
        gl_for_physicist = sl_models.GroupLinker.objects.get(pk=gl_for_physicist_id)
        gl_for_therapist_id = user_select_from_list_of_numbers('Select group linker for Accel field "Therapist Reported To"', gl_ids)
        gl_for_therapist = sl_models.GroupLinker.objects.get(pk=gl_for_therapist_id)

        # Set up ServiceEventStatuses
        print('\n---\tSelect service event status for all approved Accel services')
        for ses in sl_models.ServiceEventStatus.objects.filter(is_approval_required=False):
            print('\t' + str(ses.id) + ': ' + ses.name)

        approved_status_id = user_select_from_list_of_numbers('Select approved status id', list(sl_models.ServiceEventStatus.objects.filter(is_approval_required=False).values_list('id', flat=True)))

        print('\n---\tSelect service event status for all other Accel services')
        for ses in sl_models.ServiceEventStatus.objects.all():
            print('\t' + str(ses.id) + ': ' + ses.name)

        status_id = user_select_from_list_of_numbers('Select status id for other services', list(sl_models.ServiceEventStatus.objects.all().values_list('id', flat=True)))

        # Set up ServiceTypes
        st_q = sl_models.ServiceType.objects.all()

        print('\n---\tService types in QaTrack database: ')
        for st in st_q:
            print('\t' + str(st.id) + ': ' + st.name)

        extensive_service_type_id = user_select_from_list_of_numbers('Select type for extensive Accel services', list(st_q.values_list('id', flat=True)))
        pmi_service_type_id = user_select_from_list_of_numbers('Select type for PMI Accel services', list(st_q.values_list('id', flat=True)))
        other_service_type_id = user_select_from_list_of_numbers('Select type for the rest of Accel services', list(st_q.values_list('id', flat=True)))

        print('\n---\tStarting migration... This might take awhile if your Accel DB is large')

        try:
            self.updating_cursor.execute('select service_event_id from service')
        except pyodbc.Error:
            self.updating_cursor.execute(""" ALTER TABLE service ADD COLUMN service_event_id INT """)

        self.iterating_cursor.execute(
            """
            SELECT
              srn,
              unit_no,
              date,
              time,
              problem,
              work_done,
              employee_id,
              service_time,
              service_time_min,
              lost_time,
              lost_time_min,
              type_of_service,
              extensive,
              physicist_reported,
              safety_precautions,
              radiation_therapist,
              physics_approval,
              approval_date,
              approved,
              edited_by,
              PMI,
              user_win_id
            FROM service
            ORDER BY srn
            """
        )

        while 1:
            row = self.iterating_cursor.fetchone()
            if not row:
                break

            try:
                if sl_models.ServiceEvent.objects.filter(id=row.srn).exists():
                    continue

                user_created_row = self.updating_cursor.execute('select winlogon, third_party, PASSWORD from employees where employee_id = ?', row.employee_id).fetchone()
                created_by_winlogon = user_created_row.winlogon
                created_by = User.objects.get(username=created_by_winlogon)

                unit_id = self.updating_cursor.execute('select unit_id from equipment where unit_no = ?', row.unit_no).fetchone().unit_id
                unit = u_models.Unit.objects.get(pk=unit_id)

                service_area_id = self.updating_cursor.execute('select service_area from service_types where headings = ?', row.type_of_service).fetchone().service_area
                service_area = sl_models.ServiceArea.objects.get(pk=service_area_id)

                unit_service_area, usa_is_new = sl_models.UnitServiceArea.objects.get_or_create(unit=unit, service_area=service_area)

                datetime_service = timezone.datetime.combine(row.date.date(), row.time.time())
                datetime_created = datetime_service

                service_time = timezone.timedelta(hours=row.service_time, minutes=row.service_time_min)

                lost_time = timezone.timedelta(hours=row.lost_time, minutes=row.lost_time_min)

                if row.approved:
                    service_status = sl_models.ServiceEventStatus.objects.get(pk=approved_status_id)
                    status_changed_by_winlogon = self.updating_cursor.execute('select winlogon from employees where staff_name = ?', row.physics_approval.strip()).fetchone().winlogon
                    status_changed_by = User.objects.get(username=status_changed_by_winlogon)
                    datetime_status_changed = row.approval_date
                else:
                    service_status = sl_models.ServiceEventStatus.objects.get(pk=status_id)
                    status_changed_by = None
                    datetime_status_changed = None

                if row.extensive:
                    service_type = sl_models.ServiceType.objects.get(pk=extensive_service_type_id)
                elif row.PMI:
                    service_type = sl_models.ServiceType.objects.get(pk=pmi_service_type_id)
                else:
                    service_type = sl_models.ServiceType.objects.get(pk=other_service_type_id)

                is_approval_required = service_type.is_approval_required

                if row.edited_by:
                    modified_by_row = self.updating_cursor.execute('select winlogon, third_party, PASSWORD from employees where staff_name = ?', row.edited_by.strip()).fetchone()
                    modified_by_winlogon = modified_by_row.winlogon
                    modified_by = User.objects.get(username=modified_by_winlogon)
                    datetime_modified = datetime_service
                else:
                    modified_by = None
                    datetime_modified = None

                service_event = sl_models.ServiceEvent(
                    datetime_created=datetime_created,
                    datetime_service=datetime_service,
                    datetime_modified=datetime_modified,
                    datetime_status_changed=datetime_status_changed,
                    # srn=row.srn,
                    safety_precautions=row.safety_precautions,
                    problem_description=row.problem,
                    work_description=row.work_done,
                    duration_service_time=service_time,
                    duration_lost_time=lost_time,
                    service_status=service_status,
                    service_type=service_type,
                    unit_service_area=unit_service_area,
                    user_created_by=created_by,
                    user_modified_by=modified_by,
                    user_status_changed_by=status_changed_by,
                    is_approval_required=is_approval_required
                )
                service_event.save()
                self.updating_cursor.execute('update service set service_event_id = ? where srn = ?', str(service_event.id), str(row.srn))

                # Search through problem in service event and create related events from description.
                if amt_settings.FIND_RELATED_IN_PROBLEM and amt_settings.RELATED_EVENT_REGEX.search(row.problem) is not None:
                    srn = amt_settings.RELATED_EVENT_REGEX.search(row.problem).groups(0)[1]
                    try:
                        rel_id = self.updating_cursor.execute('select service_event_id from service where srn = ?', srn).fetchone().service_event_id
                        related_event = sl_models.ServiceEvent.objects.get(id=rel_id)
                        service_event.service_event_related = [related_event]

                        new_problem = re.sub(str(srn), str(related_event.id), row.problem)
                        service_event.problem_description = new_problem

                        print('---\tFound related service event. Changed srn: ' + str(srn) + ' to id: ' + str(rel_id))
                    except AttributeError:
                        print('---\tCould not find service event srn: ' + str(srn) + ' in Accel db. Skipping related event creation.')
                    except ObjectDoesNotExist:
                        print('---\tCould not find service event id: ' + str(rel_id) + ' in QaTrack db. Skipping related event creation.')

                    service_event.save()

                if row.physicist_reported and row.physicist_reported.strip() != '':
                    physicist_winlogon = self.updating_cursor.execute('select winlogon from employees where staff_name = ?', row.physicist_reported.strip()).fetchone().winlogon
                    physicist_reported_to = User.objects.get(username=physicist_winlogon)

                    gli_physicist_reported_to = sl_models.GroupLinkerInstance(
                        group_linker=gl_for_physicist,
                        user=physicist_reported_to,
                        service_event=service_event,
                        datetime_linked=datetime_service
                    )
                    gli_physicist_reported_to.save()

                if row.radiation_therapist and row.radiation_therapist.strip() != '':
                    try:
                        name = re.sub('[,.()\\\/\s]+', ' ', row.radiation_therapist).strip()
                        first_name = name.split(' ')[0]
                        last_name = name.split(' ')[1]
                        therapist_reported_to = None
                        if len(first_name) == 1:
                            users_q = User.objects.filter(first_name__startswith=first_name)
                            for u in users_q:
                                if u.last_name == last_name:
                                    therapist_reported_to = u
                            if not therapist_reported_to:
                                raise ObjectDoesNotExist
                        else:
                            therapist_reported_to = User.objects.get(first_name=first_name, last_name=last_name)
                    except (ObjectDoesNotExist, IndexError):
                        pass
                    else:
                        print('---\tFound therapist ' + therapist_reported_to.username + ' for field value of ' + name)
                        gli_therapist_reported_to = sl_models.GroupLinkerInstance(
                            group_linker=gl_for_therapist,
                            user=therapist_reported_to,
                            service_event=service_event,
                            datetime_linked=datetime_service
                        )
                        gli_therapist_reported_to.save()

            except Exception as e:
                print('Error migrating service: ' + str(row.srn))
                raise e

        print('\n---\tDone migrating service table')
        return False

    def migrate_workload(self):

        try:
            self.updating_cursor.execute('select hours_id from Workload')
        except pyodbc.Error:
            self.updating_cursor.execute(""" ALTER TABLE Workload ADD COLUMN hours_id INT """)

        self.iterating_cursor.execute(
            """
            SELECT
              srn,
              employee,
              time,
              hours_id
            FROM Workload
            ORDER BY srn
            """
        )

        print('\n---\tStarting workload migration. This might take awhile depending on Accel table size')

        while 1:
            row = self.iterating_cursor.fetchone()
            if not row:
                break

            if not row.hours_id:

                try:
                    try:
                        service_event_id = self.updating_cursor.execute('select service_event_id from service where srn = ?', str(row.srn)).fetchone().service_event_id
                        service_event = sl_models.ServiceEvent.objects.get(id=service_event_id)
                    except ObjectDoesNotExist:
                        print('---\tServce with id ' + str(service_event_id) + ' not found in QaTrack db.')
                        continue
                    except AttributeError:
                        print('---\tService with srn ' + str(row.srn) + ' not found in Accel db.')
                        continue

                    employee_row = self.updating_cursor.execute('select winlogon, third_party from employees where employee_id = ?', row.employee).fetchone()

                    if employee_row.third_party:
                        third_party = sl_models.ThirdParty.objects.get(pk=employee_row.third_party)
                        user = None
                    else:
                        user = User.objects.get(username=employee_row.winlogon)
                        third_party = None

                    try:
                        hours = sl_models.Hours.objects.get(service_event=service_event, user=user, third_party=third_party)
                        hours.time = timezone.timedelta(minutes=round(row.time * 60))
                    except ObjectDoesNotExist:
                        hours = sl_models.Hours.objects.create(service_event=service_event, user=user, third_party=third_party, time=timezone.timedelta(minutes=round(row.time * 60)))
                    hours.save()

                    self.updating_cursor.execute('update Workload set hours_id = ? where srn = ? and employee = ?', str(hours.id), str(row.srn), str(row.employee))

                except Exception as e:
                    print('\n---\tError with workload item related to service ' + str(row.srn))
                    print(row)
                    raise e

        print('\n---\tDone migrating workload')

        return False

    def commit_to_accel(self):
        self.conn.commit()
        return False

    def done_exit(self):
        self.conn.commit()
        return True



