
require.config({
    urlArgs: (function () {
        if (siteConfig.DEBUG == 'True')
            return 'v=' + Math.random();
        return 'v=' + siteConfig.VERSION;
    }()),
    baseUrl: siteConfig.STATIC_URL,
    paths: {
        // Third party:
        jquery: siteConfig.STATIC_URL + 'jquery/js/jquery',
        bootstrap: siteConfig.STATIC_URL + 'bootstrap/js/bootstrap',
        datepicker: siteConfig.STATIC_URL + 'datepicker/js/bootstrap-datepicker',
        multiselect: siteConfig.STATIC_URL + 'multiselect/js/bootstrap.multiselect',
        admin_lte_config: siteConfig.STATIC_URL + 'adminlte/js/admin-lte-config',
        admin_lte: siteConfig.STATIC_URL + 'adminlte/js/admin-lte',
        slimscroll: siteConfig.STATIC_URL + 'slimscroll/js/jquery.slimscroll',
        lodash: siteConfig.STATIC_URL + 'lodash/js/lodash',
        json2: siteConfig.STATIC_URL + 'json2/js/json2',
        datatables: siteConfig.STATIC_URL + 'listable/js/jquery.dataTables',
        'datatables.columnFilter': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.columnFilter',
        'datatables.searchPlugins': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.searchPlugins',
        'datatables.sort': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.sort',
        'datatables.bootstrap': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.bootstrap',
        listable: siteConfig.STATIC_URL + 'listable/js/listable',

        // Site wide:
        site_base: siteConfig.STATIC_URL + 'qatrack/js/base',

        // qa module:
        qa: siteConfig.STATIC_URL + 'qa/js/qa',
        qautils: siteConfig.STATIC_URL + 'qa/js/qautils',
        testlistinstance: siteConfig.STATIC_URL + 'qa/js/testlistinstance'

        // unit module:
    },
    shim: {
        // Third party:
        jquery: {
            exports: '$'
        },
        bootstrap: {
            deps: ['jquery']
        },
        datepicker: {
            deps: ['jquery', 'bootstrap']
        },
        multiselect: {
            deps: ['jquery', 'bootstrap']
        },
        admin_lte: {
            deps: ['jquery', 'bootstrap', 'slimscroll', 'admin_lte_config']
        },
        slimscroll: {
            deps: ['jquery']
        },
        lodash: {
            exports: '_'
        },
        datatables: {
            deps: ['jquery'],
            exports: 'dataTable'
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
        'datatables.bootstrap': {
            deps: ['jquery', 'datatables', 'bootstrap']
        },
        listable: {
            deps: ['jquery', 'datatables', 'datatables.columnFilter', 'datatables.searchPlugins', 'datatables.sort', 'datatables.bootstrap', 'multiselect', 'datepicker']
        },

        // Site wide:
        site_base: {
            deps: ['jquery']
        },

        // qa module:
        qa: {
            deps: ['jquery', 'qautils', 'site_base', 'lodash', 'datepicker']
        },
        testlistinstance: {
            deps: ['jquery', 'site_base', 'qa', 'lodash', 'datatables', 'datatables.columnFilter', 'datepicker']
        }

        // unit module:
    }
});

//
require(['jquery', 'bootstrap', 'admin_lte', 'lodash', 'json2', 'site_base']);