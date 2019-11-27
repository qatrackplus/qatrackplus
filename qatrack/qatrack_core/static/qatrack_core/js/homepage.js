(function(){

"use strict";

require(['jquery', 'treeview'], function($){

    function initTree(id, data){

        var tree = $(id).treeview({
            data: data,
            enableLinks: true,
            highlightSelected: false,
            levels: 0,
            showBorder: false,
            collapseIcon: 'fa fa-minus-square-o fa-fw fa-lg',
            expandIcon: 'fa fa-plus-square-o fa-fw fa-lg'
        });
        tree.on("nodeSelected", function(event, data){
            tree.treeview('toggleNodeExpanded', data.nodeId, {'silent': true});
            tree.treeview('unselectNode', data.nodeId, {'silent': true});
        });

    }

    initTree("#site-cat-qc-tree", window.catTree);
    initTree("#site-freq-qc-tree", window.freqTree);
});

})();
