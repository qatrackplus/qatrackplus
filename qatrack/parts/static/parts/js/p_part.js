
require(['jquery', 'lodash', 'moment', 'autosize', 'select2', 'sl_utils', 'inputmask'], function ($, _, moment, autosize) {

    $(document).ready(function () {

        var $part_category = $('#id_part_category'),
            $cost = $('#id_cost'),
            $quantity_min = $('#id_quantity_min'),
            $attachInput = $('#id_part_attachments'),
            $attach_deletes = $('.attach-delete'),
            $attach_delete_ids = $('#id_part_attachments_delete_ids'),
            $attach_names = $('#part-attachment-names');

        autosize($('textarea.autosize'));

        $part_category.select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        $cost.inputmask("numeric", {
            radixPoint: ".",
            groupSeparator: ",",
            digits: 2,
            autoGroup: true,
            prefix: '$', //No Space, this will truncate the first character
            rightAlign: false,
            allowPlus: false,
            allowMinus: false,
            oncleared: function () {
                try {
                    self.Value('$0');
                } catch(err) {
                }
            }
        });

        // Suppliers
        var $suppliers = $('.supplier').select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });

        // Storage
        var $rooms = $('.room').select2({
            minimumResultsForSearch: 10,
            width: '100%'
        });
        $rooms.change(function(a, b, c) {
            var r_id = $(this).val();
            var storage_location = $(this).closest('td').siblings().find('.location'),
                storage_field = $(this).closest('td').siblings().find('.storage_field');
            if (r_id) {
                process_location_results(r_id, storage_location);
                storage_location.prop('disabled', false);
                storage_field.prop('disabled', false);
            } else {
                storage_location.find('option').remove();
                storage_field.val('');
                storage_location.prop('disabled', true);
                storage_field.prop('disabled', true);
            }
        });
        var $old_new_location = false;
        function process_location_results(r_id, location_select, initial_val) {
            $.ajax({
                type: "GET",
                url: QAURLs.ROOM_LOCATION_SEARCHER,
                data: {r_id: r_id},
                success: function (response) {
                    var keep_new_val = false,
                        $keep_new_opt
                    ;
                    if (initial_val && initial_val.indexOf('__new__') !== -1) {
                        keep_new_val = true;
                        $keep_new_opt = $('option[value=' + initial_val + ']');
                        $old_new_location = $keep_new_opt;
                    }

                    location_select.find('option').remove();
                    location_select.append('<option value="' + response.storage_no_location + '">&lt;no specific location&gt;</option>');
                    if (keep_new_val) {
                        location_select.append($keep_new_opt);
                    } else {
                        for (var l in response.storage) {
                            if (response.storage[l][1] && response.storage[l][1].replace(/ /g, '') !== '') {
                                location_select.append('<option value="' + response.storage[l][0] + '" title="' + response.storage[l][2] + '">' + response.storage[l][1] + '</option>');
                            }
                        }
                    }
                    if (initial_val) {
                        location_select.val(initial_val);
                    }
                    location_select.change();
                },
                error: function (e, data) {
                    console.log('ErROr');
                }
            });
        }
        function template_location(data) {
            var $result = $("<span></span>");
            $result.text(data.text);

            if (data.id && data.id.indexOf('__new__') !== -1) {
                $result.append("<em> (new)</em>");
                if ($old_new_location && data.id !== $old_new_location.val()) {
                    $old_new_location.remove();
                }
            }

            return $result;
        }
        var $locations = $('.location').select2({
            templateSelection: template_location,
            createTag: function (params) {
                return {
                    id: '__new__' + params.term,
                    text: params.term,
                    newOption: true
                };
            },
            templateResult: template_location,
            tags: true,
            width: '100%'
        });
        $locations.change(function(e) {
            $(this).closest('td').siblings().find('.storage_field').val($(this).val());
        });

        $locations.each(function(i, $elem) {
            var r = $($elem).closest('td').siblings().find('.room').val();
            var initial_val = $(this).val();
            if (r) {
                process_location_results(r, $($elem), initial_val);
                $(this).prop('disabled', false);
            }
        });

        $attachInput.on("change", function(){
            var fnames = _.map(this.files, function(f){
                return '<tr><td><i class="fa fa-paperclip fa-fw" aria-hidden="true"></i>' + f.name + '</td></tr>';
            }).join("");
            $attach_names.html(fnames);
        });

        $attach_deletes.change(function() {
            var deletes = [];
            $.each($attach_deletes, function(i, v) {
                var el = $(v);
                if (el.prop('checked')) {
                    deletes.push(el.val());
                }
            });
            $attach_delete_ids.val(deletes.join(','));
        });

    });

});
