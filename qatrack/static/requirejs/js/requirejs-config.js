
require.config({
    urlArgs: (function () {
        if (siteConfig.DEBUG == 'True')
            return 'v=' + Math.random();
        return 'v=' + siteConfig.VERSION;
    }()),
    baseUrl: siteConfig.STATIC_URL,
    paths: {
        // Third party:
        admin_lte: siteConfig.STATIC_URL + 'adminlte/js/admin-lte',
        admin_lte_config: siteConfig.STATIC_URL + 'adminlte/js/admin-lte-config',
        bootstrap: siteConfig.STATIC_URL + 'bootstrap/js/bootstrap',
        datatables: siteConfig.STATIC_URL + 'listable/js/jquery.dataTables',
        'datatables.bootstrap': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.bootstrap',
        'datatables.columnFilter': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.columnFilter',
        'datatables.searchPlugins': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.searchPlugins',
        'datatables.sort': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.sort',
        datepicker: siteConfig.STATIC_URL + 'datepicker/js/bootstrap-datepicker',
        daterangepicker: siteConfig.STATIC_URL + 'daterangepicker/js/daterangepicker',
        icheck: siteConfig.STATIC_URL + 'icheck/js/icheck.min',
        jquery: siteConfig.STATIC_URL + 'jquery/js/jquery',
        json2: siteConfig.STATIC_URL + 'json2/js/json2',
        listable: siteConfig.STATIC_URL + 'listable/js/listable',
        lodash: siteConfig.STATIC_URL + 'lodash/js/lodash',
        moment: siteConfig.STATIC_URL + 'moment/js/moment-with-locales',
        multiselect: siteConfig.STATIC_URL + 'multiselect/js/bootstrap.multiselect',
        slimscroll: siteConfig.STATIC_URL + 'slimscroll/js/jquery.slimscroll',

        // Site wide:
        sidebar: siteConfig.STATIC_URL + 'qatrack_core/js/sidebar',
        site_base: siteConfig.STATIC_URL + 'qatrack_core/js/base',

        // qa module:
        qa: siteConfig.STATIC_URL + 'qa/js/qa',
        qautils: siteConfig.STATIC_URL + 'qa/js/qautils',
        testlistinstance: siteConfig.STATIC_URL + 'qa/js/testlistinstance'

        // unit module:
    },
    shim: {
        // Third party:
        admin_lte: {
            deps: ['jquery', 'bootstrap', 'slimscroll', 'admin_lte_config']
        },
        bootstrap: {
            deps: ['jquery']
        },
        datatables: {
            deps: ['jquery'],
            exports: 'dataTable'
        },
        'datatables.bootstrap': {
            deps: ['jquery', 'datatables', 'bootstrap']
        },
        'datatables.columnFilter': {
            deps: ['jquery', 'datatables']
        },
        'datatables.searchPlugins': {
            deps: ['jquery', 'datatables']
        },
        'datatables.sort': {
            deps: ['jquery', 'datatables']
        },
        datepicker: {
            deps: ['jquery', 'bootstrap']
        },
        daterangepicker: {
            exports: 'DateRangePicker',
            deps: ['jquery', 'moment']
        },
        icheck: {
            deps: ['jquery']
        },
        jquery: {
            exports: '$'
        },
        listable: {
            deps: ['jquery', 'datatables', 'datatables.columnFilter', 'datatables.searchPlugins', 'datatables.sort', 'datatables.bootstrap', 'multiselect', 'datepicker']
        },
        lodash: {
            exports: '_'
        },
        moment: {
            deps: ['jquery']
        },
        multiselect: {
            deps: ['jquery', 'bootstrap']
        },
        slimscroll: {
            deps: ['jquery']
        },

        // Site wide:
        sidebar: {
            deps: ['jquery', 'admin_lte', 'bootstrap', 'daterangepicker']
        },
        site_base: {
            deps: ['jquery']
        },

        // qa module:
        qa: {
            deps: ['jquery', 'qautils', 'site_base', 'lodash', 'datepicker']
        },
        testlistinstance: {
            deps: ['jquery', 'site_base', 'qa', 'lodash', 'datatables', 'datatables.columnFilter', 'daterangepicker', 'sidebar', 'icheck']
        }

        // unit module:
    }
});

require(['jquery', 'bootstrap', 'admin_lte', 'lodash', 'json2', 'site_base']);