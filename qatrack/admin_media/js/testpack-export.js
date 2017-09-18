var tables = ["testlistcycles", "testlists", "tests"];
var dataTables = {};

function setSelected(type, selected){
    $("#"+type + "-summary").html(selected.length + " Selected");
    $("input[name="+type+"]").attr("value", selected.join(","));
}

for (var i=0; i < tables.length; i++){

    dataTables[tables[i]] = $("#"+ tables[i] + "-table").dataTable({
        buttons: [
            {extend: "selectAll", className: "button"},
            {extend: "selectNone", className: "button"},
            {
              text: 'Select Filtered',
              className: "button",
              action: function () {
                $(this).DataTable().rows( {search:'applied'} ).select();
              }
            }
        ],
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
      }).show().DataTable().on('select', function ( e, dt, type, indexes ) {
          if (type === 'row') {
            var data = dt.rows({selected: true}).data().pluck(0).toArray();
            var type = $(dt.table().container()).attr("id").split("-")[0];
            setSelected(type, data);
          }
      }).column(0).visible(false);
}
