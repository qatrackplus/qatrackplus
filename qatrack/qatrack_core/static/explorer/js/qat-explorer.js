require(['jquery', 'lodash', 'saveSvgAsPng', 'select2'], function ($, _, saveSvgAsPng, select2) {

    function onElementInserted(containerSelector, elementSelector, callback) {

        var onMutationsObserved = function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    var elements = $(mutation.addedNodes).find(elementSelector);
                    for (var i = 0, len = elements.length; i < len; i++) {
                        callback(elements[i]);
                    }
                }
            });
        };

        var target = $(containerSelector)[0];
        var config = { childList: true, subtree: true };
        var MutationObserver = window.MutationObserver || window.WebKitMutationObserver;
        var observer = new MutationObserver(onMutationsObserved);
        observer.observe(target, config);

    }
    /*
    onElementInserted('body', '.pvtAttrDropdown', function(element) {
        $(element).addClass("form-control");
    });
    */
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
});
