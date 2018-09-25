var tables = ["testlistcycles", "testlists", "tests"];
var dataTables = {};

function setSelected(type, selected){
    var all = selected.length > 0 && dataTables[type].column(0).data().length === selected.length
    $("#"+type + "-summary").html(all ? "All" : selected.length + " Selected");
    var val;
    if (all){
      val = "all";
    } else {
      val = JSON.stringify(selected);
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
            var data = dt.rows({selected: true}).data().pluck(0).toArray();
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

  $("#version").text(meta.version);
  $("#name").text(meta.name);
  $("#created-by").text(meta.contact);
  $("#description").text(meta.description);
  var models = ["tests", "testlists", "testlistcycles"];
  var model_map = {'tests': 'qa.test' , 'testlists': 'qa.testlist' , 'testlistcycles': 'qa.testlistcycle'};
  var objects_to_imp = {'tests': [], 'test_lists': [], 'test_list_cycles': []};
  _.each(models, function(model){
        var objects = _.map(tpk.objects[model], function(o){return JSON.parse(o);});
        var objects_to_imp = [];
        var table = dataTables[model];
        var converter = converters[model];
        _.each(objects, function(model_objects){
            table.row.add([model_objects.key].concat(converter(model_objects['object'])));
        });
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
