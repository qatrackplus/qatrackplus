var tables = ["testlists", "testlistcycles", "tests"];
var dataTables = {};

function setSelected(type, selected){
    var all = selected.length > 0 && dataTables[type].column(0).data().length === selected.length
    $("#"+type + "-summary").html(all ? "All" : selected.length + " Selected");
    var val;
    if (all){
      val = "all";
    } else {
      val = selected.join(",");
    }
    $("input[name="+type+"]").attr("value", val);
}

var columns = [];

for (var i=0; i < tables.length; i++){
    if (i === 0 || i === 1){
        columns = [{width: "40%", "targets": 0}];
    }else{
        columns = [{width: "20%", "targets": 1}, {width: "10%", "targets": 2}, {width: "10%", "targets": 3}];
    }

    dataTables[tables[i]] = $("#"+ tables[i] + "-table").dataTable({
        buttons: [
            {extend: "selectAll", className: "button"},
            {extend: "selectNone", className: "button"},
            {
              text: 'Select Filtered',
              className: "button",
              action: function () {
                this.rows( {search:'applied'} ).select();
              }
            }
        ],
        columnDefs: columns,
        autoWidth: false,
        dom: 'Bfrtip',
        language: {
            buttons: {
                selectAll: "Select all items",
                selectNone: "Select none"
            }
          },
          pagingType: "full_numbers",
          select: "multi",
          initComplete: function(settings, json){
              $(this).parents(".tp-container").find(".loading").remove();
              $(".dt-button").removeClass("dt-button");
          }
      }).show().DataTable().on('select deselect', function ( e, dt, type, indexes ) {
          if (type === 'row') {
            var data = dt.rows({selected: true}).data().pluck(0).toArray();
            var type = $(dt.table().container()).attr("id").split("-")[0];
            setSelected(type, data);
          }
      }).column(0).visible(false);
}


