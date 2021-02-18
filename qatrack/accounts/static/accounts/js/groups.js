
require(['jquery', 'lodash', 'vue', 'datatables', 'jquery-ui'], function ($, _, Vue, dataTables) {

    "use strict";

    Vue.component('permission', {
        /* permissions component for toggling group permissions */
        template: "#perm-template",
        delimiters: ['${', '}'],
        props: ['code', 'name', 'description', 'active'],
        methods: {
            toggle: function(){
                /* tell parent app to toggle permission */
                this.$emit('toggle', this.code, this.active);
            }
        },
        computed: {
            icon: function(){
                // show check or x depending on whether permission is active for current group
                return this.active ? 'fa fa-check-circle fa-lg success' : 'fa fa-times-circle fa-lg danger';
            },
            title: function(){
                // update tool tip depending on whether permission is active for current group
                var addRem = this.active ? "remove" : "add";
                var toFrom = this.active ? "from" : "to";
                return "Click to " + addRem + " this permission " + toFrom + " the " + this.$parent.selectedGroup + " group";
            }
        }
    });

    var app = new Vue({
        el: '#app',
        delimiters: ['${', '}'],
        data: {
            allPermissions: window.allPermissions,
            permissionCategories: [],
            permissionIndex: {},
            groups: [],
            selected: '',
            users: [],
            newGroupName: '',
            editGroupName: '',
            groupData: {permissions: []},
            groupModalTitle: "",
            groupModalButton: "",
            groupMode: "" // is modal dialog being used to edit or create new group?
        },
        methods: {

            hasPerm: function(perm){
                // return whether currently selected group has input permission
                return !_.isNull(this.groupData) && this.groupData.permissions.indexOf(perm) >= 0;
            },

            togglePerm: function(code, active){
                // toggle input permission on server for selected group

                var self = this;

                $.ajax({
                    url: this.groupData.url,
                    method:  "PUT",
                    data: {perm: code, active: !active, type: 'perms'},
                    success: function(data){
                        var idx = self.permissionIndex[code];
                        self.permissionCategories[idx.catIdx].perms[idx.permIdx].active = !active;
                    }
                });

            },

            addGroupDialog: function(mode){
                // set up modal dialog for creating new or editing existing group

                var self = this;
                this.groupMode = mode;

                this.clearGroupStatusMessage();

                if (this.groupMode === 'edit'){
                    this.newGroupName = this.selectedGroup;
                    this.groupModalTitle = "Edit Group";
                    this.groupModalButton = "Save Group";
                    _.each(this.users, function(user){
                        if (self.groupData.user_set.indexOf(user.url) >= 0){
                            user.selected = true;
                        }
                    });
                }else{
                    this.newGroupName = '';
                    this.groupModalTitle = "Add New Group";
                    this.groupModalButton = "Add Group";
                    _.each(this.users, function(user){user.selected = false;});
                }


                $("#new-group-modal").modal('show');

            },

            clearGroupStatusMessage: function(){
                // clear group edit modal status message
                $("#group-add-msg").removeClass("text-success").removeClass("text-danger").text("");
            },

            groupModalClose: function(){
                // close dialog and clear selected users
                $("#new-group-modal").modal('hide');
            },
            updateGroup: function(){
                // save new group or update existing group

                var self = this;

                this.clearGroupStatusMessage();
                var $msg = $("#group-add-msg");

                var url;
                var method;
                var data = {
                    name: this.newGroupName,
                    user_set: _.map(this.selectedUsers, "url")
                };

                if (this.groupMode === 'edit'){
                    url = this.groupDict[this.selected].url;
                    data.type = "users";
                    method = "PUT";
                }else{
                    url = window.groupsUrl;
                    method = "POST";
                }

                $.ajax({
                    url: url,
                    data: data,
                    traditional: true, // don't add square brackets to lists
                    method: method,
                    error: function(e){
                        var msg = "";
                        if (e.responseJSON){
                            _.each(e.responseJSON, function(v, k){
                                msg += k + " : " + v;
                            });
                        } else {
                            msg = "Unable to save group, try again later";
                        }
                        $msg.removeClass("text-success").addClass("text-danger").text(msg);
                    },
                    success: function(data){

                        $msg.removeClass("text-danger").addClass("text-success").text(
                            "Saved group!"
                        );

                        self.initGroups(self.newGroupName);

                        // show success message briefly then close dialog
                        setTimeout(function(){
                                $("#new-group-modal").modal('hide');
                            },
                            500
                        );
                    }
                });
            },

            userToggle: function(user, idx){
                user.selected = !user.selected;
            },

            userSelectAll: function(){
                // select all uers in group membership table
                _.each(this.users, function(u){u.selected = true;});
            },
            userSelectNone: function(){
                // clear selection for group membership table
                _.each(this.users, function(u){u.selected = false;});
            },

            initGroups: function(selectAfter){
                // fetch current status of groups from server

                var self = this;

                /* Fetch all groups for display */
                $.ajax({
                    url: window.groupsUrl,
                    method: 'GET',
                    success: function (data) {
                        self.groups = data.results;
                        if (selectAfter){
                            self.selected = selectAfter;
                        } else if (self.groups.length > 0){
                            self.selected = self.groups[0].name;
                        }
                    },
                    error: function (error) {
                        console.log(error);
                    }
                });

                $.ajax({
                    url: window.usersUrl,
                    method: 'GET',
                    error: function(e){
                        console.log(e);
                    },
                    success: function(data){
                        self.users = _.map(data.results, function(user){
                            user.selected = false;
                            return user;
                        });
                    }
                });

            }
        },

        computed: {

            groupDict: function(){
                // lookup table for group properties based on their name
                var dict = {};
                _.each(this.groups, function(group){
                    dict[group.name] = group;
                });
                return dict;
            },

            selectedGroup: function() {
                /* when selected group is changed, fetch all data for that group */

                var self = this;

                if (this.selected){

                    var group = this.groupDict[this.selected];

                    $.ajax({
                        url: group.url,
                        method: 'GET',
                        success: function (data) {
                            self.groupData = data;
                            _.each(self.permissionCategories, function(category, catIdx){
                                var perms = category.perms;
                                _.each(perms, function(p, permIdx){
                                    var active = self.hasPerm(p.code);
                                    self.permissionCategories[catIdx].perms[permIdx].active = active;
                                });
                            });
                        },
                        error: function (error) {
                            console.log(error);
                        }
                    });
                    return group.name;
                }

                return "";
            },
            selectedUsers: function(){
                return _.filter(this.users, function(user){return user.selected;});
            }
        },

        mounted: function () {
            var self = this;

            this.initGroups();

            _.each(this.allPermissions, function(category, catIdx){
                var cat = category[0];
                var perms = category[1];
                self.permissionCategories.push({'name': cat, 'perms': []});
                _.each(perms, function(p, permIdx){
                    var active = self.hasPerm(p[0]);
                    self.permissionIndex[p[0]] = {catIdx: catIdx, permIdx: permIdx};
                    self.permissionCategories[catIdx].perms.push({
                        code: p[0],
                        name: p[1],
                        description: p[2],
                        active: false
                    });
                });
            });
            $("#new-group-modal").modal({show: false});
            $("#new-group-modal").on('shown.bs.modal', function(){
                $("#user-table tbody").scrollTop(0);
            });

            this.$userTable = $("#user-table");
        }
    });
});
