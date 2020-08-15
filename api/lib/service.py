import os
import time
import glob
import copy
import json
import yaml
import requests
import functools
import traceback

import redis
import flask
import flask_restful
import sqlalchemy.exc

import opengui


import klotio
import klotio_flask_restful
import klotio_sqlalchemy_restful
import nandyio_people_integrations
import nandyio_chore_models

def app():

    app = flask.Flask("nandy-io-chore-api")

    app.mysql = nandyio_chore_models.MySQL()

    app.redis = redis.Redis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']))
    app.channel = os.environ['REDIS_CHANNEL']

    api = flask_restful.Api(app)

    api.add_resource(klotio_flask_restful.Health, '/health')
    api.add_resource(Group, '/group')
    api.add_resource(TemplateCL, '/template')
    api.add_resource(TemplateRUD, '/template/<int:id>')
    api.add_resource(AreaCL, '/area')
    api.add_resource(AreaRUD, '/area/<int:id>')
    api.add_resource(AreaA, '/area/<int:id>/<action>')
    api.add_resource(ActCL, '/act')
    api.add_resource(ActRUD, '/act/<int:id>')
    api.add_resource(ActA, '/act/<int:id>/<action>')
    api.add_resource(ToDoCL, '/todo')
    api.add_resource(ToDoRUD, '/todo/<int:id>')
    api.add_resource(ToDoA, '/todo/<int:id>/<action>')
    api.add_resource(RoutineCL, '/routine')
    api.add_resource(RoutineRUD, '/routine/<int:id>')
    api.add_resource(RoutineA, '/routine/<int:id>/<action>')
    api.add_resource(TaskA, '/routine/<int:routine_id>/task/<int:task_id>/<action>')

    app.logger = klotio.logger(app.name)

    app.logger.debug("init", extra={
        "init": {
            "redis": {
                "connection": str(app.redis),
                "channel": app.channel
            },
            "mysql": {
                "connection": str(app.mysql.engine.url)
            }
        }
    })

    return app


class Group(klotio_flask_restful.Group):
    APP = "chore.nandy.io"


class Template(klotio_sqlalchemy_restful.Model):

    SINGULAR = "template"
    PLURAL = "templates"
    MODEL = nandyio_chore_models.Template
    ORDER = [nandyio_chore_models.Template.name]

    FIELDS = [
        {
            "name": "name"
        },
        {
            "name": "kind",
            "options": [
                "area",
                "act",
                "todo",
                "routine"
            ],
            "style": "radios",
            "trigger": True
        }
    ]

    @classmethod
    def integrations(cls, form):

        integrations = []

        if form in ["template", "area", "act", "todo", "routine"]:
            integrations.extend(klotio.integrations(form))

        return integrations

    @classmethod
    def request(cls, converted):

        values = {}

        integrations = opengui.Fields({}, {}, cls.integrations(converted.get("kind", "template")))

        for field in converted.keys():

            if field in integrations.names:
                values.setdefault("data", {})
                values["data"][field] = converted[field]
            elif field != "yaml":
                values[field] = converted[field]

        if "yaml" in converted:
            values.setdefault("data", {})
            values["data"].update(yaml.safe_load(converted["yaml"]))

        if "data" in converted:
            values.setdefault("data", {})
            values["data"].update(converted["data"])

        return values

    @classmethod
    def response(cls, model):

        converted = {
            "data": {}
        }

        integrations = opengui.Fields({}, {}, cls.integrations(model.kind or "template"))

        for field in model.__table__.columns._data.keys():
            if field != "data":
                converted[field] = getattr(model, field)

        for field in model.data:
            if field in integrations.names:
                converted[field] = model.data[field]
            else:
                converted["data"][field] = model.data[field]

        converted["yaml"] = yaml.safe_dump(dict(converted["data"]), default_flow_style=False)

        return converted

    @classmethod
    def choices(cls, kind):

        ids = []
        labels = {}

        for model in flask.request.session.query(
            cls.MODEL
        ).filter_by(
            kind=kind
        ).order_by(
            *cls.ORDER
        ).all():
            ids.append(model.id)
            labels[model.id] = model.name

        flask.request.session.commit()

        return (ids, labels)

    @staticmethod
    def form(values, originals):

        if values and "kind" in values:
            return values["kind"]

        if originals and "kind" in originals:
            return originals["kind"]

        return "template"

