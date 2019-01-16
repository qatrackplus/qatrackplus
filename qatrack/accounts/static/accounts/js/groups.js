
require(['jquery', 'lodash', 'vue', 'jquery-ui'], function ($, _, Vue) {
    "use strict";

    var app = new Vue({
        el: '#app',
        delimiters: ['${', '}'],
        data: {
            allPermissions: window.allPermissions,
            groups: [],
            selected: null,
            groupModel: {permissions: []}
        },
        methods: {
            hasPerm: function(perm){
                return !_.isNull(this.groupModel) && this.groupModel.permissions.indexOf(perm) >= 0;
            }
        },
        computed: {
            groupDict: function(){
                var dict = {};
                _.each(this.groups, function(group){
                    dict[group.name] = group;
                });
                return dict;
            },
            selectedGroup: function() {
                /* when selected is changed, fetch data */

                var group = this.groupDict[this.selected];
                var self = this;

                if (this.selected){
                    $.ajax({
                        url: group.url,
                        method: 'GET',
                        success: function (data) {
                            self.groupModel = data;
                        },
                        error: function (error) {
                            console.log(error);
                        }
                    });
                    return group.name;
                }
                return "<em>None</em>";
            }
        },
        mounted: function () {
            var self = this;

            /* Fetch all groups for display */
            $.ajax({
                url: window.groupsUrl,
                method: 'GET',
                success: function (data) {
                    self.groups = data.results;
                },
                error: function (error) {
                    console.log(error);
                }
            });
        }
    });
});
