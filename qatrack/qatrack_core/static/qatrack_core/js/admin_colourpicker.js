
$(document).ready(function() {

   var $colour = $('#id_colour');
   var colour = $colour.val();
   
   $colour.before('<div id="colour_form" class="input-group colorpicker-component"><span class="input-group-addon"><i></i></span></div>');
   $colour.appendTo('#colour_form');

   $('#colour_form').colorpicker({
      color: colour,
      format: 'rgba'
   });

   $colour.after(
       '<div class="btn-group" style="margin-left: 20px;">' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(60,141,188,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(0,192,239,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(0,166,90,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(243,156,18,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(221,75,57,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(210,214,222,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(0,31,63,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(96,92,168,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(216,27,96,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(1,255,112,1);"></i></span>' +
       '    <span class="pre-set-colour input-group-addon"><i style="background-color: rgba(243,247,10,1);"></i></span>' +
       '</div>'
   );

   $('.pre-set-colour i').click(function() {
      var colour = $(this).css('background-color');
      $('#colour_form').colorpicker('setValue', colour)
   })


});

   