class TemplateCL(Template, klotio_sqlalchemy_restful.ModelCL):

    @classmethod
    def fields(cls, values=None, originals=None):

        return opengui.Fields(values, originals=originals, fields=copy.deepcopy(cls.FIELDS + cls.integrations(cls.form(values, originals)) + cls.YAML))

class TemplateRUD(Template, klotio_sqlalchemy_restful.ModelRUD):

    @classmethod
    def fields(cls, values=None, originals=None):

        return opengui.Fields(values, originals=originals, fields=copy.deepcopy(cls.ID + cls.FIELDS + cls.integrations(cls.form(values, originals)) + cls.YAML))



class Status(klotio_sqlalchemy_restful.Model):

    @classmethod
    def build(cls, **kwargs):
        """
        Builds complete fields from a raw fields, template, template id, etc.
        """

        fields = {
            "data": {}
        }

        data = {}

        if "template" in kwargs and isinstance(kwargs["template"], dict):

            data = kwargs["template"]

        else:

            template = None

            if "template_id" in kwargs:
                template = flask.request.session.query(
                    nandyio_chore_models.Template
                ).get(
                    kwargs["template_id"]
                )

            elif "template" in kwargs:
                template = flask.request.session.query(
                    nandyio_chore_models.Template
                ).filter_by(
                    kind=cls.SINGULAR,
                    name=kwargs["template"]
                )[0]

            if template:
                data = template.data
                if "name" not in data:
                    data["name"] = template.name

        if data:
            fields["data"].update(copy.deepcopy(data))

        if "data" in kwargs:
            fields["data"].update(copy.deepcopy(kwargs["data"]))

        person = kwargs.get("person", fields["data"].get("person"))

        if person:
            fields["person_id"] = nandyio_people_integrations.Person.model(name=person)["id"]

        for field in ["person_id", "name", "status", "created", "updated"]:
            if field in kwargs:
                fields[field] = kwargs[field]
            elif field in fields["data"]:
                fields[field] = fields["data"][field]

        return fields

    @classmethod
    def notify(cls, action, model):
        """
        Notifies something happened
        """

        model.data["notified"] = time.time()
        model.updated = time.time()

        klotio_sqlalchemy_restful.notify({
            "kind": cls.SINGULAR,
            "action": action,
            cls.SINGULAR: cls.response(model),
            "person": nandyio_people_integrations.Person.model(id=model.person_id)
        })

    @classmethod
    def create(cls, **kwargs):

        model = cls.MODEL(**cls.build(**kwargs))
        flask.request.session.add(model)
        flask.request.session.commit()

        cls.notify("create", model)

        return model


class StatusCL(klotio_sqlalchemy_restful.ModelCL):

    FIELDS = [
        {
            "name": "status",
            "style": "radios"
        },
        {
            "name": "template_id",
            "label": "template",
            "style": "select",
            "optional": True,
            "trigger": True
        },
        {
            "name": "name"
        }
    ]

    @classmethod
    def fields(cls, values=None, originals=None):

        fields = opengui.Fields(values, originals=originals, fields=nandyio_people_integrations.Person.fields() + cls.FIELDS + cls.integrations() + cls.YAML)

        fields["status"].options = cls.STATUSES
        fields["template_id"].options, fields["template_id"].content["labels"] = Template.choices(cls.SINGULAR)

        if fields["template_id"].value:

            template = Template.response(TemplateRUD.retrieve(fields["template_id"].value))

            fields["name"].value = template["name"]
            fields["yaml"].value = template["yaml"]

        return fields

    @klotio_flask_restful.logger
    @klotio_sqlalchemy_restful.session
    def post(self):

        model = self.create(**self.request(flask.request.json[self.SINGULAR]))

        return {self.SINGULAR: self.response(model)}, 201

    @klotio_flask_restful.logger
    @klotio_sqlalchemy_restful.session
    def get(self):

        since = None
        filter_by = {}

        for name, value in flask.request.args.to_dict().items():
            if name == "since":
                since = float(value)
            else:
                filter_by[name] = value

        models = flask.request.session.query(
            self.MODEL
        ).filter_by(
            **filter_by
        )

        if since is not None:
            models = models.filter(
                self.MODEL.updated>time.time()-since*60*60*24
            )

        models = models.order_by(
            *self.ORDER
        ).all()

        flask.request.session.commit()

        return {self.PLURAL: self.responses(models)}

