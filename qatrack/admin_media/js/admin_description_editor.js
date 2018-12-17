(function($){
    $(document).ready(function() {

        var element = $("#id_description"),
            js_element = $('#id_javascript');
        if (element.length > 0){
            var description = element.hide();
            description.after(
                '<div style="height:100px; " id="description-editor" class="colM aligned vLargeTextField"></div>'
            );

            description.parents(".form-row").after('<div class="form-row"><div><label>Description Preview:</label><pre id="description-preview"></pre></div></div>');

            var descriptionEditor = ace.edit("description-editor");
            var descriptionSession = descriptionEditor.getSession();
            var preview = $("#description-preview");
            preview.css('white-space', 'pre-wrap');
            preview.css('clear', 'both');
            preview.html(description.val());

            descriptionEditor.setValue(description.val());
            descriptionSession.setMode( "ace/mode/html");
            descriptionSession.setTabSize(2);
            descriptionSession.setUseSoftTabs(true);
            descriptionEditor.on('blur', function(){
                description.val(descriptionEditor.getValue());
            });

            descriptionEditor.on('change', function(){
                preview.html(descriptionEditor.getValue());
            });
            descriptionEditor.resize();

            if (js_element.length == 1) {
                var javascript = js_element.hide();
                javascript.after(
                    '<div style="height: 100px;" id="javascript-editor" class="colM aligned vLargeTextField"></div>'
                );
                var javascriptEditor = ace.edit("javascript-editor");
                var javascriptSession = javascriptEditor.getSession();

                javascriptEditor.setValue(javascript.val());
                javascriptSession.setMode("ace/mode/javascript");
                javascriptSession.setTabSize(2);
                javascriptSession.setUseSoftTabs(true);
                javascriptEditor.on('blur', function () {
                    javascript.val(javascriptEditor.getValue());
                });

                // javascriptEditor.on('change', function(){
                //     preview.html(javascriptEditor.getValue());
                // });
                javascriptEditor.resize();
            }
        }
    });
})(django.jQuery);
