(function(){

"use strict";

require(['jquery', 'treeview'], function($){

        var tree = $("#site-qc-tree").treeview({
          data: window.tree,
          enableLinks: true,
          highlightSelected: true,
          levels: 0,
          showBorder: false,
          collapseIcon: 'fa fa-minus-square-o fa-fw fa-lg',
          expandIcon: 'fa fa-plus-square-o fa-fw fa-lg'
        });
        tree.on("nodeSelected", function(event, data){
            tree.treeview('toggleNodeExpanded', data.nodeId, true);
            tree.treeview('unselectNode', data.nodeId, true);
        });


});

})();