class StatusRUD(klotio_sqlalchemy_restful.ModelRUD):

    FIELDS = [
        {
            "name": "status",
            "style": "radios"
        },
        {
            "name": "name"
        },
        {
            "name": "created",
            "style": "datetime",
            "readonly": True
        },
        {
            "name": "updated",
            "style": "datetime",
            "readonly": True
        }
    ]

    @classmethod
    def fields(cls, values=None, originals=None):

        fields = opengui.Fields(values, originals=originals, fields=cls.ID + nandyio_people_integrations.Person.fields() + cls.FIELDS + cls.integrations() + cls.YAML)

        fields["status"].options = cls.STATUSES

        return fields

class StatusA(flask_restful.Resource):

    @klotio_flask_restful.logger
    @klotio_sqlalchemy_restful.session
    def patch(self, id, action):

        model = flask.request.session.query(self.MODEL).get(id)

        if action in self.ACTIONS:

            updated = getattr(self, action)(model)

            if updated:
                flask.request.session.commit()

            return {"updated": updated}, 202


class Value(Status):

    STATUSES = ['positive', 'negative']
    ACTIONS = ["right", "wrong"]

    @classmethod
    def wrong(cls, model):
        """
        Wrongs a model
        """

        if model.status == "positive":

            model.status = "negative"
            cls.notify("wrong", model)

            return True

        return False

    @classmethod
    def right(cls, model):
        """
        Rights a model
        """

        if model.status == "negative":

            model.status = "positive"
            cls.notify("right", model)

            return True

        return False


class Area(Value):

    SINGULAR = "area"
    PLURAL = "areas"
    MODEL = nandyio_chore_models.Area
    ORDER = [nandyio_chore_models.Area.name]

    @classmethod
    def wrong(cls, model):
        """
        Wrongs a model
        """

        if model.status == "positive":

            model.status = "negative"

            cls.notify("wrong", model)

            if "todo" in model.data:
                ToDo.create(person_id=model.person_id, data={"area": model.id}, template=model.data["todo"])

            return True

        return False

class AreaCL(Area, StatusCL):
    pass

class AreaRUD(Area, StatusRUD):
    pass

class AreaA(Area, StatusA):
    pass

class Act(Value):

    SINGULAR = "act"
    PLURAL = "acts"
    MODEL = nandyio_chore_models.Act
    ORDER = [nandyio_chore_models.Act.created.desc()]

    @classmethod
    def create(cls, **kwargs):

        model = cls.MODEL(**cls.build(**kwargs))
        flask.request.session.add(model)
        flask.request.session.commit()

        cls.notify("create", model)

        if model.status == "negative" and "todo" in model.data:
            if isinstance(model.data["todo"], dict):
                template = model.data["todo"]
            else:
                template = copy.deepcopy(model.data)
                del template["todo"]
                del template["notified"]
                template["name"] = model.name
                template["act"] = True

            ToDo.create(person_id=model.person_id, status="opened", template=template)

        return model

class ActCL(Act, StatusCL):
    pass

class ActRUD(Act, StatusRUD):
    pass

class ActA(Act, StatusA):
    pass


class State(Status):

    STATUSES = ['opened', 'closed']
    ACTIONS = ["remind", "pause", "unpause", "skip", "unskip", "complete", "uncomplete", "expire", "unexpire"]

    @classmethod
    def remind(cls, model):
        """
        Reminds a model
        """

        cls.notify("remind", model)

        return True

    @classmethod
    def pause(cls, model):
        """
        Pauses a model
        """

        if "paused" not in model.data or not model.data["paused"]:

            model.data["paused"] = True
            cls.notify("pause", model)

            return True

        return False

    @classmethod
    def unpause(cls, model):
        """
        Resumes a model
        """

        if "paused" in model.data and model.data["paused"]:

            model.data["paused"] = False
            cls.notify("unpause", model)

            return True

        return False

    @classmethod
    def skip(cls, model):
        """
        Skips a model
        """

        if "skipped" not in model.data or not model.data["skipped"]:

            model.data["skipped"] = True
            model.data["end"] = time.time()
            model.status = "closed"
            cls.notify("skip", model)

            return True

        return False

    @classmethod
    def unskip(cls, model):
        """
        Unskips a model
        """

        if "skipped" in model.data and model.data["skipped"]:

            model.data["skipped"] = False
            del model.data["end"]
            model.status = "opened"
            cls.notify("unskip", model)

            return True

        return False

    @classmethod
    def complete(cls, model):
        """
        Completes a model
        """

        if "end" not in model.data or model.status != "closed":

            model.data["end"] = time.time()
            model.status = "closed"
            cls.notify("complete", model)

            return True

        return False

    @classmethod
    def uncomplete(cls, model):
        """
        Uncompletes a model
        """

        if "end" in model.data or model.status == "closed":

            del model.data["end"]
            model.status = "opened"
            cls.notify("uncomplete", model)

            return True

        return False

    @classmethod
    def expire(cls, model):
        """
        Skips a model
        """

        if "expired" not in model.data or not model.data["expired"]:

            model.data["expired"] = True
            model.data["end"] = time.time()
            model.status = "closed"
            cls.notify("expire", model)

            return True

        return False

    @classmethod
    def unexpire(cls, model):
        """
        Unexpires a model
        """

        if "expired" in model.data and model.data["expired"]:

            model.data["expired"] = False
            del model.data["end"]
            model.status = "opened"
            cls.notify("unexpire", model)

            return True

        return False


