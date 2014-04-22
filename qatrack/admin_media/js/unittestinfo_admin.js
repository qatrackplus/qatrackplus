$(document).ready(function() {
    $("select[name='dest_unit'] > option").remove();
    $("select[name='testlist'] > option").remove();
    var tempGetTestListUrl = ADMINURLs.GETTESTLIST;
    var tempGetDestUnitUrl = ADMINURLs.GETDESTUNIT;

    GetTestLists = function() {
        $("select[name='dest_unit'] > option").remove();
        $("select[name='testlist'] > option").remove();
        var testListUrl= tempGetTestListUrl + source_unit + '/' + content_type;
        $.getJSON(testListUrl,
            function(data) {
                var dropdown = $("select[name='testlist']");
                $("select[name='testlist'] > option").remove();
                dropdown.append("<option selected='selected'>---------</option>");
                $.each(data, function() {
                    dropdown.append($("<option />").text(this));
                });

        });
    };

    GetDestUnit = function() {
        var getDestUnitUrl = tempGetDestUnitUrl + source_unit + '/' + content_type + '/' + testlist;
        $.getJSON(getDestUnitUrl,
            function(data) {
                var dropdown = $("select[name='dest_unit']");
                $("select[name='dest_unit'] > option").remove();
                $.each(data, function() {
                    dropdown.append($("<option />").text(this));
                });

        });
    };

    $("select[name='source_unit']").change(function() {
        $( "select[name='source_unit'] option:selected" ).each(function() {
            source_unit = $( this ).text();
            GetTestLists();
        });

    });

    $("select[name='content_type']").change(function() {
        $( "select[name='content_type'] option:selected" ).each(function() {
            content_type = $( this ).text();
            GetTestLists();
        });
    });

    $("select[name='testlist']").change(function() {
        $( "select[name='testlist'] option:selected" ).each(function() {
            testlist = $( this ).text();
            GetDestUnit();
        });
    });

});