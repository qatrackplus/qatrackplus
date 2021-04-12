require(['jquery', 'lodash', 'saveSvgAsPng', 'select2'], function ($, _, saveSvgAsPng, select2) {

    function downloadCSV(csv, filename) {

        var csvFile;
        var downloadLink;

        csvFile = new Blob([csv], {type: "text/csv"});

        downloadLink = document.createElement("a");
        downloadLink.download = filename;
        downloadLink.href = window.URL.createObjectURL(csvFile);
        downloadLink.style.display = "none";
        document.body.appendChild(downloadLink);
        downloadLink.click();
    }


    $(".pvtAggregator").on("change", function(){
        setTimeout(function(){
            $(".pvtAttrDropdown").addClass("form-control");
        }, 100);
    });

    $(".pvtRenderer,.pvtAggregator").addClass("form-control");

    $("#save-image").click(function(){

        var svg = $("svg");

        if (svg.length === 0){
            return;
        }

        saveSvgAsPng.saveSvgAsPng(svg.get(0), "plot.png", {
            scale: 1,
            backgroundColor: "#FFFFFF",
            canvg: window.canvg,
            selectorRemap: function(s){
                return s.replace(/\.c3 /g, '');
            }
        });
    });

    $("#export-csv").click(function(){

        var csv = [];
        var rows = document.querySelectorAll(".pvtTable tr");

        for (var i = 0; i < rows.length; i++) {
            var row = [], cols = rows[i].querySelectorAll("td, th");

            for (var j = 0; j < cols.length; j++)
                row.push(cols[j].innerText);

            csv.push(row.join(","));
        }

        // Download CSV file
        downloadCSV(csv.join("\n"), "export.csv");
    });

});