class ToDo(State):

    SINGULAR = "todo"
    PLURAL = "todos"
    MODEL = nandyio_chore_models.ToDo
    ORDER = [nandyio_chore_models.ToDo.created.desc()]

    @classmethod
    def todos(cls, data):
        """
        Reminds all ToDos
        """

        if "person" in data:
            person = nandyio_people_integrations.Person.model(name=data["person"])
        else:
            person = nandyio_people_integrations.Person.model(id=data["person_id"])

        updated = False

        todos = []

        for todo in flask.request.session.query(
            nandyio_chore_models.ToDo
        ).filter_by(
            person_id=person["id"],
            status="opened"
        ).order_by(
            *ToDo.ORDER
        ).all():

            todo.data["notified"] = time.time()
            todo.updated = time.time()
            todos.append(todo)

        if todos:

            klotio_sqlalchemy_restful.notify({
                "kind": "todos",
                "action": "remind",
                "person": person,
                "chore-speech.nandy.io": data.get("chore-speech.nandy.io", {}),
                "todos": cls.responses(todos)
            })

            updated = True

        return updated

    @classmethod
    def complete(cls, model):
        """
        Completes a model
        """

        if "end" not in model.data or model.status != "closed":

            model.data["end"] = time.time()
            model.status = "closed"
            cls.notify("complete", model)

            if "area" in model.data:
                Area.right(flask.request.session.query(nandyio_chore_models.Area).get(model.data["area"]))

            if "act" in model.data:

                if isinstance(model.data["act"], dict):
                    template = model.data["act"]
                else:
                    template = copy.deepcopy(model.data)
                    del template["act"]
                    del template["notified"]
                    template["name"] = model.name

                Act.create(person_id=model.person_id, status="positive", template=template)

            return True

        return False

class ToDoCL(ToDo, StatusCL):

    @klotio_flask_restful.logger
    @klotio_sqlalchemy_restful.session
    def patch(self):

        updated = ToDo.todos(flask.request.json["todos"])

        if updated:
            flask.request.session.commit()

        return {"updated": updated}, 202

class ToDoRUD(ToDo, StatusRUD):
    pass

class ToDoA(ToDo, StatusA):
    pass


