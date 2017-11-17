
require(['jquery', 'moment', 'autosize', 'select2', 'sl_utils', 'inputmask'], function ($, moment, autosize) {

    $(document).ready(function () {

        var $part_category = $('#id_part_category'),
            $cost = $('#id_cost');

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
            var storage_location = $(this).closest('td').siblings().find('.location');
            if ($(this).val()) {
                process_location_results(r_id, storage_location);
                storage_location.prop('disabled', false);
            } else {
                storage_location.val('');
                storage_location.prop('disabled', true);
            }
        });
        function process_location_results(r_id, location_select, initial_val) {
            $.ajax({
                type: "GET",
                url: QAURLs.ROOM_LOCATION_SEARCHER,
                data: {r_id: r_id},
                success: function (response) {
                    location_select.find('option').remove();
                    location_select.append('<option value="' + response.storage_no_location + '">----------</option>');
                    for (var l in response.storage) {
                        if (response.storage[l][1] && response.storage[l][1].replace(/ /g, '') !== '') {
                            location_select.append('<option value="' + response.storage[l][0] + '">' + response.storage[l][1] + '</option>');
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
            })
        }
        function template_location(data) {
            var $result = $("<span></span>");
            $result.text(data.text);
            if (data.newOption) {
                $result.append("<em> (new)</em>");
            }
            return $result;
        }
        var $locations = $('.location').select2({
            // escapeMarkup: function (markup) { return markup; },
            // minimumResultsForSearch: 10,
            // templateResult: generate_related_result,
            templateSelection: template_location,
            createTag: function (params) {
                console.log(params);
                return {
                    id: '__new__' + params.term,
                    text: params.term,
                    newOption: true
                }
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
        
    });

});