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

import mysql

def app():

    app = flask.Flask("nandy-io-speech-api")

    app.mysql = mysql.MySQL()

    app.redis = redis.StrictRedis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']))
    app.channel = os.environ['REDIS_CHANNEL']

    api = flask_restful.Api(app)

    api.add_resource(Health, '/health')
    api.add_resource(PersonCL, '/person')
    api.add_resource(PersonRUD, '/person/<int:id>')
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

    return app


def require_session(endpoint):
    @functools.wraps(endpoint)
    def wrap(*args, **kwargs):

        flask.request.session = flask.current_app.mysql.session()

        try:

            response = endpoint(*args, **kwargs)

        except sqlalchemy.exc.InvalidRequestError:

            response = flask.make_response(json.dumps({
                "message": "session error",
                "traceback": traceback.format_exc()
            }))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 500

            flask.request.session.rollback()

        except Exception as exception:

            response = flask.make_response(json.dumps({"message": str(exception)}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 500

        flask.request.session.close()

        return response

    return wrap


def validate(fields):

    valid = fields.validate()

    for field in fields.order:

        if field.name != "yaml" or field.value is None:
            continue

        if not isinstance(yaml.safe_load(field.value), dict):
            field.errors.append("must be dict")
            valid = False

    return valid

def notify(message):

    flask.current_app.redis.publish(flask.current_app.channel, json.dumps(message))

class Health(flask_restful.Resource):
    def get(self):
        return {"message": "OK"}


class Model:

    YAML = [
        {
            "name": "yaml",
            "style": "textarea",
            "optional": True
        }
    ]

    @staticmethod
    def validate(fields):

        return validate(fields)

    @classmethod
    def retrieve(cls, id):

        model = flask.request.session.query(
            cls.MODEL
        ).get(
            id
        )

        flask.request.session.commit()
        return model

    @staticmethod
    def derive(integrate):

        if "url" in integrate:
            response = requests.options(integrate["url"])
        elif "node" in integrate:
            response = requests.options(f"http://{os.environ['NODE_NAME']}:8083/node", params=integrate["node"])

        response.raise_for_status()

        return response.json()

    @classmethod
    def integrate(cls, integration):

        if "integrate" in integration:
            try:
                integration.update(cls.derive(integration["integrate"]))
            except Exception as exception:
                integration.setdefault("errors", [])
                integration["errors"].append(f"failed to integrate: {exception}")

        for field in integration.get("fields", []):
            cls.integrate(field)

        return integration

    @classmethod
    def integrations(cls):

        integrations = []

        for integration_path in sorted(glob.glob(f"/opt/service/config/integration_*_{cls.SINGULAR}.fields.yaml")):
            with open(integration_path, "r") as integration_file:
                integrations.append(cls.integrate({**{"name": integration_path.split("_")[1], **yaml.safe_load(integration_file)}}))

        return integrations

    @classmethod
    def request(cls, converted):

        values = {}

        integrations = opengui.Fields({}, {}, cls.integrations())

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

        integrations = opengui.Fields({}, {}, cls.integrations())

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
    def responses(cls, models):

        return [cls.response(model) for model in models]

class RestCL(flask_restful.Resource):

    @classmethod
    def fields(cls, values=None, originals=None):

        return opengui.Fields(values, originals=originals, fields=copy.deepcopy(cls.FIELDS + cls.integrations() + cls.YAML))

    @require_session
    def options(self):

        values = flask.request.json[self.SINGULAR] if flask.request.json and self.SINGULAR in flask.request.json else None

        fields = self.fields(values)

        if values is not None and not self.validate(fields):
            return {"fields": fields.to_list(), "errors": fields.errors}
        else:
            return {"fields": fields.to_list()}

    @require_session
    def post(self):

        model = self.MODEL(**self.request(flask.request.json[self.SINGULAR]))
        flask.request.session.add(model)
        flask.request.session.commit()

        return {self.SINGULAR: self.response(model)}, 201

    @require_session
    def get(self):

        models = flask.request.session.query(
            self.MODEL
        ).filter_by(
            **flask.request.args.to_dict()
        ).order_by(
            *self.ORDER
        ).all()
        flask.request.session.commit()

        return {self.PLURAL: self.responses(models)}

class RestRUD(flask_restful.Resource):

    ID = [
        {
            "name": "id",
            "readonly": True
        }
    ]

    @classmethod
    def fields(cls, values=None, originals=None):

        return opengui.Fields(values, originals=originals, fields=copy.deepcopy(cls.ID + cls.FIELDS + cls.integrations() + cls.YAML))

    @require_session
    def options(self, id):

        originals = self.response(self.retrieve(id))

        values = flask.request.json[self.SINGULAR] if flask.request.json and self.SINGULAR in flask.request.json else None

        fields = self.fields(values or originals, originals)

        if values is not None and not self.validate(fields):
            return {"fields": fields.to_list(), "errors": fields.errors}
        else:
            return {"fields": fields.to_list()}

    @require_session
    def get(self, id):

        return {self.SINGULAR: self.response(self.retrieve(id))}

    @require_session
    def patch(self, id):

        rows = flask.request.session.query(
            self.MODEL
        ).filter_by(
            id=id
        ).update(
            self.request(flask.request.json[self.SINGULAR])
        )
        flask.request.session.commit()

        return {"updated": rows}, 202

    @require_session
    def delete(self, id):

        rows = flask.request.session.query(
            self.MODEL
        ).filter_by(
            id=id
        ).delete()
        flask.request.session.commit()

        return {"deleted": rows}, 202


class Person(Model):

    SINGULAR = "person"
    PLURAL = "persons"
    MODEL = mysql.Person
    ORDER = [mysql.Person.name]

    FIELDS = [
        {
            "name": "name"
        }
    ]

    @classmethod
    def choices(cls):

        ids = []
        labels = {}

        for model in flask.request.session.query(
            cls.MODEL
        ).filter_by(
            **flask.request.args.to_dict()
        ).order_by(
            *cls.ORDER
        ).all():
            ids.append(model.id)
            labels[model.id] = model.name

        flask.request.session.commit()

        return (ids, labels)

class PersonCL(Person, RestCL):
    pass

class PersonRUD(Person, RestRUD):
    pass


class Template(Model):

    SINGULAR = "template"
    PLURAL = "templates"
    MODEL = mysql.Template
    ORDER = [mysql.Template.name]

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
            "style": "radios"
        }
    ]

    @classmethod
    def choices(cls, kind):

        ids = [0]
        labels = {0: "None"}

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