class Routine(State):

    SINGULAR = "routine"
    PLURAL = "routines"
    MODEL = nandyio_chore_models.Routine
    ORDER = [nandyio_chore_models.Routine.created.desc()]
    ACTIONS = State.ACTIONS + ["next"]

    @staticmethod
    def tasks(fields):
        """
        Builds a routine from a raw fields, template, template id, etc.
        """

        if fields["data"].get("todos"):

            tasks = []

            for todo in flask.request.session.query(
                nandyio_chore_models.ToDo
            ).filter_by(
                person_id=fields["person_id"],
                status="opened"
            ).order_by(
                *ToDo.ORDER
            ).all():
                tasks.append({
                    "text": todo.data.get("text", todo.name),
                    "todo": todo.id
                })

            if "tasks" in fields["data"]:
                tasks.extend(fields["data"]["tasks"])

            fields["data"]["tasks"] = tasks

        if "tasks" in fields["data"]:

            for index, task in enumerate(fields["data"]["tasks"]):
                if "id" not in task:
                    task["id"] = index

        return fields

    @classmethod
    def check(cls, routine):
        """
        Checks to see if there's tasks remaining, if so, starts one.
        If not completes the task
        """

        if "tasks" not in routine.data:
            return

        for task in routine.data["tasks"]:

            if "start" in task and "end" not in task:
                return

        for task in routine.data["tasks"]:

            if "start" not in task:
                task["start"] = time.time()

                if "paused" in task and task["paused"]:
                    Task.notify("pause", task, routine)
                else:
                    Task.notify("start", task, routine)

                return

        cls.complete(routine)

    @classmethod
    def create(cls, **kwargs):

        model = cls.MODEL(**cls.tasks(cls.build(**kwargs)))
        flask.request.session.add(model)
        flask.request.session.commit()

        model.data["start"] = time.time()
        cls.notify("create", model)

        cls.check(model)
        flask.request.session.commit()

        return model

    @classmethod
    def next(cls, routine):
        """
        Completes the current task and starts the next. This is used
        with a button press.
        """

        for task in routine.data["tasks"]:
            if "start" in task and "end" not in task:
                Task.complete(task, routine)
                return True

        return False

    @classmethod
    def remind(cls, routine):
        """
        Reminds a routine
        """

        cls.notify("remind", routine)

        return True

class RoutineCL(Routine, StatusCL):
    pass

class RoutineRUD(Routine, StatusRUD):
    pass

class RoutineA(Routine, StatusA):
    pass


class Task:

    ACTIONS = ["remind", "pause", "unpause", "skip", "unskip", "complete", "uncomplete"]

    @classmethod
    def notify(cls, action, task, routine):
        """
        Notifies somethign happened
        """

        routine.data["notified"] = time.time()
        routine.updated = time.time()
        task["notified"] = time.time()

        klotio_sqlalchemy_restful.notify({
            "kind": "task",
            "action": action,
            "task": task,
            "routine": Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(id=routine.person_id)
        })

    @classmethod
    def remind(cls, task, routine):
        """
        Reminds a task
        """

        cls.notify("remind", task, routine)

        return True

    @classmethod
    def pause(cls, task, routine):
        """
        Pauses a task
        """

        # Pause if it isn't.

        if "paused" not in task or not task["paused"]:

            task["paused"] = True
            cls.notify("pause", task, routine)

            return True

        return False

    @classmethod
    def unpause(cls, task, routine):
        """
        Resumes a task
        """

        # Resume if it's paused

        if "paused" in task and task["paused"]:

            task["paused"] = False
            cls.notify("unpause", task, routine)

            return True

        return False

    @classmethod
    def skip(cls, task, routine):
        """
        Skips a task
        """

        if "skipped" not in task or not task["skipped"]:

            task["skipped"] = True
            task["end"] = time.time()

            if "start" not in task:
                task["start"] = task["end"]

            cls.notify("skip", task, routine)

            Routine.check(routine)

            return True

        return False

    @classmethod
    def unskip(cls, task, routine):
        """
        Unskips a task
        """

        if "skipped" in task and task["skipped"]:

            task["skipped"] = False
            del task["end"]
            cls.notify("unskip", task, routine)

            Routine.uncomplete(routine)

            return True

        return False

    @classmethod
    def complete(cls, task, routine):
        """
        Completes a specific task
        """

        if "end" not in task:

            task["end"] = time.time()

            if "start" not in task:
                task["start"] = task["end"]

            cls.notify("complete", task, routine)

            Routine.check(routine)

            if "todo" in task:
                ToDo.complete(flask.request.session.query(nandyio_chore_models.ToDo).get(task["todo"]))

            return True

        return False

    @classmethod
    def uncomplete(cls, task, routine):
        """
        Undoes a specific task
        """

        if "end" in task:

            del task["end"]
            cls.notify("uncomplete", task, routine)

            Routine.uncomplete(routine)

            if "todo" in task:
                ToDo.uncomplete(flask.request.session.query(nandyio_chore_models.ToDo).get(task["todo"]))

            return True

        return False

class TaskA(Task, flask_restful.Resource):

    @klotio_flask_restful.logger
    @klotio_sqlalchemy_restful.session
    def patch(self, routine_id, task_id, action):

        routine = flask.request.session.query(nandyio_chore_models.Routine).get(routine_id)
        task = routine.data["tasks"][task_id]

        if action in self.ACTIONS:

            updated = getattr(self, action)(task, routine)

            if updated:
                flask.request.session.commit()

            return {"updated": updated}, 202
