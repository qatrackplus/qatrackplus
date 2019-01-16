
require(['jquery', 'lodash', 'vue', 'jquery-ui'], function ($, _, Vue) {
    "use strict";

    var app = new Vue({
        el: '#app',
        delimiters: ['${', '}'],
        data: {
            allPermissions: window.allPermissions,
            groups: [],
            selected: '',
            groupModel: {permissions: []}
        },
        methods: {
            hasPerm: function(perm){
                var res = !_.isNull(this.groupModel) && this.groupModel.permissions.indexOf(perm) >= 0
                return res;
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

                if (this.selected){

                    var group = this.groupDict[this.selected];
                    var self = this;

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
                return "";
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
                    if (self.groups.length > 0){
                        self.selected = self.groups[0].name;
                    }
                },
                error: function (error) {
                    console.log(error);
                }
            });
        }
    });
});
