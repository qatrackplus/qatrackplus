
function updateRRDisplay(cal, start, end){
    var rr;
    var txt = $("#id_recurrences").val();
    var time = (new Date()).strftime("%H%M%S");

    if (txt.indexOf("DTSTART") < 0){
        txt = "DTSTART:20120101T" + time +"\n" + txt;
    }

    try {
        rr = rrule.rrulestr(txt);
    } catch (e){
        return;
    }

    var winStart = parseInt($("#id_window_start").val());
    if (!isFinite(winStart)){
        $(".classic-freq").show();
        winStart = 0;
    } else {
        $(".classic-freq").hide();
    }
    var winEnd = parseInt($("#id_window_end").val());
    if (!isFinite(winEnd)){
        winEnd = 0;
    }
    var dates = rr.between(start, end, true);
    var data = {};
    $.each(dates, function(idx, e){
        var ts = e.getTime()/1000;
        data[ts] = 1;
        for (var i=1; i <= winStart; i++){
            data[ts - i*24*60*60] = 0;
        }
        for (i=1; i <= winEnd; i++){
            data[ts + i*24*60*60] = 0;
        }

    });
    cal.update(data);

}

$(document).ready(function() {

    var isFreqList = $("#cal-1").length === 0;
    if (isFreqList){
        // only need to initialize things on create/change page
        return;
    }

    var $el = $("#id_recurrences");
    var $start = $("#id_window_start");
    var $end = $("#id_window_end");

    var curVal = $el.val();

    var newVal;

    var cal1 = new CalHeatMap();
    var start1 = new Date(new Date().getFullYear(), 0, 1);
    var end1 = new Date(new Date().getFullYear(), 6, 30);

    var cal2 = new CalHeatMap();
    var start2 = new Date(new Date().getFullYear(), 6, 1);
    var end2 = new Date(new Date().getFullYear(), 12, 31);

    var baseOpts = {
        animationDuration: 0,
        domain: "month",
        label: {
            position: 'top'
        },
        subDomain: "x_day",
        cellSize: 20,
        cellPadding: 1,
        domainPadding: 10,
        domainGutter: 10,
        range: 6,
        domainDynamicDimension: false,
        domainLabelFormat: function(date) {
            moment.locale("en");
            return moment(date).format("MMMM").toUpperCase();
        },
        subDomainTextFormat: "%d",
        displayLegend: false,
        legend: [0, 1, 2],
        legendColors: {
            base: "white",
            min: "#ffffff",
            max: "#faea25"
        },
        weekStartOnMonday: false,
        tooltip: false
    };

    var opts1 = $.extend({}, baseOpts, {itemSelector: "#cal-1", start: start1});
    var opts2 = $.extend({}, baseOpts, {itemSelector: "#cal-2", start: start2});

    cal1.init(opts1);
    cal2.init(opts2);

    function update(){
        updateRRDisplay(cal1, start1, end1);
        updateRRDisplay(cal2, start2, end2);
    }

    $start.on("input", function(){update();});
    $end.on("input", function(){update();});

    /* not sure why change events are not being triggered. Poll instead :/ */
    setInterval(function(){
        newVal = $el.val();

        if (newVal !== curVal){
            curVal = newVal;
            update();
        }

    }, 100);

    update();
});
