Glossary
========

.. glossary::

    Admin Site

        This is the section of your QATrack+ site used for configuring Tests,
        Test Lists, Auto Review Rules etc. See :ref:`the Admin Site
        documentation <access_admin_site>`.

    API

        The API (Application Programming Interface) is a method you can use to
        access and upload data to your QATrack+ programmaticaly. See :ref:`the
        API documentation <qatrack_api>`.

    Auth Token

        The :term:`API` uses Auth tokens for authenticating API requests.

    Auto Review

        In QATrack+ you can set up :ref:`Auto Review Rules <qa_auto_review>` to
        automatically assign :term:`Test Instance Status`\s to your :term:`Test
        instance`\s so that no manual review is required.

    Auto Review Rule

        See :term:`Auto Review`.

    Category

        Categories define the type of test users are performing. Test Lists can
        be filtered by Test Category when performing QA. See :ref:`Categories
        <qa_categories>`.

    Contacts

        Contacts are phone numbers that can be displayed to users when
        performing QA in case they run into any issues and need to call for
        help. See :ref:`Contacts <qa_contacts>`.

    Frequency

        Frequency is the time schedule with which a test list is to be
        performed (e.g. Daily, Monthly, Annual etc). See :ref:`Frequency
        <qa_frequencies>`.

    Groups

        Groups are used to :term:`User` s with common roles
        within the clinic.  Groups are useful for managing :term:`Permissions`
        for similar users. See :ref:`Groups <auth_groups>`.

    Group Linkers

        Group linkers are used to specifiy individual :term:`Groups` members
        involved in a :term:`Service Event`. This information is displayed on
        the Service Event page in the Involved Parties and Durations frame and
        may be used to specifiy the various individuals involved in the Service
        Event (beyond those doing the actual service work). See :ref:`Service
        Log <service_log>`.

    Location

        Parts storage :term:`Rooms` may have one or more locations (e.g. a
        shelf, closet, cabinet etc) associated with them.

    Modality

        Treatment & diagnostic units may have multiple modalities assigned (for
        example 6MV photon & 15MeV electron).  In future, it may be possible to
        assign Test List's to specific Unit modalities rather than an entire
        Unit.

    Notification Subscriptions

        Notification subscriptions allow QATrack+ to send email alerts to
        different groups when a Test List is submitted with one or more Tests
        which are outside of Tolerance or Action levels.  See :ref:`Email
        notifications <qa_emails>`.

    Parts

        As of QATrack+ v0.3.0 there is now a Parts application which can be
        used for tracking spare parts inventory. See :ref:`Parts <parts_user>`.

    Parts Categories

        Parts categories allow you to categorize parts by their function (e.g.
        Linac, Table, Laser etc).

    Permissions

        The permissions assigned to Groups and Users control what functionality
        they have access to on the QATrack+ site.  See :ref:`Permissions
        <permissions_admin>`.

    QA Session

        See :term:`Test List Instance`.

    Reference

        The value which :term:`Test Instance` are compared to when performing QA
        to determine whether they are within tolerance and action levels. See
        :ref:`References & Tolerances <qa_ref_tols>`.

    Rooms

        Rooms are used in the :term:`Parts` app for keeping track of where
        spare parts are located.

    Return To Service QA

        Test Lists that must be performed after a :term:`Service Event` before
        a :term:`Unit` can be released for clinical service.

    RTS

       See :term:`Return to Service QA`

    RTS QA

       See :term:`Return to Service QA`

    Service Area

        Service Area's are different sub systems of a treatment unit & bunker.
        For example:

            - Treatment Table
            - Lasers
            - XVI
            - iView

    Service Event

        A machine service event like preventative maintenance, unplanned outage etc.
        See :ref:`Service Log <service_log>`.

    Service Event Status

        The status of a :term:`Service Event`. Service Event Status's indicate whether
        review of the Service Event is required and whether Return To Service QA must
        be reviewed. Example Service Event Status's include:
        - Service Pending
        - Service In Progress
        - Service Complete
        - Approved
        - Test Data
        - Rejected

    Service Type

        The type of a :term:`Service Event`. For example:
        - Preventative Maintenance
        - Minor Repairs / Corrective Maintenance
        - Extensive Repairs
        - Safety Systems

        See :ref:`Service Log <service_log>`.

    Site

        For clinics with multiple sites, you can indicate which site a
        :term:`Unit` is located at.

    Staff User

        A Staff user is any user who can access the admin section. See
        :ref:`Users <auth_users>`.

    Status

        See :term:`Test Instance Status`

    Sublist

        To ease configuration of :term:`Test List`\s, you can include other
        :term:`Test List`\s in addition to :term:`Test`\s. See :ref:`Sublists
        <qa_sublists>`.

    Superuser

        A User who has Superuser status has all :term:`Permissions` granted to
        them implicitly.  See :ref:`Users <auth_users>`.

    Suppliers

        Suppliers are companies/vendors who supply your clinic with parts. See
        :ref:`Parts <parts>`.

    Test

        A Test is any individual measurement to be entered into QATrack+. Tests may be
        a numerical value to be entered, a true or false checkmark, text entry etc.

    Test List

        A Test List is a grouping of Test's to be performed at the same time. For example
        a Test List might be "Monthly 6MV Output" and be made up of tests for temperature,
        air pressure, ion chamber calibration factors and ion chamber readings.

    Test List Cycle

        A Test List Cycle allows you to group multiple Test Lists into a single
        repeating cycle that can be assigned to a unit. See :ref:`Test Lists
        <qa_test_lists>`.

    Test Instance

        A Test Instance is a single completed value of any given :term:`Test`.
        Each Test Instance is assigned a :term:`Test Instance Status`.

    Test List Instance

        A Test List Instance is a single completed value of any given
        :term:`Test List`. Also called a `QA Session`.

    Test Instance Status

        A Test Instance Status is assigned to each :term:`Test Instance` which
        indicates whether a Test Instance is reviewed/approved/rejected. See
        :ref:`Statuses <qa_statuses>`.

    Test Pack

        A file of Tests, Test Lists, Test List Cycles, and Test Categories to
        enable sharing configurations between different clinics.  See
        :ref:`Test Packs <testpack_admin>`.

    Third Parties

        Third parties are service people, associated with a :term:`Vendor` from
        outside the clinic who work on/repair units.  See :ref:`Service Log
        <service_log>`.

    Tolerance

        Tolerances, in combination with :term:`Reference`\s, determine whether
        a Test Instance value is within tolerance or action levels.  See
        :ref:`References & Tolerances <qa_ref_tols>`.

    Unit
        A piece of equipment e.g. a linac, brachy suite, tomotherapy unit etc. You
        may also want to define e.g.

    Unit Class

        Unit class is the category of Unit e.g. Linac, Tomotherapy, CT, MRI etc.

    Unit Type

        The model of a unit e.g. Elekta Synergy, Varian TrueBeam.

    Unit Service Area Memberships

        Unit Service Area Memberships are how :term:`Service Area`\s are
        associated with a :term:`Unit` and are configured via the :ref:`Unit
        admin <unit_creating>`.

    Unit Test Collection

        Unit Test Collections are how :term:`Test List`\s and :term:`Frequency`
        are associated with a :ref:`Unit <unit_creating>`.

    Unreviewed Queue
        The set of :term:`Test List Instance`'s that require manual review.

    User

        Any person who has the ability to login to your QATrack+ site. See
        :ref:`User <auth_users>`.

    Vendor

        Major equipment vendors e.g. Accuray, Elekta, Varian etc.


