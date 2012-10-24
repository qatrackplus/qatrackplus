function trim(str) {
    str = str.replace(/^\s+/, '');
    for (var i = str.length - 1; i >= 0; i--) {
        if (/\S/.test(str.charAt(i))) {
            str = str.substring(0, i + 1);
            break;
        }
    }
    return str;
}

jQuery.fn.dataTableExt.oSort['date-euro-asc'] = function(a, b) {
    if (trim(a) != '') {
        var frDatea = trim(a).split(' ');
        var frTimea = frDatea[1].split(':');
        var frDatea2 = frDatea[0].split('/');
        var x = (frDatea2[2] + frDatea2[1] + frDatea2[0] + frTimea[0] + frTimea[1] + frTimea[2]) * 1;
    } else {
        var x = 10000000000000; // = l'an 1000 ...
    }

    if (trim(b) != '') {
        var frDateb = trim(b).split(' ');
        var frTimeb = frDateb[1].split(':');
        frDateb = frDateb[0].split('/');
        var y = (frDateb[2] + frDateb[1] + frDateb[0] + frTimeb[0] + frTimeb[1] + frTimeb[2]) * 1;
    } else {
        var y = 10000000000000;
    }
    var z = ((x < y) ? -1 : ((x > y) ? 1 : 0));
    return z;
};

jQuery.fn.dataTableExt.oSort['date-euro-desc'] = function(a, b) {
    if (trim(a) != '') {
        var frDatea = trim(a).split(' ');
        var frTimea = frDatea[1].split(':');
        var frDatea2 = frDatea[0].split('/');
        var x = (frDatea2[2] + frDatea2[1] + frDatea2[0] + frTimea[0] + frTimea[1] + frTimea[2]) * 1;
    } else {
        var x = 10000000000000;
    }

    if (trim(b) != '') {
        var frDateb = trim(b).split(' ');
        var frTimeb = frDateb[1].split(':');
        frDateb = frDateb[0].split('/');
        var y = (frDateb[2] + frDateb[1] + frDateb[0] + frTimeb[0] + frTimeb[1] + frTimeb[2]) * 1;
    } else {
        var y = 10000000000000;
    }
    var z = ((x < y) ? 1 : ((x > y) ? -1 : 0));
    return z;
};

jQuery.fn.dataTableExt.oSort['uk_date-asc']  = function(a,b) {
    var ukDatea = a.split('/');
    var ukDateb = b.split('/');

    var x = (ukDatea[2] + ukDatea[1] + ukDatea[0]) * 1;
    var y = (ukDateb[2] + ukDateb[1] + ukDateb[0]) * 1;

    return ((x < y) ? -1 : ((x > y) ?  1 : 0));
};

jQuery.fn.dataTableExt.oSort['uk_date-desc'] = function(a,b) {
    var ukDatea = a.split('/');
    var ukDateb = b.split('/');

    var x = (ukDatea[2] + ukDatea[1] + ukDatea[0]) * 1;
    var y = (ukDateb[2] + ukDateb[1] + ukDateb[0]) * 1;

    return ((x < y) ? 1 : ((x > y) ?  -1 : 0));
};

jQuery.fn.dataTableExt.oSort['monthYear-sort-asc']  = function(a,b) {
    a = new Date('01 '+a);
    b = new Date('01 '+b);
    return ((a < b) ? -1 : ((a > b) ?  1 : 0));
};

jQuery.fn.dataTableExt.oSort['monthYear-sort-desc'] = function(a,b) {
    a = new Date('01 '+a);
    b = new Date('01 '+b);
    return ((a < b) ? 1 : ((a > b) ?  -1 : 0));
};

jQuery.fn.dataTableExt.oSort['day-month-year-sort-asc']  = function(a,b) {
    a = new Date(a);
    b = new Date(b);
    if ((a.toString().toLowerCase() === "invalid date") && (b.toString().toLowerCase() !== "invalid date")){
        return 1;
    }else if ((a.toString().toLowerCase() !== "invalid date") && (b.toString().toLowerCase() === "invalid date")){
        return -1;
    }else if ((a.toString().toLowerCase() === "invalid date") && (b.toString().toLowerCase() === "invalid date")){
        return 0;
    }

    return ((a < b) ? -1 : ((a > b) ?  1 : 0));
};

jQuery.fn.dataTableExt.oSort['day-month-year-sort-desc'] = function(a,b) {

    a = new Date(a);
    b = new Date(b);

    if ((a.toString().toLowerCase() === "invalid date") && (b.toString().toLowerCase() !== "invalid date")){
        return -1;
    }else if ((a.toString().toLowerCase() !== "invalid date") && (b.toString().toLowerCase() === "invalid date")){
        return 1;
    }else if ((a.toString().toLowerCase() === "invalid date") && (b.toString().toLowerCase() === "invalid date")){
        return 0;
    }
    return ((a < b) ? 1 : ((a > b) ?  -1 : 0));
};

jQuery.fn.dataTableExt.oSort['span-day-month-year-sort-asc']  = function(a,b) {
    return jQuery.fn.dataTableExt.oSort['day-month-year-sort-asc']($(a).text(),$(b).text());
};

jQuery.fn.dataTableExt.oSort['span-day-month-year-sort-desc'] = function(a,b) {
    return jQuery.fn.dataTableExt.oSort['day-month-year-sort-desc']($(a).text(),$(b).text());
};


jQuery.fn.dataTableExt.oSort['span-timestamp-asc'] = function(a,b) {

    var a = parseInt($(a).data("timestamp"));
    var b = parseInt($(b).data("timestamp"));

    return ((a < b) ? -1 : ((a > b) ?  1 : 0));
};

jQuery.fn.dataTableExt.oSort['span-timestamp-desc'] = function(a,b) {

    var a = parseInt($(a).data("timestamp"));
    var b = parseInt($(b).data("timestamp"));

    return ((a < b) ? 1 : ((a > b) ?  -1 : 0));
};

jQuery.fn.dataTableExt.oSort['null-sort-asc'] = function(a,b) {
    return 0;
};
jQuery.fn.dataTableExt.oSort['null-sort-desc'] = function(a,b) {
    return 0;
};
