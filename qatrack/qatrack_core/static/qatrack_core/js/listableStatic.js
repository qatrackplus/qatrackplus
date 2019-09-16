function listableStatic(Listable, moment){

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '' && name) {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var table = $(Listable.tableId).addClass(
        Listable.cssTableClass
    ).dataTable({
        aaSorting: Listable.order,
        aoColumns: Listable.columnDefs,
        bAutoWidth: Listable.autoWidth,
        bFilter: true,
        bPaginate: Listable.paginate,
        bProcessing: false,
        bServerSide: false,
        bStateSave: Listable.stateSave,
        iDisplayLength: Listable.displayLength,
        sCookiePrefix: Listable.cookiePrefix,
        sDom: Listable.DOM,
        sPaginationType: Listable.paginationType
    }).columnFilter({
        sPlaceHolder: "head:after",
        aoColumns: Listable.columnFilterDefs,
        iFilteringDelay: 250
    });

    var cookie_obj = JSON.parse(/*window.*/getCookie(Listable.cookie));

    if (cookie_obj) {
        for (var i in cookie_obj.aoSearchCols) {
            var searcher = cookie_obj.aoSearchCols[i].sSearch;
            if (searcher.charAt(0) == '^') {
                searcher = searcher.replace('^(', '').replace(')$', '');
                if (searcher != '.*') {
                    var c = parseInt(i) + 1;
                    var searchers = searcher.split('|');
                    var select = $("thead > tr > th:nth-child(" + c + ") select");
                    for (var j in searchers) {
                        var option = $(select).children("option[value='" + searchers[j] + "']");
                        $(option).attr('selected', 'selected');
                    }
                }
            }
        }
    }
    $("option.search_init").text('-----');

    var available_ranges = {
        "Today": [
            moment(),
            moment()
        ],
        "Yesterday": [
            moment().subtract(1, 'days'),
            moment().subtract(1, 'days')
        ],
        "Tomorrow": [
            moment().add(1, 'days'),
            moment().add(1, 'days')
        ],
        "Last 7 Days": [
            moment().subtract(7, 'days'),
            moment()
        ],
        "Last 14 Days": [
            moment().subtract(14, 'days'),
            moment()
        ],
        "Last 30 Days": [
            moment().subtract(30, 'days'),
            moment()
        ],
        "Last 365 Days": [
            moment().subtract(365, 'days'),
            moment()
        ],
        "This Week": [
            moment().startOf('week'),
            moment().endOf('week')
        ],
        "This Month": [
            moment().startOf('month'),
            moment().endOf('month')
        ],
        "This Quarter": [
            moment().startOf('quarter'),
            moment().endOf('quarter')
        ],
        "This Year": [
            moment().startOf('year'),
            moment().endOf('year')
        ],
        "Last Week": [
            moment().subtract(1, 'weeks').startOf('week'),
            moment().subtract(1, 'weeks').endOf('week')
        ],
        "Last Month": [
            moment().subtract(1, 'months').startOf('month'),
            moment().subtract(1, 'months').endOf('month')
        ],
        "Last Quarter": [
            moment().subtract({months: (moment().month() % 3) + 1}).subtract({months: 3}).startOf('month'),
            moment().subtract({months: (moment().month() % 3) + 1}).endOf('month')
        ],
        "Last Year": [
            moment().subtract(1, 'years').startOf('year'),
            moment().subtract(1, 'years').endOf('year')
        ],
        "Week To Date": [
            moment().startOf('week'),
            moment()
        ],
        "Month To Date": [
            moment().startOf('month'),
            moment()
        ],
        "Quarter To Date": [
            moment().startOf('quarter'),
            moment()
        ],
        "Year To Date": [
            moment().startOf('year'),
            moment()
        ],
        "Next Week": [
            moment().add(1, 'weeks').startOf('week'),
            moment().add(1, 'weeks').endOf('week')
        ],
        "Next Month": [
            moment().add(1, 'months').startOf('month'),
            moment().add(1, 'months').endOf('month')
        ],
        "Next Quarter": [
            moment().add({months: (moment().month() % 3) + 1}).subtract({months: 3}).startOf('month'),
            moment().add({months: (moment().month() % 3) + 1}).endOf('month')
        ],
        "Next Year": [
            moment().add(1, 'years').startOf('year'),
            moment().add(1, 'years').endOf('year')
        ]
    };

    var date_range_locale = {
        "format": siteConfig.DATERANGEPICKER_DATE_FMT,
        "separator": " - ",
        "applyLabel": "Apply",
        "cancelLabel": "Clear",
        "fromLabel": "From",
        "toLabel": "To",
        "customRangeLabel": "Custom",
        "weekLabel": "W",
        "daysOfWeek": [
            "Su",
            "Mo",
            "Tu",
            "We",
            "Th",
            "Fr",
            "Sa"
        ],
        "monthNames": [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December"
        ],
        "firstDay": 1
    };

    for (var col in Listable.columnFilterDefs) {
        if (Listable.columnFilterDefs[col]) {
            if (Listable.columnFilterDefs[col].type == 'select') {
                var c = parseInt(col) + 1;
                var select = $("thead > tr > th:nth-child(" + c + ") select");
                if (Listable.columnFilterDefs[col].multiple) {
                    $(select)
                        .attr('multiple', 'multiple')
                        .multiselect({
                            includeSelectAllOption: true,
                            numberDisplayed: 1,
                            nonSelectedText: '------'
                        });
                } else {
                    $(select).attr('multiple', false).multiselect({});
                }
                // $(select).multiselect();
            }
            else if (Listable.columnFilterDefs[col].type == 'daterange') {

                var c = parseInt(col) + 1;
                var date_range = $("thead > tr > th:nth-child(" + c + ") input");
                date_range.hide();
                var inital_display = date_range.val();
                if (date_range.hasClass('search_init')) {
                    date_range.val('');
                    inital_display = '------';
                }
                var $input_div = $(
                    '<div id="daterange-div-' + c + '" class="btn-group daterange-div">\n' +
                    '    <button class="daterange-inner btn btn-default"><span class="daterange-val-display">' + inital_display + '</span> <b class="caret"></b></button>\n' +
                    '</div>'
                );
                date_range.after($input_div);

                var opens;
                var left_offset = $(date_range).offset().left;
                left_offset > 800 ? opens = 'left' : left_offset > 400 ? opens = 'center' : opens = 'right';

                var ranges = {};
                for (var r in Listable.columnFilterDefs[col].ranges) {
                    var range = Listable.columnFilterDefs[col].ranges[r];
                    ranges[range] = available_ranges[range]
                }

                $($input_div).daterangepicker({
                    autoUpdateInput: false,
                    "ranges": ranges,
                    "showDropdowns": true,
                    "linkedCalendars": false,
                    "locale": date_range_locale,
                    "opens": opens
                }, function (start_date, end_date) {
                    var div = $(this.element).find('.daterange-val-display');
                    var dates = start_date.format(siteConfig.MOMENT_DATE_FMT) + ' - ' + end_date.format(siteConfig.MOMENT_DATE_FMT);
                    var input = $(this.element).siblings('input');
                    input.val(dates);
                    div.html(dates);
                }).on('apply.daterangepicker', function (ev, picker) {
                    var div = $(picker.element).find('.daterange-val-display');
                    var dates = picker.startDate.format(siteConfig.MOMENT_DATE_FMT) + ' - ' + picker.endDate.format(siteConfig.MOMENT_DATE_FMT);
                    var input = $(picker.element).siblings('input');
                    var started_null = input.val() === '';
                    input.val(dates);
                    div.html(dates);
                    if (!picker.startDate.isSame(picker.oldStartDate) || !picker.endDate.isSame(picker.oldEndDate) || started_null) {
                        input.trigger('keyup');
                    }
                    $('.suppress-active').removeClass('suppress-active');
                }).on('cancel.daterangepicker', function (ev, picker) {
                    var div = $(picker.element).find('.daterange-val-display');
                    var input = $(picker.element).siblings('input');
                    div.html('------');
                    input.val('');
                    input.trigger('keyup');
                    picker.startDate = moment();
                    picker.endDate = moment();
                    $(picker.container).addClass('suppress-active');
                });

                if ($(date_range).val() === '') {
                    $($input_div.data('daterangepicker').container).addClass('suppress-active');
                }

            }
            else if (Listable.columnFilterDefs[col].type == 'date') {
                var c = parseInt(col) + 1;
                var date = $('thead > tr > th:nth-child(' + c + ') input');

                $(date).datepicker({
                    orientation: 'bottom left',
                    format: 'dd M yyyy',
                    autoclose: true,
                    clearBtn: true,
                    toggleActive: true

                }).on('changeDate', function (x) {
                    $(this).trigger('keyup');
                });
            }
        }
    }

    $(table).find("input:not(:checkbox, :radio), select, button").addClass(
        Listable.cssInputClass
    );
}
