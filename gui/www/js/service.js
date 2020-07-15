window.DRApp = new DoTRoute.Application();

DRApp.load = function (name) {
    return $.ajax({url: name + ".html", async: false}).responseText;
}

$.ajaxPrefilter(function(options, originalOptions, jqXHR) {

});

DRApp.me = $.cookie('chore-nandy-io-me');

DRApp.capitalize = function(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

DRApp.controller("Base",null,{
    rest: function(type,url,data) {
        var response = $.ajax({
            type: type,
            url: url,
            contentType: "application/json",
            data: data ? JSON.stringify(data) : (type != 'GET' ? '{}' : null),
            dataType: "json",
            async: false
        });
        if ((response.status != 200) && (response.status != 201) && (response.status != 202)) {
            alert(type + ": " + url + " failed");
            throw (type + ": " + url + " failed");
        }
        return response.responseJSON;
    },
    home: function() {
        this.application.render(this.it);
    },
    url: function(params) {
        if (params && Object.keys(params).length) {
            return "/api/" + this.singular + "?" + $.param(params);
        } else {
            return "/api/" + this.singular;
        }
    },
    id_url: function() {
        return this.url() + "/" + this.application.current.path.id;
    },
    route: function(action, id) {
        if (id) {
            this.application.go(this.singular + "_" + action, id);
        } else {
            this.application.go(this.singular + "_" + action);
        }
    },
    list: function() {
        this.it = this.rest("GET",this.url());
        this.application.render(this.it);
    },
    fields_change: function() {
        this.it = this.rest("OPTIONS",this.url(), this.fields_request());
        this.application.render(this.it);
    },
    fields_values: function(prefix, fields) {
        prefix = prefix || [];
        fields = fields || this.it.fields;
        var values = {};
        for (var index = 0; index < fields.length; index++) {
            var field = fields[index];
            if (field.fields) {
                values[field.name] = this.fields_values(prefix.concat(field.name), field.fields);
                continue;
            }
            var full_name = prefix.concat(field.name).join('-').replace(/\./g, '-');
            if (field.readonly) {
                continue
            } else if (field.options && field.style != "select") {
                if (field.multi) {
                    values[field.name] = [];
                    $("input[name='" + full_name + "']:checked").each(function () {
                        values[field.name].push($(this).val());
                    });
                } else {
                    values[field.name] = $("input[name='" + full_name+ "']:checked").val()
                }
            } else {
                values[field.name] = $('#' + full_name).val();
            }
            if (field.name == "yaml" && values[field.name] == "") {
                values[field.name] = "{}";
            }
        }
        return values;
    },
    fields_request: function() {
        var request = {};
        request[this.singular] = this.fields_values();
        return request;
    },
    create: function() {
        this.it = this.rest("OPTIONS",this.url());
        this.application.render(this.it);
    },
    create_save: function() {
        var request = this.fields_request();
        this.it = this.rest("OPTIONS",this.url(), request);
        if (this.it.hasOwnProperty('errors')) {
            this.application.render(this.it);
        } else {
            this.route("retrieve", this.rest("POST",this.url(), request)[this.singular].id);
        }
    },
    retrieve: function() {
        this.it = this.rest("OPTIONS",this.id_url());
        this.application.render(this.it);
    },
    update: function() {
        this.it = this.rest("OPTIONS",this.id_url());
        this.application.render(this.it);
    },
    update_save: function() {
        var request = this.fields_request();
        this.it = this.rest("OPTIONS",this.id_url(), request);
        if (this.it.hasOwnProperty('errors')) {
            this.application.render(this.it);
        } else {
            this.rest("PATCH",this.id_url(), request);
            this.route("retrieve", this.application.current.path.id);
        }
    },
    delete: function() {
        if (confirm("Are you sure?")) {
            this.rest("DELETE", this.id_url());
            this.route("list");
        }
    }
});

// Service

DRApp.partial("Header",DRApp.load("header"));
DRApp.partial("Form",DRApp.load("form"));
DRApp.partial("Footer",DRApp.load("footer"));

DRApp.template("Home",DRApp.load("home"),null,DRApp.partials);
DRApp.template("Fields",DRApp.load("fields"),null,DRApp.partials);
DRApp.template("Create",DRApp.load("create"),null,DRApp.partials);
DRApp.template("Retrieve",DRApp.load("retrieve"),null,DRApp.partials);
DRApp.template("Update",DRApp.load("update"),null,DRApp.partials);

DRApp.route("home","/","Home","Base","home");

// Persons

DRApp.controller("Person","Base",{
    singular: "person",
    plural: "persons",
    me: function(name) {
        DRApp.me = name;
        $.cookie('chore-nandy-io-me', DRApp.me);
        this.application.refresh();
    },
    not_me: function() {
        DRApp.me = '';
        $.cookie('chore-nandy-io-me', DRApp.me);
        this.application.refresh();
    }
});

DRApp.template("Persons",DRApp.load("persons"),null,DRApp.partials);

DRApp.route("person_list","/person","Persons","Person","list");
DRApp.route("person_create","/person/create","Create","Person","create");
DRApp.route("person_retrieve","/person/{id:^\\d+$}","Retrieve","Person","retrieve");
DRApp.route("person_update","/person/{id:^\\d+$}/update","Update","Person","update");

// Templates

DRApp.controller("Template","Base",{
    singular: "template",
    plural: "templates"
});

DRApp.template("Templates",DRApp.load("templates"),null,DRApp.partials);

DRApp.route("template_list","/template","Templates","Template","list");
DRApp.route("template_create","/template/create","Create","Template","create");
DRApp.route("template_retrieve","/template/{id:^\\d+$}","Retrieve","Template","retrieve");
DRApp.route("template_update","/template/{id:^\\d+$}/update","Update","Template","update");

// Status

DRApp.controller("Status","Base",{
    sinces: [
        7,
        30,
        90
    ],
    persons_lookup: function() {
        this.it.persons_lookup = {};
        this.it.persons = this.rest("GET","/api/person").persons;
        this.it.person_id = this.application.current.query.person_id;
        for (var person = 0; person < this.it.persons.length; person++) {
            this.it.persons_lookup[this.it.persons[person]["id"]] = this.it.persons[person]["name"];
            if (!this.it.person_id && this.it.persons[person]["name"] == DRApp.me) {
                this.it.person_id = this.it.persons[person]["id"];
            }
        }
    },
    list: function() {
        var params = {};

        this.persons_lookup();
        if (this.it.person_id && this.it.person_id != 'all') {
            params.person_id = this.it.person_id;
        }

        this.it.statuses = this.statuses;
        this.it.status = this.application.current.query.status || this.status;
        if (this.it.status && this.it.status != 'all') {
            params.status = this.it.status;
        }

        this.it.sinces = this.sinces;
        this.it.since = this.application.current.query.since || this.since;
        if (this.it.since && this.it.since != 'all') {
            params.since = this.it.since;
        }

        this.it[this.plural] = this.rest("GET",this.url(params))[this.plural];
        this.application.render(this.it);
    },
    list_change: function() {
        var params = {};
        params.person_id = $("#person_id").val();
        params.status = $("#status").val();
        params.since = $("#since").val();
        this.application.go(this.singular + '_list', params);
    },
    action: function(id, action) {
        this.rest("PATCH",this.url() + "/" + id + "/" + action);
        this.application.refresh();
    }
});

// Value

DRApp.controller("Value","Status",{
    statuses: [
        "positive",
        "negative"
    ]
});

// Status

DRApp.controller("State","Status",{
    statuses: [
        "opened",
        "closed"
    ],
    status: "opened"
});

// Areas

DRApp.controller("Area","Value",{
    singular: "area",
    plural: "areas"
});

DRApp.template("Areas",DRApp.load("areas"),null,DRApp.partials);

DRApp.route("area_list","/area","Areas","Area","list");
DRApp.route("area_create","/area/create","Create","Area","create");
DRApp.route("area_retrieve","/area/{id:^\\d+$}","Retrieve","Area","retrieve");
DRApp.route("area_update","/area/{id:^\\d+$}/update","Update","Area","update");

// Acts

DRApp.controller("Act","Value",{
    singular: "act",
    plural: "acts",
    since: 7
});

DRApp.template("Acts",DRApp.load("acts"),null,DRApp.partials);

DRApp.route("act_list","/act","Acts","Act","list");
DRApp.route("act_create","/act/create","Create","Act","create");
DRApp.route("act_retrieve","/act/{id:^\\d+$}","Retrieve","Act","retrieve");
DRApp.route("act_update","/act/{id:^\\d+$}/update","Update","Act","update");

// ToDos

DRApp.controller("ToDo","State",{
    singular: "todo",
    plural: "todos"
});

DRApp.template("ToDos",DRApp.load("todos"),null,DRApp.partials);

DRApp.route("todo_list","/todo","ToDos","ToDo","list");
DRApp.route("todo_create","/todo/create","Create","ToDo","create");
DRApp.route("todo_retrieve","/todo/{id:^\\d+$}","Retrieve","ToDo","retrieve");
DRApp.route("todo_update","/todo/{id:^\\d+$}/update","Update","ToDo","update");

// Routines

DRApp.controller("Routine","State",{
    singular: "routine",
    plural: "routines",
    retrieve: function() {
        this.it = this.rest("OPTIONS",this.id_url());
        this.it.routine = this.rest("GET",this.id_url()).routine;
        this.application.render(this.it);
    },
    task_action: function(routine_id, task_id, action) {
        this.rest("PATCH",this.url() + "/" + routine_id + "/task/" + task_id + "/" + action);
        this.application.refresh();
    }
});

DRApp.template("Routines",DRApp.load("routines"),null,DRApp.partials);

DRApp.route("routine_list","/routine","Routines","Routine","list");
DRApp.route("routine_create","/routine/create","Create","Routine","create");
DRApp.route("routine_retrieve","/routine/{id:^\\d+$}","Retrieve","Routine","retrieve");
DRApp.route("routine_update","/routine/{id:^\\d+$}/update","Update","Routine","update");
