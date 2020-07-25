DRApp.me = $.cookie('chore-nandy-io-me');

// Me

DRApp.controller("Me","Base",{
    singular: "person",
    plural: "persons",
    list: function() {
        this.it = this.rest("GET","/people.nandy.io/person");
        this.application.render(this.it);
    },
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

DRApp.template("Me",DRApp.load("me"),null,DRApp.partials);

DRApp.route("me","/me","Me","Me","list");

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
        this.it.persons = this.rest("GET","/people.nandy.io/person").persons;
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
