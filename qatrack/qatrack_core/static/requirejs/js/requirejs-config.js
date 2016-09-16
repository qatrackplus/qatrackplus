
require.config({
    urlArgs: 'v=' + siteConfig.VERSION,
    // urlArgs: (function () {
    //     if (siteConfig.DEBUG == 'True')
    //         return 'v=' + Math.random();
    //     return 'v=' + siteConfig.VERSION;
    // }()),
    baseUrl: siteConfig.STATIC_URL,
    paths: {
        // Third party:
        admin_lte: siteConfig.STATIC_URL + 'adminlte/js/admin-lte',
        admin_lte_config: siteConfig.STATIC_URL + 'adminlte/js/admin-lte-config',
        autosize: siteConfig.STATIC_URL + 'autosize/js/autosize.min',
        bootstrap: siteConfig.STATIC_URL + 'bootstrap/js/bootstrap.min',
        d3: siteConfig.STATIC_URL + 'd3/js/d3',
        datatables: siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.min',
        'datatables.bootstrap': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.bootstrap',
        'datatables.columnFilter': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.columnFilter',
        'datatables.searchPlugins': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.searchPlugins',
        'datatables.sort': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.sort',
        datepicker: siteConfig.STATIC_URL + 'datepicker/js/bootstrap-datepicker.min',
        daterangepicker: siteConfig.STATIC_URL + 'daterangepicker/js/daterangepicker',
        dropzone: siteConfig.STATIC_URL + 'dropzone/js/dropzone-amd-module',
        icheck: siteConfig.STATIC_URL + 'icheck/js/icheck.min',
        inputmask: siteConfig.STATIC_URL + "inputmask/js/inputmask",
        "inputmask.dependencyLib": siteConfig.STATIC_URL + "inputmask/js/inputmask.dependencyLib.jquery",
        'jquery.inputmask': siteConfig.STATIC_URL + 'inputmask/js/jquery.inputmask',
        jquery: siteConfig.STATIC_URL + 'jquery/js/jquery.min',
        'jquery-ui': siteConfig.STATIC_URL + 'jqueryui/js/jquery-ui.min',
        json2: siteConfig.STATIC_URL + 'json2/js/json2',
        listable: siteConfig.STATIC_URL + 'listable/js/listable',
        lodash: siteConfig.STATIC_URL + 'lodash/js/lodash',
        moment: siteConfig.STATIC_URL + 'moment/js/moment.min',
        multiselect: siteConfig.STATIC_URL + 'multiselect/js/bootstrap.multiselect',
        slimscroll: siteConfig.STATIC_URL + 'slimscroll/js/jquery.slimscroll.min',

        // Site wide:
        sidebar: siteConfig.STATIC_URL + 'qatrack_core/js/sidebar',
        site_base: siteConfig.STATIC_URL + 'qatrack_core/js/base',

        // qa module:
        qa: siteConfig.STATIC_URL + 'qa/js/qa',
        qacharts: siteConfig.STATIC_URL + 'qa/js/qacharts',
        qautils: siteConfig.STATIC_URL + 'qa/js/qautils',
        qareview: siteConfig.STATIC_URL + 'qa/js/qareview',
        qaoverview: siteConfig.STATIC_URL + 'qa/js/qaoverview'

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
            // deps: ['jquery'],
            exports: 'dataTable'
        },
        'datatables.bootstrap': {
            deps: [/*'jquery', */'datatables'/*, 'bootstrap'*/]
        },
        'datatables.columnFilter': {
            deps: [/*'jquery', */'datatables']
        },
        'datatables.searchPlugins': {
            deps: [/*'jquery', */'datatables']
        },
        'datatables.sort': {
            deps: [/*'jquery', */'datatables']
        },
        // datepicker: {
        //     deps: ['jquery', 'bootstrap']
        // },
        daterangepicker: {
            exports: 'DateRangePicker',
            deps: [/*'jquery', */'moment']
        },
        // icheck: {
        //     deps: ['jquery']
        // },
        jquery: {
            exports: '$'
        },
        listable: {
            deps: ['jquery', 'datatables', 'datatables.columnFilter', 'datatables.searchPlugins', 'datatables.sort', 'datatables.bootstrap', 'multiselect', 'datepicker', 'daterangepicker']
        },
        lodash: {
            exports: '_'
        },
        multiselect: {
            deps: ['jquery', 'bootstrap']
        },
        slimscroll: {
            deps: ['jquery']
        },

        // Site wide:
        sidebar: {
            deps: [/*'jquery', 'admin_lte', 'bootstrap', */'icheck']
        },
        site_base: {
            deps: ['jquery']
        },

        // qa module:
        qa: {
            deps: ['jquery', 'qautils', 'site_base', 'lodash', 'daterangepicker', 'sidebar', 'datatables', 'datatables.columnFilter', 'inputmask']
        },
        // qacharts: {
        //     deps: ['jquery', 'site_base', 'bootstrap', 'amdin_lte', 'json2']
        // },
        // qareview: {
        //     deps: ['jquery', 'site_base', 'bootstrap', 'admin_lte']
        // },
        // qaoverview: {
        //     deps: ['jquery', 'site_base', 'bootstrap', 'admin_lte']
        // }

        // unit module:
    }
});

require(['jquery', 'bootstrap', 'admin_lte', 'json2', 'site_base']);