class TemplateCL(Template, RestCL):
    pass

class TemplateRUD(Template, RestRUD):
    pass


class Status(Model):

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

            if "template_id" in kwargs and kwargs["template_id"]:
                template = flask.request.session.query(
                    mysql.Template
                ).get(
                    kwargs["template_id"]
                )

            elif "template" in kwargs:
                template = flask.request.session.query(
                    mysql.Template
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
            fields["person_id"] = flask.request.session.query(
                mysql.Person
            ).filter_by(
                name=person
            ).one().id

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

        notify({
            "kind": cls.SINGULAR,
            "action": action,
            cls.SINGULAR: cls.response(model),
            "person": Person.response(model.person)
        })

    @classmethod
    def create(cls, **kwargs):

        model = cls.MODEL(**cls.build(**kwargs))
        flask.request.session.add(model)
        flask.request.session.commit()

        cls.notify("create", model)

        return model


class StatusCL(RestCL):

    FIELDS = [
        {
            "name": "person_id",
            "label": "person",
            "style": "radios"
        },
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

        fields = opengui.Fields(values, originals=originals, fields=cls.FIELDS + cls.YAML)

        fields["person_id"].options, fields["person_id"].content["labels"] = Person.choices()
        fields["status"].options = cls.STATUSES
        fields["template_id"].options, fields["template_id"].content["labels"] = Template.choices(cls.SINGULAR)

        if fields["template_id"].value:

            template = Template.response(TemplateRUD.retrieve(fields["template_id"].value))

            fields["name"].value = template["name"]
            fields["yaml"].value = template["yaml"]

        return fields

    @require_session
    def post(self):

        model = self.create(**self.request(flask.request.json[self.SINGULAR]))

        return {self.SINGULAR: self.response(model)}, 201

    @require_session
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

class StatusRUD(RestRUD):

    FIELDS = [
        {
            "name": "person_id",
            "label": "person",
            "style": "radios"
        },
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

        fields = opengui.Fields(values, originals=originals, fields=cls.ID + cls.FIELDS + cls.YAML)

        fields["person_id"].options, fields["person_id"].content["labels"] = Person.choices()
        fields["status"].options = cls.STATUSES

        return fields

class StatusA(flask_restful.Resource):

    @require_session
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
    MODEL = mysql.Area
    ORDER = [mysql.Area.name]

    @classmethod
    def wrong(cls, model):
        """
        Wrongs a model
        """

        if model.status == "positive":

            model.status = "negative"
            cls.notify("wrong", model)

            if "todo" in model.data:
                ToDo.create(person_id=model.person.id, data={"area": model.id}, template=model.data["todo"])

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
    MODEL = mysql.Act
    ORDER = [mysql.Act.created.desc()]

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

            ToDo.create(person_id=model.person.id, status="opened", template=template)

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
    MODEL = mysql.ToDo
    ORDER = [mysql.ToDo.created.desc()]

    @classmethod
    def todos(cls, data):
        """
        Reminds all ToDos
        """

        if "person" in data:
            person_id = flask.request.session.query(
                mysql.Person
            ).filter_by(
                name=data["person"]
            ).one().id
        else:
            person_id = data["person_id"]

        person = flask.request.session.query(mysql.Person).get(person_id)

        updated = False

        todos = []

        for todo in flask.request.session.query(
            mysql.ToDo
        ).filter_by(
            person_id=person_id,
            status="opened"
        ).order_by(
            *ToDo.ORDER
        ).all():

            todo.data["notified"] = time.time()
            todo.updated = time.time()
            todos.append(todo)

        if todos:

            notify({
                "kind": "todos",
                "action": "remind",
                "person": Person.response(person),
                "speech": data.get("speech", {}),
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
                Area.right(flask.request.session.query(mysql.Area).get(model.data["area"]))

            if "act" in model.data:

                if isinstance(model.data["act"], dict):
                    template = model.data["act"]
                else:
                    template = copy.deepcopy(model.data)
                    del template["act"]
                    del template["notified"]
                    template["name"] = model.name

                Act.create(person_id=model.person.id, status="positive", template=template)

            return True

        return False

class ToDoCL(ToDo, StatusCL):

    @require_session
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
    MODEL = mysql.Routine
    ORDER = [mysql.Routine.created.desc()]
    ACTIONS = State.ACTIONS + ["next"]

    @staticmethod
    def tasks(fields):
        """
        Builds a routine from a raw fields, template, template id, etc.
        """

        if fields["data"].get("todos"):

            tasks = []

            for todo in flask.request.session.query(
                mysql.ToDo
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

    @staticmethod
    def notify(action, task, routine):
        """
        Notifies somethign happened
        """

        routine.data["notified"] = time.time()
        routine.updated = time.time()
        task["notified"] = time.time()

        notify({
            "kind": "task",
            "action": action,
            "task": task,
            "routine": Routine.response(routine),
            "person": Person.response(routine.person)
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
                ToDo.complete(flask.request.session.query(mysql.ToDo).get(task["todo"]))

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
                ToDo.uncomplete(flask.request.session.query(mysql.ToDo).get(task["todo"]))

            return True

        return False

class TaskA(Task, flask_restful.Resource):

    @require_session
    def patch(self, routine_id, task_id, action):

        routine = flask.request.session.query(mysql.Routine).get(routine_id)
        task = routine.data["tasks"][task_id]

        if action in self.ACTIONS:

            updated = getattr(self, action)(task, routine)

            if updated:
                flask.request.session.commit()

            return {"updated": updated}, 202
