var tables = ["testlistcycles", "testlists", "tests"];
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
            },
            {extend: "pageLength", className: "button"},
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
      }).show().DataTable().on('select deselect', function ( e, dt, type, indexes ) {
          if (type === 'row') {
            var data = dt.rows({selected: true}).data().pluck(1).toArray();
            var type = $(dt.table().container()).attr("id").split("-")[0];
            setSelected(type, data);
          }
      }).column(0).visible(false);
}

function tpkError(msg){
  alert(msg);
}


var converters = {
  'tests': function(o){
      return [
          o.fields.name,
          o.fields.category[0],
          window.test_types[o.fields.type],
          o.fields.description
      ];
  },
  'testlists': function(o){
      return [
          o.fields.name,
          o.fields.description
      ];
  },
  'testlistcycles': function(o){
      return [
          o.fields.name,
          o.fields.description
      ];
  }
};



function loadTestPack(tpk){
  var meta = tpk.meta;
  var version = parseVersion(meta.version);
  var objects = {};
  _.map(tpk.objects, function(o){
    var data = JSON.parse(o);
    if (data.length === 0 ||
        !(data[0].model === "qa.test" || data[0].model === "qa.testlist" || data[0].model === "qa.testlistcycle")){
      return;
    }
    var model = data[0].model.replace("qa.", "") + "s";
    var table = dataTables[model];
    table.clear();
    objects[model] = [];
    var converter = converters[model];
    for (var i = 0; i < data.length; i++){
      table.row.add([i].concat(converter(data[i])));
    }
    table.draw();
    $("#"+model+"-table_wrapper .buttons-select-all").click();
  });
}

$("#id_testpack").on("change", function(e){
    var files = e.target.files;
    for (var i = 0, f; f = files[i]; i++) {

      var reader = new FileReader();

      reader.onload = (function(tpkFile) {
        return function(e) {
          var data;
          $("#id_testpack_data").val(e.target.result);
          try {
            data = JSON.parse(e.target.result);
          } catch(e){
            tpkError("Unable to read test pack. Invalid test pack file.");
            return;
          }
          loadTestPack(data);
        };
      })(f);

      reader.readAsText(f);
    }
});
