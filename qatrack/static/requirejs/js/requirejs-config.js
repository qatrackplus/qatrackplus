
require.config({
    urlArgs: (function () {
        if (SiteConfig.debug == 'True')
            return 'v=' + Math.random();
        return 'v=' + SiteConfig.VERSION;
    }()),
    baseUrl: SiteConfig.STATIC_URL,
    paths: {
        jquery: SiteConfig.STATIC_URL + 'jquery/js/jquery.min',
    },
    shim: {
        jquery: {
            exports: '$'
        },
    }
});

require(['jquery'/*, 'bootstrap', 'json2'*/]);