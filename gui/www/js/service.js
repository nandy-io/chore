window.DRApp = new DoTRoute.Application();

DRApp.load = function (name) {
    return $.ajax({url: name + ".html", async: false}).responseText;
}

$.ajaxPrefilter(function(options, originalOptions, jqXHR) {

});

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
    url: function() {
        return "/api/" + this.singular;
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
    fields_input: function() {
        var input = {};
        input[this.singular] = {}
        for (var index = 0; index < this.it.fields.length; index++) {
            var field = this.it.fields[index];
            var value;
            if (field.readonly) {
                continue
            } else if (field.options && field.style != "select") {
                value = $('input[name=' + field.name + ']:checked').val();
            } else {
                value = $('#' + field.name).val();
            }
            if (value && value.length) {
                if (field.options) {
                    for (var option = 0; option < field.options.length; option++) {
                        if (value == field.options[option]) {
                            value = field.options[option];
                        }
                    }
                } 
                input[this.singular][field.name] = value;
            }
        }
        return input;
    },
    create: function() {
        this.it = this.rest("OPTIONS",this.url());
        this.application.render(this.it);
    },
    create_change: function() {
        this.it = this.rest("OPTIONS",this.url(), this.fields_input());
        this.application.render(this.it);
    },
    create_save: function() {
        var input = this.fields_input();
        this.it = this.rest("OPTIONS",this.url(), input);
        if (this.it.hasOwnProperty('errors')) {
            this.application.render(this.it);
        } else {
            this.route("retrieve", this.rest("POST",this.url(), input)[this.singular].id);
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
    update_change: function() {
        this.it = this.rest("OPTIONS",this.id_url(), this.fields_input());
        this.application.render(this.it);
    },
    update_save: function() {
        var input = this.fields_input();
        this.it = this.rest("OPTIONS",this.id_url(), input);
        if (this.it.hasOwnProperty('errors')) {
            this.application.render(this.it);
        } else {
            this.rest("PATCH",this.id_url(), input);
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
DRApp.partial("Fields",DRApp.load("fields"));
DRApp.partial("Footer",DRApp.load("footer"));

DRApp.template("Home",DRApp.load("home"),null,DRApp.partials);
DRApp.template("Create",DRApp.load("create"),null,DRApp.partials);
DRApp.template("Retrieve",DRApp.load("retrieve"),null,DRApp.partials);
DRApp.template("Update",DRApp.load("update"),null,DRApp.partials);

DRApp.route("home","/","Home","Base","home");

// Persons

DRApp.controller("Person","Base",{
    singular: "person",
    plural: "persons"
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
    persons_lookup: function() {
        var lookup = {};
        var persons = this.rest("GET","/api/person").persons;
        for (var person = 0; person < persons.length; person++) {
            lookup[persons[person]["id"]] = persons[person]["name"];
        }
        return lookup;
    },
    list: function() {
        this.it = this.rest("GET",this.url());
        this.it.persons = this.persons_lookup();
        this.application.render(this.it);
    },
    action: function(id, action) {
        this.rest("PATCH",this.url() + "/" + id + "/" + action);
        this.application.refresh();
    }
});

// Areas

DRApp.controller("Area","Status",{
    singular: "area",
    plural: "areas"
});

DRApp.template("Areas",DRApp.load("areas"),null,DRApp.partials);

DRApp.route("area_list","/area","Areas","Area","list");
DRApp.route("area_create","/area/create","Create","Area","create");
DRApp.route("area_retrieve","/area/{id:^\\d+$}","Retrieve","Area","retrieve");
DRApp.route("area_update","/area/{id:^\\d+$}/update","Update","Area","update");

// Acts

DRApp.controller("Act","Status",{
    singular: "act",
    plural: "acts"
});

DRApp.template("Acts",DRApp.load("acts"),null,DRApp.partials);

DRApp.route("act_list","/act","Acts","Act","list");
DRApp.route("act_create","/act/create","Create","Act","create");
DRApp.route("act_retrieve","/act/{id:^\\d+$}","Retrieve","Act","retrieve");
DRApp.route("act_update","/act/{id:^\\d+$}/update","Update","Act","update");

// ToDos

DRApp.controller("ToDo","Status",{
    singular: "todo",
    plural: "todos"
});

DRApp.template("ToDos",DRApp.load("todos"),null,DRApp.partials);

DRApp.route("todo_list","/todo","ToDos","ToDo","list");
DRApp.route("todo_create","/todo/create","Create","ToDo","create");
DRApp.route("todo_retrieve","/todo/{id:^\\d+$}","Retrieve","ToDo","retrieve");
DRApp.route("todo_update","/todo/{id:^\\d+$}/update","Update","Act","update");

// Routines

DRApp.controller("Routine","Status",{
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
DRApp.route("routine_update","/routine/{id:^\\d+$}/update","Update","Act","update");
