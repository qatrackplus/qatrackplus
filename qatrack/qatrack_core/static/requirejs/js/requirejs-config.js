
require.config({
    // urlArgs: 'v=' + siteConfig.VERSION,
    urlArgs: (function () {
        if (siteConfig.DEBUG == 'True')
            return 'v=' + Math.random();
        return 'v=' + siteConfig.VERSION;
    }()),
    baseUrl: siteConfig.STATIC_URL,
    waitSeconds: 0,
    packages: [{
        name: "codemirror",
        location: siteConfig.STATIC_URL + "codemirror",
        main: "lib/codemirror"
    }],
    paths: {

        // Third party:
        admin_lte: siteConfig.STATIC_URL + 'adminlte/js/admin-lte',
        admin_lte_config: siteConfig.STATIC_URL + 'adminlte/js/admin-lte-config',
        autosize: siteConfig.STATIC_URL + 'autosize/js/autosize.min',
        bootstrap: siteConfig.STATIC_URL + 'bootstrap/js/bootstrap.min',
        cheekycheck: siteConfig.STATIC_URL + 'cheekycheck/js/cheekycheck',
        codemirror: siteConfig.STATIC_URL + 'codemirror/lib/codemirror',
        d3: siteConfig.STATIC_URL + 'd3/js/d3',
        c3: siteConfig.STATIC_URL + 'c3/js/c3.min',
        explorer: siteConfig.STATIC_URL + 'explorer/js/explorer',
        'explorer.queryList': siteConfig.STATIC_URL + 'explorer/js/query-list',
        qatexplorer: siteConfig.STATIC_URL + 'explorer/js/qat-explorer',
        saveSvgAsPng: siteConfig.STATIC_URL + 'd3/js/saveSvgAsPng',
        canvg: siteConfig.STATIC_URL + 'd3/js/canvg',
        rgbcolor: siteConfig.STATIC_URL + 'd3/js/rgbcolor.min',
        'stackblur-canvas': siteConfig.STATIC_URL + 'd3/js/stackblur.min',

        /* listable data tables */
        datatables: siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.min',
        'datatables.bootstrap': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.bootstrap',
        'datatables.columnFilter': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.columnFilter',
        'datatables.searchPlugins': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.searchPlugins',
        'datatables.sort': siteConfig.STATIC_URL + 'listable/js/jquery.dataTables.sort',

        datepicker: siteConfig.STATIC_URL + 'datepicker/js/bootstrap-datepicker.min',
        daterangepicker: siteConfig.STATIC_URL + 'daterangepicker/js/daterangepicker',
        dropzone: siteConfig.STATIC_URL + 'dropzone/js/dropzone-amd-module',
        felter: siteConfig.STATIC_URL + 'felter/js/felter',
        flatpickr: siteConfig.STATIC_URL + 'flatpickr/js/flatpickr.min',
        floatthead: siteConfig.STATIC_URL + 'floatthead/js/jquery.floatThead.min',
        icheck: siteConfig.STATIC_URL + 'icheck/js/icheck.min',
        inputmask: siteConfig.STATIC_URL + 'inputmask/js/jquery.inputmask.bundle.min',
        jquery: siteConfig.STATIC_URL + 'jquery/js/jquery.min',
        "qatrack-jquery": siteConfig.STATIC_URL + 'jquery/js/qatrack-jquery',
        'jquery-ui': siteConfig.STATIC_URL + 'jqueryui/js/jquery-ui.min',
        'jquery-ui-sql': siteConfig.STATIC_URL + 'explorer/js/jquery-ui.min',
        'jquery-cookie': siteConfig.STATIC_URL + 'explorer/js/jquery.cookie.min',
        json2: siteConfig.STATIC_URL + 'json2/js/json2',
        list: siteConfig.STATIC_URL + 'list/js/list.min',
        listable: siteConfig.STATIC_URL + 'listable/js/listable',
        lodash: siteConfig.STATIC_URL + 'lodash/js/lodash',
        moment: siteConfig.STATIC_URL + 'moment/js/moment.min',
        moment_timezone: siteConfig.STATIC_URL + 'moment/js/moment-timezone-with-data.min',
        pivottable: siteConfig.STATIC_URL + 'pivottable/',
        multiselect: siteConfig.STATIC_URL + 'multiselect/js/bootstrap.multiselect',
        select2: siteConfig.STATIC_URL + 'select2/js/select2.min',
        slimscroll: siteConfig.STATIC_URL + 'slimscroll/js/jquery.slimscroll.min',
        zxcvbn: siteConfig.STATIC_URL + 'zxcvbn_password/js/zxcvbn',
        password_strength: siteConfig.STATIC_URL + 'zxcvbn_password/js/password_strength',
        vue: siteConfig.STATIC_URL + 'vue/js/vue.min',
        treeview: siteConfig.STATIC_URL + 'treeview/js/bootstrap-treeview.min',

        // Site wide:
        sidebar: siteConfig.STATIC_URL + 'qatrack_core/js/sidebar',
        site_base: siteConfig.STATIC_URL + 'qatrack_core/js/base',
        comments: siteConfig.STATIC_URL + 'qatrack_core/js/comments',
        ping: siteConfig.STATIC_URL + 'qatrack_core/js/ping',
        listablestatic: siteConfig.STATIC_URL + 'qatrack_core/js/listableStatic',

        // accounts module:
        groups: siteConfig.STATIC_URL + 'accounts/js/groups',

        // homepage
        homepage: siteConfig.STATIC_URL + 'qatrack_core/js/homepage',

        // reports module:
        reports: siteConfig.STATIC_URL + 'reports/js/reports',

        // qa module:
        qa: siteConfig.STATIC_URL + 'qa/js/qa',
        qacharts: siteConfig.STATIC_URL + 'qa/js/qacharts',
        qautils: siteConfig.STATIC_URL + 'qa/js/qautils',
        qareview: siteConfig.STATIC_URL + 'qa/js/qareview',
        qabulkreview: siteConfig.STATIC_URL + 'qa/js/qabulkreview',
        qaoverview: siteConfig.STATIC_URL + 'qa/js/qaoverview',

        // unit module:
        unit_avail: siteConfig.STATIC_URL + 'units/js/unit_available_time',
        unit_list: siteConfig.STATIC_URL + 'units/js/unit_list',
        unit_choose: siteConfig.STATIC_URL + 'units/js/unit_choose',

        // service log module
        sl_dash: siteConfig.STATIC_URL + 'service_log/js/sl_dash',
        sl_se: siteConfig.STATIC_URL + 'service_log/js/sl_serviceevent',
        sl_se_delete: siteConfig.STATIC_URL + 'service_log/js/sl_se_delete',
        sl_se_details:siteConfig.STATIC_URL + 'service_log/js/sl_serviceevent_details',
        sl_utils: siteConfig.STATIC_URL + 'service_log/js/sl_utils',
        service_event_down_time_list: siteConfig.STATIC_URL + 'service_log/js/service_event_down_time_list',
        down_time_summary: siteConfig.STATIC_URL + 'service_log/js/down_time_summary',
        sl_se_template: siteConfig.STATIC_URL + 'service_log/js/sl_se_template',

        //parts module:
        p_part: siteConfig.STATIC_URL + 'parts/js/p_part',
        parts_reporting: siteConfig.STATIC_URL + 'parts/js/parts_reporting',

        //faults module:
        faults: siteConfig.STATIC_URL + 'faults/js/faults',
        faultsbulkreview: siteConfig.STATIC_URL + 'faults/js/faultsbulkreview',

        //issue module:
        issues: siteConfig.STATIC_URL + 'issue_tracker/js/issues'
    },
    shim: {
        // Third party:
        admin_lte: {
            deps: ['jquery', 'bootstrap', 'slimscroll', 'admin_lte_config']
        },
        bootstrap: {
            deps: ['jquery']
        },
        codemirror: {
            exports: 'CodeMirror'
        },
        /* listable data tables */
        datatables: {
            deps: ['jquery'],
            exports: 'dataTable'
        },
        'datatables.bootstrap': {
            deps: ['datatables']
        },
        'datatables.columnFilter': {
            deps: ['datatables']
        },
        'datatables.searchPlugins': {
            deps: ['datatables']
        },
        'datatables.sort': {
            deps: ['datatables']
        },

        datepicker: {
            deps: ['jquery', 'bootstrap']
        },
        daterangepicker: {
            exports: 'DateRangePicker',
            deps: ['jquery', 'moment']
        },
        explorer: {
            deps: [
                'jquery',
                'jquery-ui-sql',
                'bootstrap',
                'jquery-cookie',
                'lodash',
                'list',
                'codemirror',
                'floatthead',
                'pivottable/pivot.min',
                'pivottable/d3_renderers.min',
                'pivottable/c3_renderers.min',
                'qatexplorer'
            ]
        },
        flatpickr: {
            exports: 'Flatpickr',
            deps: ['jquery']
        },
        floatthead: {
            deps: ['jquery']
        },
        icheck: {
            deps: ['jquery']
        },
        inputmask: {
            deps: ['jquery']
        },
        jquery: {
            exports: '$'
        },
        "jquery-cookie": {
            deps: ['jquery']
        },
        "qatrack-jquery": {
            deps: ['jquery']
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
        password_strength: {
            deps: ['jquery']
        },
        'pivottable/pivot': ['jquery', 'jqueryui'],
        'pivottable/d3_renderers': ['pivottable/pivot', 'd3'],
        'pivottable/c3_renderers': ['pivottable/pivot', 'c3'],
        'pivottable/export_renderers': ['pivottable/pivot'],
        saveSvgAsPng: {
            deps: ['canvg'],
            exports: 'saveSvgAsPng'
        },
        canvg: {
            exports: 'canvg',
            deps: ['rgbcolor', 'stackblur-canvas']
        },
        slimscroll: {
            deps: ['jquery']
        },
        treeview: {
            deps: ['jquery', 'lodash']
        },
        zxcvbn: {
            deps: ['jquery']
        },

        // Site wide:
        site_base: {
            deps: ['jquery']
        },

        listablestatic: {
            deps: ['jquery', 'datatables', 'datatables.columnFilter', 'datatables.searchPlugins', 'datatables.sort', 'datatables.bootstrap', 'multiselect', 'datepicker', 'daterangepicker']
        },

        // accounts module:
        groups: {
            deps: ['vue']
        },

        homepage: {
            deps: ['jquery', 'treeview']
        },

        // reports module:
        reports: {
            deps: ['jquery', 'lodash', 'moment', 'select2', 'jquery-ui', 'datepicker', 'daterangepicker']
        },

        // qa module:
        qa: {
            deps: ['jquery', 'qautils', 'site_base', 'lodash', 'daterangepicker', 'sidebar', 'datatables', 'datatables.columnFilter', 'inputmask', 'select2', 'sl_utils', 'flatpickr', 'ping']
        },

        // service_log module
        sl_utils: {
            deps: ['jquery', 'site_base', 'bootstrap']
        }

    },
    map: {
        'reports': {
            'datatables': 'datatables/1.10/datatables.min.js',
        },
        '*': {
            'datatables.net': siteConfig.STATIC_URL + 'datatables/1.10/js/datatables.min.js',
            'datatables.net-bs': siteConfig.STATIC_URL + 'datatables/1.10/DataTables-1.10.18/js/dataTables.bootstrap.min.js',

            /* when any module requests jquery give it qatrack-jquery instead.
             * qatrack-jquery sets up ajax calls with the Django CSRF token */
            'jquery': 'qatrack-jquery'
        },
        'qatrack-jquery': {
            /* when qatrack-jquery requires jquery, give it the real deal */
            jquery: 'jquery'
        }
    }
});

require(['jquery', 'bootstrap', 'admin_lte', 'json2', 'site_base'], function($) {
    $(document).ready(function() {
      $("body").removeClass("preload");
    });

});
