import unittest
import unittest.mock
import klotio_unittest
import nandyio_people_unittest

import os
import json
import yaml

import flask
import opengui
import sqlalchemy.exc

import klotio
import klotio_sqlalchemy_restful
import nandyio_people_integrations

import nandyio_chore_models
import test_nandyio_chore_models

import service

class TestRestful(klotio_unittest.TestCase):

    maxDiff = None

    @classmethod
    @unittest.mock.patch.dict(os.environ, {
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_CHANNEL": "stuff"
    })
    @unittest.mock.patch("redis.Redis", klotio_unittest.MockRedis)
    @unittest.mock.patch("klotio.logger", klotio_unittest.MockLogger)
    def setUpClass(cls):

        cls.app = service.build()
        cls.api = cls.app.test_client()

    def setUp(self):

        self.app.mysql.drop_database()
        self.app.mysql.create_database()

        self.session = self.app.mysql.session()

        self.sample = test_nandyio_chore_models.Sample(self.session)

        self.app.mysql.Base.metadata.create_all(self.app.mysql.engine)

        self.app.logger.clear()

    def tearDown(self):

        self.session.close()
        self.app.mysql.drop_database()


class TestAPI(TestRestful):

    @unittest.mock.patch.dict(os.environ, {
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_CHANNEL": "stuff"
    })
    @unittest.mock.patch("redis.Redis", klotio_unittest.MockRedis)
    @unittest.mock.patch("klotio.logger", klotio_unittest.MockLogger)
    def test_app(self):

        app = service.build()

        self.assertEqual(app.name, "nandy-io-chore-api")
        self.assertEqual(str(app.mysql.engine.url), "mysql+pymysql://root@nandyio-chore-api-mysql:3306/nandy_chore")

        self.assertEqual(app.logger.name, "nandy-io-chore-api")

        self.assertLogged(app.logger, "debug", "init", extra={
            "init": {
                "redis": {
                    "connection": "MockRedis<host=most.com,port=667>",
                    "channel": "stuff"
                },
                "mysql": {
                    "connection": "mysql+pymysql://root@nandyio-chore-api-mysql:3306/nandy_chore"
                }
            }
        })

class TestHealth(TestRestful):

    def test_get(self):

        self.assertEqual(self.api.get("/health").json, {"message": "OK"})


class TestGroup(TestRestful):

    @unittest.mock.patch("requests.get")
    def test_get(self, mock_get):

        mock_get.return_value.json.return_value = [{
            "name": "unit",
            "url": "test"
        }]

        self.assertEqual(self.api.get("/group").json, {"group": [{
            "name": "unit",
            "url": "test"
        }]})

        mock_get.assert_has_calls([
            unittest.mock.call("http://api.klot-io/app/chore.nandy.io/member"),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])


class TestTemplate(TestRestful):

    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_integrations(self):

        klotio.integrations.add("template", {
            "name": "unit.test",
            "description": "template"
        })

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "area"
        })

        klotio.integrations.add("act", {
            "name": "unit.test",
            "description": "act"
        })

        klotio.integrations.add("todo", {
            "name": "unit.test",
            "description": "todo"
        })

        klotio.integrations.add("routine", {
            "name": "unit.test",
            "description": "routine"
        })

        self.assertEqual(service.Template.integrations("template"), [{
            "name": "unit.test",
            "description": "template"
        }])

        self.assertEqual(service.Template.integrations("area"), [{
            "name": "unit.test",
            "description": "area"
        }])

        self.assertEqual(service.Template.integrations("act"), [{
            "name": "unit.test",
            "description": "act"
        }])

        self.assertEqual(service.Template.integrations("todo"), [{
            "name": "unit.test",
            "description": "todo"
        }])

        self.assertEqual(service.Template.integrations("routine"), [{
            "name": "unit.test",
            "description": "routine"
        }])

        self.assertEqual(service.Template.integrations("nope"), [])

    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_request(self):

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "area"
        })

        klotio.integrations.add("template", {
            "name": "unit.test",
            "description": "template"
        })

        self.assertEqual(service.Template.request({
            "kind": "area",
            "unit.test": {
                "integrate": "yep"
            },
            "yaml": yaml.dump({"b": 2})
        }), {
            "kind": "area",
            "data": {
                "b": 2,
                "unit.test": {
                    "integrate": "yep"
                }
            }
        })

        self.assertEqual(service.Template.request({
            "unit.test": {
                "integrate": "yep"
            },
            "yaml": yaml.dump({"b": 2})
        }), {
            "data": {
                "b": 2,
                "unit.test": {
                    "integrate": "yep"
                }
            }
        })

    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_response(self):

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "area"
        })

        klotio.integrations.add("template", {
            "name": "unit.test",
            "description": "template"
        })

        template = self.sample.template(
            "unit",
            kind="area",
            data={
                "d": 4,
                "unit.test": {
                    "integrate": "yep"
                }
            }
        )

        self.assertEqual(service.Template.response(template), {
            "id": template.id,
            "name": "unit",
            "kind": "area",
            "unit.test": {
                "integrate": "yep"
            },
            "data": {
                "d": 4
            },
            "yaml": yaml.dump({"d": 4}, default_flow_style=False)
        })

        template.kind = None

        self.assertEqual(service.Template.response(template), {
            "id": template.id,
            "name": "unit",
            "kind": None,
            "unit.test": {
                "integrate": "yep"
            },
            "data": {
                "d": 4
            },
            "yaml": yaml.dump({"d": 4}, default_flow_style=False)
        })

    def test_choices(self):

        unit = self.sample.template("unit", "todo")
        test = self.sample.template("test", "act")
        rest = self.sample.template("rest", "todo")

        @klotio_sqlalchemy_restful.session
        def choices():
            return {"choices": service.Template.choices('todo')}

        self.app.add_url_rule('/choices/template', 'choices', choices)

        self.assertStatusValue(self.api.get("/choices/template"), 200, "choices", [
            [rest.id, unit.id],
            {str(rest.id): "rest", str(unit.id): "unit"}
        ])

    def test_form(self):

        self.assertEqual(service.Template.form({"kind": "unit"}, {"kind": "test"}), "unit")
        self.assertEqual(service.Template.form({}, {"kind": "test"}), "test")
        self.assertEqual(service.Template.form({}, {}), "template")

class TestTemplateCL(TestRestful):

    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "area"
        })

        klotio.integrations.add("act", {
            "name": "unit.test",
            "description": "act"
        })

        klotio.integrations.add("template", {
            "name": "unit.test",
            "description": "template"
        })

        self.assertEqual(service.TemplateCL.fields({"kind": "area"}, {"kind": "act"}).to_list(), [
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
                "trigger": True,
                "value": "area",
                "original": "act"
            },
            {
                "name": "unit.test",
                "description": "area"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(service.TemplateCL.fields({}, {"kind": "act"}).to_list(), [
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
                "trigger": True,
                "original": "act"
            },
            {
                "name": "unit.test",
                "description": "act"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(service.TemplateCL.fields().to_list(), [
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
            },
            {
                "name": "unit.test",
                "description": "template"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    def test_options(self):

        response = self.api.options("/template")

        self.assertStatusFields(response, 200, [
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
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
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
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True
                        }
                    ]
                }
            }
        })

        response = self.api.options("/template", json={"template": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "name",
                "errors": ["missing value"]
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
                "trigger": True,
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options("/template", json={"template": {
            "name": "yup",
            "kind": "act",
            "yaml": '"a": 1'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "name",
                "value": "yup"
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
                "trigger": True,
                "value": "act"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": '"a": 1'
            }
        ])

    def test_post(self):

        response = self.api.post("/template", json={
            "template": {
                "name": "unit",
                "kind": "todo",
                "data": {"a": 1}
            }
        })

        self.assertStatusModel(response, 201, "template", {
            "name": "unit",
            "kind": "todo",
            "data": {"a": 1}
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 201,
                "json": {
                    "template": {
                        "name": "unit",
                        "kind": "todo",
                        "data": {"a": 1}
                    }
                }
            }
        })

    def test_get(self):

        self.sample.template("unit", "todo")
        self.sample.template("test", "act")

        self.assertStatusModels(self.api.get("/template"), 200, "templates", [
            {
                "name": "test"
            },
            {
                "name": "unit"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "templates": [
                        {
                            "name": "test"
                        },
                        {
                            "name": "unit"
                        }
                    ]
                }
            }
        })

class TestTemplateRUD(TestRestful):

    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "area"
        })

        klotio.integrations.add("act", {
            "name": "unit.test",
            "description": "act"
        })

        klotio.integrations.add("template", {
            "name": "unit.test",
            "description": "template"
        })

        self.assertEqual(service.TemplateRUD.fields({"kind": "area"}, {"kind": "act"}).to_list(), [
            {
                "name": "id",
                "readonly": True
            },
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
                "trigger": True,
                "value": "area",
                "original": "act"
            },
            {
                "name": "unit.test",
                "description": "area"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(service.TemplateRUD.fields({}, {"kind": "act"}).to_list(), [
            {
                "name": "id",
                "readonly": True
            },
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
                "trigger": True,
                "original": "act"
            },
            {
                "name": "unit.test",
                "description": "act"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(service.TemplateRUD.fields().to_list(), [
            {
                "name": "id",
                "readonly": True
            },
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
            },
            {
                "name": "unit.test",
                "description": "template"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    def test_options(self):

        template = self.sample.template("unit", "todo", {"a": 1})

        response = self.api.options(f"/template/{template.id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": template.id,
                "original": template.id
            },
            {
                "name": "name",
                "value": "unit",
                "original": "unit"
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
                "trigger": True,
                "value": "todo",
                "original": "todo"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "a: 1\n",
                "original": "a: 1\n"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "id",
                            "readonly": True,
                            "value": template.id,
                            "original": template.id
                        },
                        {
                            "name": "name",
                            "value": "unit",
                            "original": "unit"
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
                            "trigger": True,
                            "value": "todo",
                            "original": "todo"
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True,
                            "value": "a: 1\n",
                            "original": "a: 1\n"
                        }
                    ]
                }
            }
        })

        response = self.api.options(f"/template/{template.id}", json={"template": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": template.id,
                "original": template.id
            },
            {
                "name": "name",
                "original": "unit",
                "errors": ["missing value"]
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
                "trigger": True,
                "original": "todo",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "a: 1\n"
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options(f"/template/{template.id}", json={"template": {
            "name": "yup",
            "kind": "act",
            "yaml": 'b: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": template.id,
                "original": template.id
            },
            {
                "name": "name",
                "value": "yup",
                "original": "unit"
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
                "trigger": True,
                "value": "act",
                "original": "todo"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "b: 2",
                "original": "a: 1\n"
            }
        ])

    def test_get(self):

        template = self.sample.template("unit", "todo", {"a": 1})

        self.assertStatusModel(self.api.get(f"/template/{template.id}"), 200, "template", {
            "name": "unit",
            "kind": "todo",
            "data": {"a": 1},
            "yaml": "a: 1\n"
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "template": {
                        "name": "unit",
                        "kind": "todo",
                        "data": {"a": 1},
                        "yaml": "a: 1\n"
                    }
                }
            }
        })

    def test_patch(self):

        template = self.sample.template("unit", "todo", {"a": 1})

        self.assertStatusValue(self.api.patch(f"/template/{template.id}", json={
            "template": {
                "kind": "act"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/template/{template.id}"), 200, "template", {
            "name": "unit",
            "kind": "act",
            "data": {"a": 1}
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "template": {
                        "name": "unit",
                        "kind": "act",
                        "data": {"a": 1}
                    }
                }
            }
        })

    def test_delete(self):

        template = self.sample.template("unit", "todo")

        self.assertStatusValue(self.api.delete(f"/template/{template.id}"), 202, "deleted", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "deleted": 1
                }
            }
        })

        self.assertStatusModels(self.api.get("/template"), 200, "templates", [])


class TestArea(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self):

        @klotio_sqlalchemy_restful.session
        def build():
            return {"build": service.Area.build(**flask.request.json)}

        self.app.add_url_rule('/build/area', 'build', build)

        # basic

        self.assertStatusValue(self.api.get("/build/area", json={
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "positive",
                "created": 1,
                "updated": 2
            }
        }), 200, "build", {
            "person_id": 1,
            "name": "hey",
            "status": "positive",
            "created": 1,
            "updated": 2,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "positive",
                "created": 1,
                "updated": 2
            }
        })

        # template by data, person by name

        self.assertStatusValue(self.api.get("/build/area", json={
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template_id = self.sample.template("unit", "area", data={
            "by": "template_id",
            "status": "negative",
            "person": "unit"
        }).id

        self.assertStatusValue(self.api.get("/build/area", json={
            "name": "hey",
            "template_id": template_id
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "negative",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "negative"
            }
        })

        # template by name

        self.assertStatusValue(self.api.get("/build/area", json={
            "name": "hey",
            "template": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "negative",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "negative"
            }
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_notify(self, mock_notify):

        model = self.sample.area("unit", "test")

        service.Area.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "area",
            "action": "test",
            "area": service.Area.response(model),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_create(self, mock_notify):

        @klotio_sqlalchemy_restful.session
        def create():
            item = service.Area.create(**flask.request.json)
            flask.request.session.commit()
            return {"create": item.id}

        self.app.add_url_rule('/create/area', 'create', create)

        area_id = self.api.get("/create/area", json={
            "person_id": 1,
            "name": "unit",
            "created": 6,
            "data": {
                "text": "hey"
            }
        }).json["create"]

        item = self.session.query(nandyio_chore_models.Area).get(area_id)
        self.session.commit()

        self.assertEqual(item.person_id, 1)
        self.assertEqual(item.name, "unit")
        self.assertEqual(item.status, "positive")
        self.assertEqual(item.created, 6)
        self.assertEqual(item.updated, 7)
        self.assertEqual(item.data, {
            "text": "hey",
            "notified": 7
        })

        mock_notify.assert_called_once_with({
            "kind": "area",
            "action": "create",
            "area": service.Area.response(item),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_wrong(self, mock_notify):

        self.app.mysql.session = unittest.mock.MagicMock(return_value=self.session)

        area = self.sample.area("unit", "hey", data={
            "todo": {
                "name": "Unit",
                "text": "test"
            }
        })

        area_id = area.id

        @klotio_sqlalchemy_restful.session
        def wrong():
            response = {"wrong": service.Area.wrong(self.session.query(nandyio_chore_models.Area).get(flask.request.json["wrong"]))}
            flask.request.session.commit()
            return response

        self.app.add_url_rule('/wrong/area', 'wrong', wrong)

        self.assertTrue(self.api.get("/wrong/area", json={"wrong": area_id}).json["wrong"])
        area = self.session.query(nandyio_chore_models.Area).get(area_id)
        self.assertEqual(area.status, "negative")
        todo = self.session.query(nandyio_chore_models.ToDo).all()[0]
        self.assertEqual(todo.person_id, area.person_id)
        self.assertEqual(todo.name, "Unit")
        self.assertEqual(todo.data["text"], "test")
        self.assertEqual(todo.data["area"], area.id)

        self.assertEqual(mock_notify.call_args_list[0].args[0], {
            "kind": "area",
            "action": "wrong",
            "area": service.Area.response(area),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })
        self.assertEqual(mock_notify.call_args_list[1].args[0], {
            "kind": "todo",
            "action": "create",
            "todo": service.ToDo.response(todo),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        self.assertFalse(self.api.get("/wrong/area", json={"wrong": area_id}).json["wrong"])
        self.assertEqual(mock_notify.call_count, 2)

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Status.notify")
    def test_right(self, mock_notify):

        model = self.sample.area("unit", "hey", status="negative")

        self.assertTrue(service.Area.right(model))
        self.assertEqual(model.status, "positive")
        mock_notify.assert_called_once_with("right", model)

        self.assertFalse(service.Area.right(model))
        mock_notify.assert_called_once()

class TestAreaCL(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "integrate"
        })

        template_id = self.sample.template("test", "area", {"a": 1}).id

        @klotio_sqlalchemy_restful.session
        def blank_fields():
            return {"fields": service.AreaCL.fields().to_list()}

        self.app.add_url_rule('/blank_fields/areacl', 'blank_fields', blank_fields)

        self.assertEqual(self.api.get('/blank_fields/areacl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        @klotio_sqlalchemy_restful.session
        def template_fields():
            return {"fields": service.AreaCL.fields({"template_id": template_id}).to_list()}

        self.app.add_url_rule('/template_fields/areacl', 'template_fields', template_fields)

        self.assertEqual(self.api.get('/template_fields/areacl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "value": template_id,
                "optional": True
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        template_id = self.sample.template("test", "area", {"a": 1}).id

        response = self.api.options("/area")

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            }
                        },
                        {
                            "name": "status",
                            "options": ['positive', 'negative'],
                            "style": "radios"
                        },
                        {
                            "name": "template_id",
                            "label": "template",
                            "options": [template_id],
                            "labels": {template_id: "test"},
                            "style": "select",
                            "trigger": True,
                            "optional": True
                        },
                        {
                            "name": "name"
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True
                        }
                    ]
                }
            }
        })

        response = self.api.options("/area", json={"area": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "errors": ["missing value"]
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options("/area", json={"area": {
            "person_id": 1,
            "status": "positive",
            "template_id": template_id
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "value": "positive"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_post(self):

        response = self.api.post("/area", json={
            "area": {
                "person_id": 1,
                "name": "unit",
                "status": "negative",
                "data": {
                    "a": 1
                }
            }
        })

        self.assertStatusModel(response, 201, "area", {
            "person_id": 1,
            "name": "unit",
            "status": "negative",
            "data": {
                "a": 1,
                "notified": 7
            }
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 201,
                "json": {
                    "area": {
                        "person_id": 1,
                        "name": "unit",
                        "status": "negative",
                        "data": {
                            "a": 1,
                            "notified": 7
                        }
                    }
                }
            }
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_get(self):

        self.sample.area("unit", "test", updated=6)
        self.sample.area("test", "unit")

        self.assertStatusModels(self.api.get("/area"), 200, "areas", [
            {
                "name": "test"
            },
            {
                "name": "unit"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "areas": [
                        {
                            "name": "test"
                        },
                        {
                            "name": "unit"
                        }
                    ]
                }
            }
        })

        self.assertStatusModels(self.api.get("/area?since=0&status=positive"), 200, "areas", [
            {
                "name": "unit"
            }
        ])

class TestAreaRUD(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("area", {
            "name": "unit.test",
            "description": "integrate"
        })

        @klotio_sqlalchemy_restful.session
        def fields():

            return {"fields": service.AreaRUD.fields().to_list()}

        self.app.add_url_rule('/fields/arearud', 'fields', fields)

        self.assertEqual(self.api.get('/fields/arearud').json["fields"], [
            {
                "name": "id",
                "readonly": True
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
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
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        area_id = self.sample.area("unit", "test", status="positive", data={"a": 1}).id

        response = self.api.options(f"/area/{area_id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": area_id,
                "original": area_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1,
                "original": 1
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "value": "positive",
                "original": "positive"
            },
            {
                "name": "name",
                "value": "test",
                "original": "test"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "a: 1\n",
                "original": "a: 1\n"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "id",
                            "readonly": True,
                            "value": area_id,
                            "original": area_id
                        },
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            },
                            "value": 1,
                            "original": 1
                        },
                        {
                            "name": "status",
                            "options": ['positive', 'negative'],
                            "style": "radios",
                            "value": "positive",
                            "original": "positive"
                        },
                        {
                            "name": "name",
                            "value": "test",
                            "original": "test"
                        },
                        {
                            "name": "created",
                            "style": "datetime",
                            "readonly": True,
                            "value": 7,
                            "original": 7
                        },
                        {
                            "name": "updated",
                            "style": "datetime",
                            "readonly": True,
                            "value": 8,
                            "original": 8
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True,
                            "value": "a: 1\n",
                            "original": "a: 1\n"
                        }
                    ]
                }
            }
        })

        response = self.api.options(f"/area/{area_id}", json={"area": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": area_id,
                "original": area_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "original": "positive",
                "errors": ["missing value"]
            },
            {
                "name": "name",
                "original": "test",
                "errors": ["missing value"]
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "original": "a: 1\n",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options(f"/area/{area_id}", json={"area": {
            "person_id": 2,
            "name": "yup",
            "status": "negative",
            "yaml": 'b: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": area_id,
                "original": area_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "value": 2
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "original": "positive",
                "value": "negative"
            },
            {
                "name": "name",
                "original": "test",
                "value": "yup"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "a: 1\n",
                "value": "b: 2"
            }
        ])

    def test_get(self):

        area_id = self.sample.area("unit", "test").id

        self.assertStatusModel(self.api.get(f"/area/{area_id}"), 200, "area", {
            "name": "test"
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "area": {
                        "name": "test"
                    }
                }
            }
        })

    def test_patch(self):

        area_id = self.sample.area("unit", "test").id

        self.assertStatusValue(self.api.patch(f"/area/{area_id}", json={
            "area": {
                "status": "negative"
            }
        }), 202, "updated", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": 1
                }
            }
        })

        self.assertStatusModel(self.api.get(f"/area/{area_id}"), 200, "area", {
            "name": "test",
            "status": "negative"
        })

    def test_delete(self):

        area_id = self.sample.area("unit", "test").id

        self.assertStatusValue(self.api.delete(f"/area/{area_id}"), 202, "deleted", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "deleted": 1
                }
            }
        })

        self.assertStatusModels(self.api.get("/area"), 200, "areas", [])

class TestAreaA(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        area_id = self.sample.area("unit", "test").id

        # wrong

        self.assertStatusValue(self.api.patch(f"/area/{area_id}/wrong"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Area).get(area_id)
        self.session.commit()
        self.assertEqual(item.status, "negative")
        self.assertStatusValue(self.api.patch(f"/area/{area_id}/wrong"), 202, "updated", False)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": False
                }
            }
        })

        # right

        self.assertStatusValue(self.api.patch(f"/area/{area_id}/right"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Area).get(area_id)
        self.session.commit()
        self.assertEqual(item.status, "positive")
        self.assertStatusValue(self.api.patch(f"/area/{area_id}/right"), 202, "updated", False)


class TestAct(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self):

        @klotio_sqlalchemy_restful.session
        def build():

            return {"build": service.Act.build(**flask.request.json)}

        self.app.add_url_rule('/build/act', 'build', build)

        # basic

        self.assertStatusValue(self.api.get("/build/act", json={
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "positive",
                "created": 1,
                "updated": 2
            }
        }), 200, "build", {
            "person_id": 1,
            "name": "hey",
            "status": "positive",
            "created": 1,
            "updated": 2,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "positive",
                "created": 1,
                "updated": 2
            }
        })

        # template by data, person by name

        self.assertStatusValue(self.api.get("/build/act", json={
            "template": {
                "by": "template",
                "name": "hey",
                "person": "unit",
                "person": "nope"
            },
            "person": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template_id = self.sample.template("unit", "act", data={
            "by": "template_id",
            "status": "negative",
            "person": "unit"
        }).id

        self.assertStatusValue(self.api.get("/build/act", json={
            "name": "hey",
            "template_id": template_id
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "negative",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "negative"
            }
        })

        # template by name

        self.assertStatusValue(self.api.get("/build/act", json={
            "name": "hey",
            "template": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "negative",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "negative"
            }
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_notify(self, mock_notify):

        model = self.sample.act("unit", "test")

        service.Act.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "act",
            "action": "test",
            "act": service.Act.response(model),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_create(self, mock_notify):

        @klotio_sqlalchemy_restful.session
        def create():
            item = service.Act.create(**flask.request.json)
            flask.request.session.commit()
            response = flask.make_response(json.dumps({"create": item.id}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/create/act', 'create', create)

        act_id = self.api.get("/create/act", json={
            "person_id": 1,
            "name": "unit",
            "status": "negative",
            "created": 6,
            "data": {
                "text": "hey",
                "todo": {
                    "name": "Unit",
                    "text": "test"
                }
            }
        }).json["create"]

        model = self.session.query(nandyio_chore_models.Act).get(act_id)
        self.session.commit()

        self.assertEqual(model.person_id, 1)
        self.assertEqual(model.name, "unit")
        self.assertEqual(model.status, "negative")
        self.assertEqual(model.created, 6)
        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data, {
            "text": "hey",
            "notified": 7,
            "todo": {
                "name": "Unit",
                "text": "test"
            }
        })

        todo = self.session.query(nandyio_chore_models.ToDo).filter_by(name="Unit").all()[0]
        self.session.commit()
        self.assertEqual(todo.data["text"], "test")

        item = self.session.query(nandyio_chore_models.Act).get(model.id)
        self.session.commit()
        self.assertEqual(item.name, "unit")

        mock_notify.assert_has_calls([
            unittest.mock.call({
                "kind": "act",
                "action": "create",
                "act": service.Act.response(model),
                "person": nandyio_people_integrations.Person.model(id=1)
            }),
            unittest.mock.call({
                "kind": "todo",
                "action": "create",
                "todo": service.ToDo.response(todo),
                "person": nandyio_people_integrations.Person.model(id=1)
            })
        ])

        self.api.get("/create/act", json={
            "person_id": 1,
            "name": "test",
            "status": "negative",
            "created": 6,
            "data": {
                "text": "hey",
                "todo": True
            }
        })
        self.session.commit()

        todo = self.session.query(nandyio_chore_models.ToDo).filter_by(name="test").all()[0]
        self.assertEqual(todo.data, {
            "name": "test",
            "text": "hey",
            "act": True,
            "notified": 7
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Status.notify")
    def test_wrong(self, mock_notify):

        model = self.sample.act("unit", "hey")

        self.assertTrue(service.Act.wrong(model))
        self.assertEqual(model.status, "negative")
        mock_notify.assert_called_once_with("wrong", model)

        self.assertFalse(service.Act.wrong(model))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Status.notify")
    def test_right(self, mock_notify):

        model = self.sample.act("unit", "hey", status="negative")

        self.assertTrue(service.Act.right(model))
        self.assertEqual(model.status, "positive")
        mock_notify.assert_called_once_with("right", model)

        self.assertFalse(service.Act.right(model))
        mock_notify.assert_called_once()

class TestActCL(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("act", {
            "name": "unit.test",
            "description": "integrate"
        })

        template_id = self.sample.template("test", "act", {"a": 1}).id

        @klotio_sqlalchemy_restful.session
        def blank_fields():

            return {"fields": service.ActCL.fields().to_list()}

        self.app.add_url_rule('/blank_fields/actcl', 'blank_fields', blank_fields)

        self.assertEqual(self.api.get('/blank_fields/actcl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        @klotio_sqlalchemy_restful.session
        def template_fields():

            return {"fields": service.ActCL.fields({"template_id": template_id}).to_list()}

        self.app.add_url_rule('/template_fields/actcl', 'template_fields', template_fields)

        self.assertEqual(self.api.get('/template_fields/actcl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        template_id = self.sample.template("test", "act", {"a": 1}).id

        response = self.api.options("/act")

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            }
                        },
                        {
                            "name": "status",
                            "options": ['positive', 'negative'],
                            "style": "radios"
                        },
                        {
                            "name": "template_id",
                            "label": "template",
                            "options": [template_id],
                            "labels": {template_id: "test"},
                            "style": "select",
                            "trigger": True,
                            "optional": True
                        },
                        {
                            "name": "name"
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True
                        }
                    ]
                }
            }
        })

        response = self.api.options("/act", json={"act": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "errors": ["missing value"]
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options("/act", json={"act": {
            "person_id": 1,
            "status": "positive",
            "template_id": template_id
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "value": "positive"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_post(self):

        response = self.api.post("/act", json={
            "act": {
                "person_id": 1,
                "name": "unit",
                "status": "negative",
                "data": {
                    "a": 1
                }
            }
        })

        self.assertStatusModel(response, 201, "act", {
            "person_id": 1,
            "name": "unit",
            "status": "negative",
            "data": {
                "a": 1,
                "notified": 7
            }
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 201,
                "json": {
                    "act": {
                        "person_id": 1,
                        "name": "unit",
                        "status": "negative",
                        "data": {
                            "a": 1,
                            "notified": 7
                        }
                    }
                }
            }
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_get(self):

        self.sample.act("unit", "test", updated=6)
        self.sample.act("test", "unit")

        self.assertStatusModels(self.api.get("/act"), 200, "acts", [
            {
                "name": "test"
            },
            {
                "name": "unit"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "acts": [
                        {
                            "name": "test"
                        },
                        {
                            "name": "unit"
                        }
                    ]
                }
            }
        })

        self.assertStatusModels(self.api.get("/act?since=0&status=positive"), 200, "acts", [
            {
                "name": "unit"
            }
        ])

class TestActRUD(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("act", {
            "name": "unit.test",
            "description": "integrate"
        })

        @klotio_sqlalchemy_restful.session
        def fields():

            response = flask.make_response(json.dumps({"fields": service.ActRUD.fields().to_list()}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/fields/actrud', 'fields', fields)

        self.assertEqual(self.api.get('/fields/actrud').json["fields"], [
            {
                "name": "id",
                "readonly": True
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
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
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        act_id = self.sample.act("unit", "test", status="positive", data={"a": 1}).id

        response = self.api.options(f"/act/{act_id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": act_id,
                "original": act_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1,
                "original": 1
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "value": "positive",
                "original": "positive"
            },
            {
                "name": "name",
                "value": "test",
                "original": "test"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "a: 1\n",
                "original": "a: 1\n"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "id",
                            "readonly": True,
                            "value": act_id,
                            "original": act_id
                        },
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            },
                            "value": 1,
                            "original": 1
                        },
                        {
                            "name": "status",
                            "options": ['positive', 'negative'],
                            "style": "radios",
                            "value": "positive",
                            "original": "positive"
                        },
                        {
                            "name": "name",
                            "value": "test",
                            "original": "test"
                        },
                        {
                            "name": "created",
                            "style": "datetime",
                            "readonly": True,
                            "value": 7,
                            "original": 7
                        },
                        {
                            "name": "updated",
                            "style": "datetime",
                            "readonly": True,
                            "value": 8,
                            "original": 8
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True,
                            "value": "a: 1\n",
                            "original": "a: 1\n"
                        }
                    ]
                }
            }
        })

        response = self.api.options(f"/act/{act_id}", json={"act": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": act_id,
                "original": act_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "original": "positive",
                "errors": ["missing value"]
            },
            {
                "name": "name",
                "original": "test",
                "errors": ["missing value"]
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "a: 1\n"
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options(f"/act/{act_id}", json={"act": {
            "person_id": 2,
            "name": "yup",
            "status": "negative",
            "yaml": 'b: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": act_id,
                "original": act_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "value": 2
            },
            {
                "name": "status",
                "options": ['positive', 'negative'],
                "style": "radios",
                "original": "positive",
                "value": "negative"
            },
            {
                "name": "name",
                "original": "test",
                "value": "yup"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "a: 1\n",
                "value": "b: 2"
            }
        ])

    def test_get(self):

        act_id = self.sample.act("unit", "test").id

        self.assertStatusModel(self.api.get(f"/act/{act_id}"), 200, "act", {
            "name": "test"
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "act": {
                        "name": "test"
                    }
                }
            }
        })

    def test_patch(self):

        act_id = self.sample.act("unit", "test").id

        self.assertStatusValue(self.api.patch(f"/act/{act_id}", json={
            "act": {
                "status": "negative"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/act/{act_id}"), 200, "act", {
            "name": "test",
            "status": "negative"
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "act": {
                        "name": "test"
                    }
                }
            }
        })

    def test_delete(self):

        act_id = self.sample.act("unit", "test").id

        self.assertStatusValue(self.api.delete(f"/act/{act_id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/act"), 200, "acts", [])

class TestActA(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        model = self.sample.act("unit", "hey")

        # wrong

        self.assertStatusValue(self.api.patch(f"/act/{model.id}/wrong"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Act).get(model.id)
        self.session.commit()
        self.assertEqual(item.status, "negative")
        self.assertStatusValue(self.api.patch(f"/act/{model.id}/wrong"), 202, "updated", False)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": False
                }
            }
        })

        # right

        self.assertStatusValue(self.api.patch(f"/act/{model.id}/right"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Act).get(model.id)
        self.session.commit()
        self.assertEqual(item.status, "positive")
        self.assertStatusValue(self.api.patch(f"/act/{model.id}/right"), 202, "updated", False)

class TestToDo(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self):

        @klotio_sqlalchemy_restful.session
        def build():
            return {"build": service.ToDo.build(**flask.request.json)}

        self.app.add_url_rule('/build/todo', 'build', build)

        # basic

        self.assertStatusValue(self.api.get("/build/todo", json={
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2
            }
        }), 200, "build", {
            "person_id": 1,
            "name": "hey",
            "status": "opened",
            "created": 1,
            "updated": 2,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2
            }
        })

        # template by data, person by name

        self.assertStatusValue(self.api.get("/build/todo", json={
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template_id = self.sample.template("unit", "todo", data={
            "by": "template_id",
            "status": "closed",
            "person": "unit"
        }).id

        self.assertStatusValue(self.api.get("/build/todo", json={
            "name": "hey",
            "template_id": template_id
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "closed",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "closed"
            }
        })

        # template by name

        self.assertStatusValue(self.api.get("/build/todo", json={
            "name": "hey",
            "template": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "closed",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "closed"
            }
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_notify(self, mock_notify):

        model = self.sample.todo("unit", "test")

        service.ToDo.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "todo",
            "action": "test",
            "todo": service.ToDo.response(model),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_create(self, mock_notify):

        @klotio_sqlalchemy_restful.session
        def create():
            item = service.ToDo.create(**flask.request.json)
            flask.request.session.commit()
            return {"create": item.id}

        self.app.add_url_rule('/create/todo', 'create', create)

        todo_id = self.api.get("/create/todo", json={
            "person_id": 1,
            "name": "unit",
            "created": 6,
            "data": {
                "text": "hey"
            }
        }).json["create"]

        model = self.session.query(nandyio_chore_models.ToDo).get(todo_id)
        self.session.commit()

        self.assertEqual(model.person_id, 1)
        self.assertEqual(model.name, "unit")
        self.assertEqual(model.status, "opened")
        self.assertEqual(model.created, 6)
        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data, {
            "text": "hey",
            "notified": 7
        })

        mock_notify.assert_called_once_with({
            "kind": "todo",
            "action": "create",
            "todo": service.ToDo.response(model),
            "person": nandyio_people_integrations.Person.model(id=1)
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_todos(self, mock_notify):

        self.sample.todo("unit", status="closed")
        self.sample.todo("test")

        @klotio_sqlalchemy_restful.session
        def todos():
            response = {"todos": service.ToDo.todos(flask.request.json["todos"])}
            flask.request.session.commit()
            return response

        self.app.add_url_rule('/todos/todo', 'todos', todos)

        self.assertFalse(self.api.get("/todos/todo", json={"todos": {
            "person": "unit"
        }}).json["todos"])

        mock_notify.assert_not_called()

        todo_id = self.sample.todo("unit").id

        self.assertTrue(self.api.get("/todos/todo", json={"todos": {
            "person": "unit"
        }}).json["todos"])

        item = self.session.query(nandyio_chore_models.ToDo).get(todo_id)
        self.session.commit()

        self.assertEqual(item.updated, 7)
        self.assertEqual(item.data["notified"], 7)
        mock_notify.assert_called_once_with({
            "kind": "todos",
            "action": "remind",
            "person": nandyio_people_integrations.Person.model(name="unit"),
            "chore-speech.nandy.io": {},
            "todos": service.ToDo.responses([item])
        })

        self.assertTrue(self.api.get("/todos/todo", json={"todos": {
            "person_id": 1,
            "chore-speech.nandy.io": {
                "language": "cursing"
            }
        }}).json["todos"])
        mock_notify.assert_called_with({
            "kind": "todos",
            "action": "remind",
            "person": nandyio_people_integrations.Person.model(name="unit"),
            "chore-speech.nandy.io": {"language": "cursing"},
            "todos": service.ToDo.responses([item])
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_remind(self, mock_notify):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.ToDo.remind(todo))

        mock_notify.assert_called_once_with("remind", todo)

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_pause(self, mock_notify):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.ToDo.pause(todo))
        self.assertTrue(todo.data["paused"])
        mock_notify.assert_called_once_with("pause", todo)

        self.assertFalse(service.ToDo.pause(todo))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_unpause(self, mock_notify):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey",
            "paused": True
        })

        self.assertTrue(service.ToDo.unpause(todo))
        self.assertFalse(todo.data["paused"])
        mock_notify.assert_called_once_with("unpause", todo)

        self.assertFalse(service.ToDo.unpause(todo))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_skip(self, mock_notify):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.ToDo.skip(todo))
        self.assertTrue(todo.data["skipped"])
        self.assertEqual(todo.data["end"], 7)
        self.assertEqual(todo.status, "closed")
        mock_notify.assert_called_once_with("skip", todo)

        self.assertFalse(service.ToDo.skip(todo))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_unskip(self, mock_notify):

        todo = self.sample.todo("unit", "hey", status="closed", data={
            "text": "hey",
            "skipped": True,
            "end": 0
        })

        self.assertTrue(service.ToDo.unskip(todo))
        self.assertFalse(todo.data["skipped"])
        self.assertNotIn("end", todo.data)
        self.assertEqual(todo.status, "opened")
        mock_notify.assert_called_once_with("unskip", todo)

        self.assertFalse(service.ToDo.unskip(todo))
        mock_notify.assert_called_once()

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_complete(self, mock_notify):

        area_id = self.sample.area("unit", "test", status="negative").id

        todo_id = self.sample.todo("unit", "hey", data={
            "text": "hey",
            "area": area_id,
            "act": {
                "name": "Unit",
                "text": "test"
            }
        }).id

        @klotio_sqlalchemy_restful.session
        def complete():
            todo = self.session.query(nandyio_chore_models.ToDo).get(flask.request.json["complete"])
            response = {"complete": service.ToDo.complete(todo)}
            flask.request.session.commit()
            return response

        self.app.add_url_rule('/complete/todo', 'complete', complete)

        self.assertTrue(self.api.get("/complete/todo", json={"complete": todo_id}).json["complete"])

        todo = self.session.query(nandyio_chore_models.ToDo).get(todo_id)

        self.assertEqual(todo.status, "closed")
        self.assertTrue(todo.data["end"], 7)

        area = self.session.query(nandyio_chore_models.Area).get(area_id)
        self.session.commit()
        self.assertEqual(area.status, "positive")

        act = self.session.query(nandyio_chore_models.Act).filter_by(name="Unit").all()[0]
        self.assertEqual(act.person_id, todo.person_id)
        self.assertEqual(act.status, "positive")
        self.assertEqual(act.data["text"], "test")

        self.assertEqual(mock_notify.call_args_list[0].args[0], {
            "kind": "todo",
            "action": "complete",
            "todo": service.ToDo.response(todo),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })
        self.assertEqual(mock_notify.call_args_list[1].args[0], {
            "kind": "area",
            "action": "right",
            "area": service.Area.response(area),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })
        self.assertEqual(mock_notify.call_args_list[2].args[0], {
            "kind": "act",
            "action": "create",
            "act": service.Act.response(act),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        self.assertFalse(self.api.get("/complete/todo", json={"complete": todo_id}).json["complete"])

        todo_id = self.sample.todo("unit", "hey", data={
            "text": "you",
            "act": True,
            "notified": 7
        }).id

        self.api.get("/complete/todo", json={"complete": todo_id})

        todo = self.session.query(nandyio_chore_models.ToDo).get(todo_id)
        self.session.commit()

        self.assertEqual(todo.status, "closed")
        self.assertTrue(todo.data["end"], 7)

        act = self.session.query(nandyio_chore_models.Act).filter_by(name="hey").all()[0]
        self.assertEqual(act.person_id, todo.person_id)
        self.assertEqual(act.status, "positive")
        self.assertEqual(act.data["text"], "you")

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_uncomplete(self, mock_notify):

        todo = self.sample.todo("unit", "hey", status="closed", data={
            "text": "hey",
            "end": 0
        })

        self.assertTrue(service.ToDo.uncomplete(todo))
        self.assertNotIn("end", todo.data)
        self.assertEqual(todo.status, "opened")
        mock_notify.assert_called_once_with("uncomplete", todo)

        self.assertFalse(service.ToDo.uncomplete(todo))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_expire(self, mock_notify):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.ToDo.expire(todo))
        self.assertTrue(todo.data["expired"])
        self.assertEqual(todo.data["end"], 7)
        self.assertEqual(todo.status, "closed")
        mock_notify.assert_called_once_with("expire", todo)

        self.assertFalse(service.ToDo.expire(todo))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    def test_unexpire(self, mock_notify):

        todo = self.sample.todo("unit", "hey", status="closed", data={
            "text": "hey",
            "expired": True,
            "end": 0
        })

        self.assertTrue(service.ToDo.unexpire(todo))
        self.assertFalse(todo.data["expired"])
        self.assertNotIn("end", todo.data)
        self.assertEqual(todo.status, "opened")
        mock_notify.assert_called_once_with("unexpire", todo)

        self.assertFalse(service.ToDo.unexpire(todo))
        mock_notify.assert_called_once()

class TestToDoCL(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("todo", {
            "name": "unit.test",
            "description": "integrate"
        })

        template_id = self.sample.template("test", "todo", {"a": 1}).id

        @klotio_sqlalchemy_restful.session
        def blank_fields():
            return {"fields": service.ToDoCL.fields().to_list()}

        self.app.add_url_rule('/blank_fields/todocl', 'blank_fields', blank_fields)

        self.assertEqual(self.api.get('/blank_fields/todocl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        @klotio_sqlalchemy_restful.session
        def template_fields():
            return {"fields": service.ToDoCL.fields({"template_id": template_id}).to_list()}

        self.app.add_url_rule('/template_fields/todocl', 'template_fields', template_fields)

        self.assertStatusFields(self.api.get('/template_fields/todocl'), 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "a: 1\n"
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        template_id = self.sample.template("test", "todo", {"a": 1}).id

        response = self.api.options("/todo")

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            }
                        },
                        {
                            "name": "status",
                            "options": ['opened', 'closed'],
                            "style": "radios"
                        },
                        {
                            "name": "template_id",
                            "label": "template",
                            "options": [template_id],
                            "labels": {template_id: "test"},
                            "style": "select",
                            "trigger": True,
                            "optional": True
                        },
                        {
                            "name": "name"
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True
                        }
                    ]
                }
            }
        })

        response = self.api.options("/todo", json={"todo": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "errors": ["missing value"]
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options("/todo", json={"todo": {
            "person_id": 1,
            "status": "opened",
            "template_id": template_id
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "value": "opened"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_post(self):

        response = self.api.post("/todo", json={
            "todo": {
                "person_id": 1,
                "name": "unit",
                "status": "closed",
                "data": {
                    "a": 1
                }
            }
        })

        self.assertStatusModel(response, 201, "todo", {
            "person_id": 1,
            "name": "unit",
            "status": "closed",
            "data": {
                "a": 1,
                "notified": 7
            }
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 201,
                "json": {
                    "todo": {
                        "person_id": 1,
                        "name": "unit",
                        "status": "closed",
                        "data": {
                            "a": 1,
                            "notified": 7
                        }
                    }
                }
            }
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_get(self):

        self.sample.todo("unit", "test", updated=6)
        self.sample.todo("test", "unit")

        self.assertStatusModels(self.api.get("/todo"), 200, "todos", [
            {
                "name": "test"
            },
            {
                "name": "unit"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "todos": [
                        {
                            "name": "test"
                        },
                        {
                            "name": "unit"
                        }
                    ]
                }
            }
        })

        self.assertStatusModels(self.api.get("/todo?since=0&status=opened"), 200, "todos", [
            {
                "name": "unit"
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify", unittest.mock.MagicMock)
    def test_patch(self):

        todo_id = self.sample.todo("unit", "hey", data={
            "text": "hey"
        }).id

        self.assertStatusValue(self.api.patch(f"/todo", json={
            "todos": {
                "person": "unit"
            }
        }), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo_id)
        self.session.commit()
        self.assertEqual(item.data["notified"], 7)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": True
                }
            }
        })

class TestToDoRUD(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("todo", {
            "name": "unit.test",
            "description": "integrate"
        })

        @klotio_sqlalchemy_restful.session
        def fields():
            return {"fields": service.ToDoRUD.fields().to_list()}

        self.app.add_url_rule('/fields/todorud', 'fields', fields)

        self.assertEqual(self.api.get('/fields/todorud').json["fields"], [
            {
                "name": "id",
                "readonly": True
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
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
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        todo_id = self.sample.todo("unit", "test", status="opened", data={"text": 1}).id

        response = self.api.options(f"/todo/{todo_id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": todo_id,
                "original": todo_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1,
                "original": 1
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "value": "opened",
                "original": "opened"
            },
            {
                "name": "name",
                "value": "test",
                "original": "test"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "text: 1\n",
                "original": "text: 1\n"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "id",
                            "readonly": True,
                            "value": todo_id,
                            "original": todo_id
                        },
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            },
                            "value": 1,
                            "original": 1
                        },
                        {
                            "name": "status",
                            "options": ['opened', 'closed'],
                            "style": "radios",
                            "value": "opened",
                            "original": "opened"
                        },
                        {
                            "name": "name",
                            "value": "test",
                            "original": "test"
                        },
                        {
                            "name": "created",
                            "style": "datetime",
                            "readonly": True,
                            "value": 7,
                            "original": 7
                        },
                        {
                            "name": "updated",
                            "style": "datetime",
                            "readonly": True,
                            "value": 8,
                            "original": 8
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True,
                            "value": "text: 1\n",
                            "original": "text: 1\n"
                        }
                    ]
                }
            }
        })

        response = self.api.options(f"/todo/{todo_id}", json={"todo": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": todo_id,
                "original": todo_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "original": "opened",
                "errors": ["missing value"]
            },
            {
                "name": "name",
                "original": "test",
                "errors": ["missing value"]
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "text: 1\n"
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options(f"/todo/{todo_id}", json={"todo": {
            "person_id": 2,
            "name": "yup",
            "status": "closed",
            "yaml": 'text: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": todo_id,
                "original": todo_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "value": 2
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "original": "opened",
                "value": "closed"
            },
            {
                "name": "name",
                "original": "test",
                "value": "yup"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "text: 1\n",
                "value": "text: 2"
            }
        ])

    def test_get(self):

        todo_id = self.sample.todo("unit", "test").id

        self.assertStatusModel(self.api.get(f"/todo/{todo_id}"), 200, "todo", {
            "name": "test"
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "todo": {
                        "name": "test"
                    }
                }
            }
        })

    def test_patch(self):

        todo_id = self.sample.todo("unit", "test").id

        self.assertStatusValue(self.api.patch(f"/todo/{todo_id}", json={
            "todo": {
                "status": "closed"
            }
        }), 202, "updated", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": 1
                }
            }
        })

        self.assertStatusModel(self.api.get(f"/todo/{todo_id}"), 200, "todo", {
            "name": "test",
            "status": "closed"
        })

    def test_delete(self):

        todo_id = self.sample.todo("unit", "test").id

        self.assertStatusValue(self.api.delete(f"/todo/{todo_id}"), 202, "deleted", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "deleted": 1
                }
            }
        })

        self.assertStatusModels(self.api.get("/todo"), 200, "areas", [])

class TestToDoA(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        # remind

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/remind"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.data["notified"], 7)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": True
                }
            }
        })

        # pause

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/pause"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertTrue(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/pause"), 202, "updated", False)

        # unpause

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unpause"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertFalse(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unpause"), 202, "updated", False)

        # skip

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/skip"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertTrue(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/skip"), 202, "updated", False)

        # unskip

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unskip"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertFalse(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unskip"), 202, "updated", False)

        # complete

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/complete"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.status, "closed")
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/complete"), 202, "updated", False)

        # uncomplete

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/uncomplete"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.status, "opened")
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/uncomplete"), 202, "updated", False)

        # expire

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/expire"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertTrue(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/expire"), 202, "updated", False)

        # unexpire

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unexpire"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.session.commit()
        self.assertFalse(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unexpire"), 202, "updated", False)

class TestRoutine(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self):

        @klotio_sqlalchemy_restful.session
        def build():
            return {"build": service.Routine.build(**flask.request.json)}

        self.app.add_url_rule('/build/routine', 'build', build)

        # basic

        self.assertStatusValue(self.api.get("/build/routine", json={
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2
            }
        }), 200, "build", {
            "person_id": 1,
            "name": "hey",
            "status": "opened",
            "created": 1,
            "updated": 2,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2
            }
        })

        # template by data, person by name

        self.assertStatusValue(self.api.get("/build/routine", json={
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template_id = self.sample.template("unit", "routine", data={
            "by": "template_id",
            "status": "closed",
            "person": "unit"
        }).id

        self.assertStatusValue(self.api.get("/build/routine", json={
            "name": "hey",
            "template_id": template_id
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "closed",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "closed"
            }
        })

        # template by name

        self.assertStatusValue(self.api.get("/build/routine", json={
            "name": "hey",
            "template": "unit"
        }), 200, "build", {
            "name": "hey",
            "person_id": 1,
            "status": "closed",
            "data": {
                "name": "unit",
                "person": "unit",
                "by": "template_id",
                "status": "closed"
            }
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_tasks(self):

        todo = self.sample.todo("unit")
        self.sample.todo("unit", status="closed")
        self.sample.todo("test")

        @klotio_sqlalchemy_restful.session
        def tasks():
            response = flask.make_response(json.dumps({"tasks": service.Routine.tasks(service.Routine.build(**flask.request.json))}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/tasks/routine', 'tasks', tasks)

        self.assertStatusValue(self.api.get("/tasks/routine", json={
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2,
                "todos": True,
                "tasks": [{}]
            }
        }), 200, "tasks", {
            "person_id": 1,
            "name": "hey",
            "status": "opened",
            "created": 1,
            "updated": 2,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2,
                "todos": True,
                "tasks": [
                    {
                        "id": 0,
                        "text": "todo it",
                        "todo": todo.id

                    },
                    {
                        "id": 1
                    }
                ]
            }
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_notify(self, mock_notify):

        model = self.sample.routine("unit", "test")

        service.Routine.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "routine",
            "action": "test",
            "routine": service.Routine.response(model),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_check(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey"
        })

        service.Routine.check(routine)

        mock_notify.assert_not_called()

        routine.data["tasks"] = [
            {
                "text": "do it"
            },
            {
                "text": "moo it",
                "paused": True
            }
        ]

        service.Routine.check(routine)

        self.assertEqual(routine.data["tasks"][0]["start"], 7)

        mock_notify.assert_called_once_with({
            "kind": "task",
            "action": "start",
            "task": routine.data["tasks"][0],
            "routine": service.Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        service.Routine.check(routine)

        mock_notify.assert_called_once_with({
            "kind": "task",
            "action": "start",
            "task": routine.data["tasks"][0],
            "routine": service.Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        routine.data["tasks"][0]["end"] = 0

        service.Routine.check(routine)

        self.assertEqual(routine.data["tasks"][0]["start"], 7)

        mock_notify.assert_called_with({
            "kind": "task",
            "action": "pause",
            "task": routine.data["tasks"][1],
            "routine": service.Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        routine.data["tasks"][1]["end"] = 0

        service.Routine.check(routine)

        self.assertEqual(routine.status, "closed")

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify", unittest.mock.MagicMock)
    def test_create(self):

        @klotio_sqlalchemy_restful.session
        def create():
            item = service.Routine.create(**flask.request.json)
            flask.request.session.commit()
            response = flask.make_response(json.dumps({"create": item.id}))
            response.headers.set('Content-Type', 'application/json')
            response.status_code = 200
            return response

        self.app.add_url_rule('/create/routine', 'create', create)

        routine_id = self.api.get("/create/routine", json={
            "person_id": 1,
            "name": "unit",
            "status": "opened",
            "created": 6,
            "data": {
                "text": "hey",
                "tasks": [{}]
            }
        }).json["create"]

        routine = self.session.query(nandyio_chore_models.Routine).get(routine_id)
        self.session.commit()

        self.assertEqual(routine.person_id, 1)
        self.assertEqual(routine.name, "unit")
        self.assertEqual(routine.status, "opened")
        self.assertEqual(routine.created, 6)
        self.assertEqual(routine.updated, 7)
        self.assertEqual(routine.data, {
            "text": "hey",
            "start": 7,
            "notified": 7,
            "notified": 7,
                "tasks": [{
                    "id": 0,
                    "start": 7,
                    "notified": 7
                }]
        })

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify", unittest.mock.MagicMock)
    def test_next(self):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "tasks": [{
                "text": "do it",
                "start": 0
            }]
        })

        self.assertTrue(service.Routine.next(routine))

        self.assertEqual(routine.data["tasks"][0]["end"], 7)

        self.assertFalse(service.Routine.next(routine))

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_remind(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.Routine.remind(routine))

        mock_notify.assert_called_once_with("remind", routine)

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_pause(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.Routine.pause(routine))
        self.assertTrue(routine.data["paused"])
        mock_notify.assert_called_once_with("pause", routine)

        self.assertFalse(service.Routine.pause(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_unpause(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "paused": True
        })

        self.assertTrue(service.Routine.unpause(routine))
        self.assertFalse(routine.data["paused"])
        mock_notify.assert_called_once_with("unpause", routine)

        self.assertFalse(service.Routine.unpause(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_skip(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.Routine.skip(routine))
        self.assertTrue(routine.data["skipped"])
        self.assertEqual(routine.data["end"], 7)
        self.assertEqual(routine.status, "closed")
        mock_notify.assert_called_once_with("skip", routine)

        self.assertFalse(service.Routine.skip(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_unskip(self, mock_notify):

        routine = self.sample.routine("unit", "hey", status="closed", data={
            "text": "hey",
            "skipped": True,
            "end": 0
        })

        self.assertTrue(service.Routine.unskip(routine))
        self.assertFalse(routine.data["skipped"])
        self.assertNotIn("end", routine.data)
        self.assertEqual(routine.status, "opened")
        mock_notify.assert_called_once_with("unskip", routine)

        self.assertFalse(service.Routine.unskip(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_complete(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.Routine.complete(routine))
        self.assertEqual(routine.status, "closed")
        self.assertTrue(routine.data["end"], 7)
        mock_notify.assert_called_once_with("complete", routine)

        self.assertFalse(service.Routine.complete(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_uncomplete(self, mock_notify):

        routine = self.sample.routine("unit", "hey", status="closed", data={
            "text": "hey",
            "end": 0
        })

        self.assertTrue(service.Routine.uncomplete(routine))
        self.assertNotIn("end", routine.data)
        self.assertEqual(routine.status, "opened")
        mock_notify.assert_called_once_with("uncomplete", routine)

        self.assertFalse(service.Routine.uncomplete(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_expire(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey"
        })

        self.assertTrue(service.Routine.expire(routine))
        self.assertTrue(routine.data["expired"])
        self.assertEqual(routine.data["end"], 7)
        self.assertEqual(routine.status, "closed")
        mock_notify.assert_called_once_with("expire", routine)

        self.assertFalse(service.Routine.expire(routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Routine.notify")
    def test_unexpire(self, mock_notify):

        routine = self.sample.routine("unit", "hey", status="closed", data={
            "text": "hey",
            "expired": True,
            "end": 0
        })

        self.assertTrue(service.Routine.unexpire(routine))
        self.assertFalse(routine.data["expired"])
        self.assertNotIn("end", routine.data)
        self.assertEqual(routine.status, "opened")
        mock_notify.assert_called_once_with("unexpire", routine)

        self.assertFalse(service.Routine.unexpire(routine))
        mock_notify.assert_called_once()

class TestRoutineCL(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("routine", {
            "name": "unit.test",
            "description": "integrate"
        })

        template_id = self.sample.template("test", "routine", {"a": 1}).id

        @klotio_sqlalchemy_restful.session
        def blank_fields():
            return {"fields": service.RoutineCL.fields().to_list()}

        self.app.add_url_rule('/blank_fields/routinecl', 'blank_fields', blank_fields)

        self.assertEqual(self.api.get('/blank_fields/routinecl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        @klotio_sqlalchemy_restful.session
        def template_fields():
            return {"fields": service.RoutineCL.fields({"template_id": template_id}).to_list()}

        self.app.add_url_rule('/template_fields/routinecl', 'template_fields', template_fields)

        self.assertEqual(self.api.get('/template_fields/routinecl').json["fields"], [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        template_id = self.sample.template("test", "routine", {"a": 1}).id

        response = self.api.options("/routine")

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            }
                        },
                        {
                            "name": "status",
                            "options": ['opened', 'closed'],
                            "style": "radios"
                        },
                        {
                            "name": "template_id",
                            "label": "template",
                            "options": [template_id],
                            "labels": {template_id: "test"},
                            "style": "select",
                            "trigger": True,
                            "optional": True
                        },
                        {
                            "name": "name"
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True
                        }
                    ]
                }
            }
        })

        response = self.api.options("/routine", json={"routine": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "errors": ["missing value"]
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True
            },
            {
                "name": "name",
                "errors": ["missing value"]
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options("/routine", json={"routine": {
            "person_id": 1,
            "status": "opened",
            "template_id": template_id
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "value": "opened"
            },
            {
                "name": "template_id",
                "label": "template",
                "options": [template_id],
                "labels": {str(template_id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template_id
            },
            {
                "name": "name",
                "value": "test"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "value": "a: 1\n",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_post(self):

        response = self.api.post("/routine", json={
            "routine": {
                "person_id": 1,
                "name": "unit",
                "status": "opened",
                "created": 6,
                "data": {
                    "text": "hey",
                    "tasks": [{
                        "text": "ya"
                    }]
                }
            }
        })

        self.assertStatusModel(response, 201, "routine", {
            "person_id": 1,
            "name": "unit",
            "status": "opened",
            "created": 6,
            "updated": 7,
            "data": {
                "start": 7,
                "text": "hey",
                "notified": 7,
                "tasks": [{
                    "id": 0,
                    "text": "ya",
                    "start": 7,
                    "notified": 7
                }]
            }
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 201,
                "json": {
                    "routine": {
                        "person_id": 1,
                        "name": "unit",
                        "status": "opened",
                        "created": 6,
                        "updated": 7,
                        "data": {
                            "start": 7,
                            "text": "hey",
                            "notified": 7,
                            "tasks": [{
                                "id": 0,
                                "text": "ya",
                                "start": 7,
                                "notified": 7
                            }]
                        }
                    }
                }
            }
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_get(self):

        self.sample.routine("unit", "test", created=7)
        self.sample.routine("test", "unit", created=6)

        self.assertStatusModels(self.api.get("/routine"), 200, "routines", [
            {
                "name": "test"
            },
            {
                "name": "unit"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "routines": [
                        {
                            "name": "test"
                        },
                        {
                            "name": "unit"
                        }
                    ]
                }
            }
        })

        self.assertStatusModels(self.api.get("/routine?since=0&status=opened"), 200, "routines", [
            {
                "name": "test"
            }
        ])

class TestRoutineRUD(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("klotio.integrations", klotio_unittest.MockIntegrations())
    def test_fields(self):

        klotio.integrations.add("routine", {
            "name": "unit.test",
            "description": "integrate"
        })

        @klotio_sqlalchemy_restful.session
        def fields():
            return {"fields": service.RoutineRUD.fields().to_list()}

        self.app.add_url_rule('/fields/routinerud', 'fields', fields)

        self.assertEqual(self.api.get('/fields/routinerud').json["fields"], [
            {
                "name": "id",
                "readonly": True
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                }
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
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
            },
            {
                "name": "unit.test",
                "description": "integrate"
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    def test_options(self):

        routine_id = self.sample.routine("unit", "test", status="opened", data={"text": 1}).id

        response = self.api.options(f"/routine/{routine_id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": routine_id,
                "original": routine_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "value": 1,
                "original": 1
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "value": "opened",
                "original": "opened"
            },
            {
                "name": "name",
                "value": "test",
                "original": "test"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "value": "text: 1\n",
                "original": "text: 1\n"
            }
        ])

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "fields": [
                        {
                            "name": "id",
                            "readonly": True,
                            "value": routine_id,
                            "original": routine_id
                        },
                        {
                            "name": "person_id",
                            "label": "person",
                            "style": "radios",
                            "integrate": {
                                "url": "http://api.people-nandy-io/integrate"
                            },
                            "options": [
                                1,
                                2
                            ],
                            "labels": {
                                1: "unit",
                                2: "test"
                            },
                            "value": 1,
                            "original": 1
                        },
                        {
                            "name": "status",
                            "options": ['opened', 'closed'],
                            "style": "radios",
                            "value": "opened",
                            "original": "opened"
                        },
                        {
                            "name": "name",
                            "value": "test",
                            "original": "test"
                        },
                        {
                            "name": "created",
                            "style": "datetime",
                            "readonly": True,
                            "value": 7,
                            "original": 7
                        },
                        {
                            "name": "updated",
                            "style": "datetime",
                            "readonly": True,
                            "value": 8,
                            "original": 8
                        },
                        {
                            "name": "yaml",
                            "style": "textarea",
                            "optional": True,
                            "value": "text: 1\n",
                            "original": "text: 1\n"
                        }
                    ]
                }
            }
        })

        response = self.api.options(f"/routine/{routine_id}", json={"routine": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": routine_id,
                "original": routine_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "errors": ["missing value"]
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "original": "opened",
                "errors": ["missing value"]
            },
            {
                "name": "name",
                "original": "test",
                "errors": ["missing value"]
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "text: 1\n"
            }
        ], [
            "unknown field 'nope'"
        ])

        response = self.api.options(f"/routine/{routine_id}", json={"routine": {
            "person_id": 2,
            "name": "yup",
            "status": "closed",
            "yaml": 'text: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": routine_id,
                "original": routine_id
            },
            {
                "name": "person_id",
                "label": "person",
                "style": "radios",
                "integrate": {
                    "url": "http://api.people-nandy-io/integrate"
                },
                "options": [
                    1,
                    2
                ],
                "labels": {
                    '1': "unit",
                    '2': "test"
                },
                "original": 1,
                "value": 2
            },
            {
                "name": "status",
                "options": ['opened', 'closed'],
                "style": "radios",
                "original": "opened",
                "value": "closed"
            },
            {
                "name": "name",
                "original": "test",
                "value": "yup"
            },
            {
                "name": "created",
                "style": "datetime",
                "readonly": True,
                "value": 7,
                "original": 7
            },
            {
                "name": "updated",
                "style": "datetime",
                "readonly": True,
                "value": 8,
                "original": 8
            },
            {
                "name": "yaml",
                "style": "textarea",
                "optional": True,
                "original": "text: 1\n",
                "value": "text: 2"
            }
        ])

    def test_get(self):

        routine = self.sample.routine("test", "unit")

        self.assertStatusModel(self.api.get(f"/routine/{routine.id}"), 200, "routine", {
            "person_id": routine.person_id,
            "name": "unit",
            "status": "opened",
            "created": 7,
            "data": {
                "text": "routine it"
            },
            "yaml": "text: routine it\n"
        })

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 200,
                "json": {
                    "routine": {
                        "person_id": routine.person_id,
                        "name": "unit",
                        "status": "opened",
                        "created": 7,
                        "data": {
                            "text": "routine it"
                        },
                        "yaml": "text: routine it\n"
                    }
                }
            }
        })

    def test_patch(self):

        routine_id = self.sample.routine("test", "unit").id

        self.assertStatusValue(self.api.patch(f"/routine/{routine_id}", json={
            "routine": {
                "status": "closed"
            }
        }), 202, "updated", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": 1
                }
            }
        })

        self.assertStatusModel(self.api.get(f"/routine/{routine_id}"), 200, "routine", {
            "status": "closed"
        })

    def test_delete(self):

        routine_id = self.sample.routine("test", "unit").id

        self.assertStatusValue(self.api.delete(f"/routine/{routine_id}"), 202, "deleted", 1)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "deleted": 1
                }
            }
        })

        self.assertStatusModels(self.api.get("/routine"), 200, "routines", [])

class TestRoutineA(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "tasks": [
                {
                    "text": "do it",
                    "start": 0
                },
                {
                    "text": "moo it",
                    "start": 0
                }
            ]
        })

        # remind

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/remind"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.data["notified"], 7)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": True
                }
            }
        })

        # next

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/next"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.data["tasks"][0]["end"], 7)

        # pause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/pause"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/pause"), 202, "updated", False)

        # unpause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unpause"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unpause"), 202, "updated", False)

        # skip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/skip"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/skip"), 202, "updated", False)

        # unskip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unskip"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unskip"), 202, "updated", False)

        # complete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/complete"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "closed")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/complete"), 202, "updated", False)

        # uncomplete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/uncomplete"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "opened")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/uncomplete"), 202, "updated", False)

        # expire

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/expire"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/expire"), 202, "updated", False)

        # unexpire

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unexpire"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unexpire"), 202, "updated", False)


class TestTask(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_notify(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "node": "plimpton",
            "tasks": [{
                "text": "you"
            }]
        })

        service.Task.notify("test", routine.data["tasks"][0], routine)

        self.assertEqual(routine.updated, 7)
        self.assertEqual(routine.data["notified"], 7)
        self.assertEqual(routine.data["tasks"][0]["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "task",
            "action": "test",
            "task": routine.data["tasks"][0],
            "routine": service.Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    def test_remind(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [{
                "text": "do it"
            }]
        })

        self.assertTrue(service.Task.remind(routine.data["tasks"][0], routine))
        mock_notify.assert_called_once_with("remind", routine.data["tasks"][0], routine)

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    def test_pause(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [{
                "text": "do it"
            }]
        })

        self.assertTrue(service.Task.pause(routine.data["tasks"][0], routine))
        self.assertTrue(routine.data["tasks"][0]["paused"])
        mock_notify.assert_called_once_with("pause", routine.data["tasks"][0], routine)

        self.assertFalse(service.Task.pause(routine.data["tasks"][0], routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    def test_unpause(self, mock_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [{
                "text": "do it",
                "paused": True
            }]
        })

        self.assertTrue(service.Task.unpause(routine.data["tasks"][0], routine))
        self.assertFalse(routine.data["tasks"][0]["paused"])
        mock_notify.assert_called_once_with("unpause", routine.data["tasks"][0], routine)

        self.assertFalse(service.Task.unpause(routine.data["tasks"][0], routine))
        mock_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    @unittest.mock.patch("service.Routine.notify")
    def test_skip(self, mock_routine_notify, mock_task_notify):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [{
                "text": "do it"
            }]
        })

        self.assertTrue(service.Task.skip(routine.data["tasks"][0], routine))
        self.assertTrue(routine.data["tasks"][0]["skipped"])
        self.assertEqual(routine.data["tasks"][0]["start"], 7)
        self.assertEqual(routine.data["tasks"][0]["end"], 7)
        self.assertEqual(routine.status, "closed")
        mock_task_notify.assert_called_once_with("skip", routine.data["tasks"][0], routine)
        mock_routine_notify.assert_called_once_with("complete", routine)

        self.assertFalse(service.Task.skip(routine.data["tasks"][0], routine))
        mock_task_notify.assert_called_once()
        mock_routine_notify.assert_called_once()

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    @unittest.mock.patch("service.Routine.notify")
    def test_unskip(self, mock_routine_notify, mock_task_notify):

        routine = self.sample.routine("unit", "hey", status="closed", data={
            "text": "hey",
            "language": "cursing",
            "end": 0,
            "tasks": [{
                "text": "do it",
                "skipped": True,
                "end": 0
            }]
        })

        self.assertTrue(service.Task.unskip(routine.data["tasks"][0], routine))
        self.assertFalse(routine.data["tasks"][0]["skipped"])
        self.assertNotIn("end", routine.data["tasks"][0])
        self.assertEqual(routine.status, "opened")
        mock_task_notify.assert_called_once_with("unskip", routine.data["tasks"][0], routine)
        mock_routine_notify.assert_called_once_with("uncomplete", routine)

        self.assertFalse(service.Task.unskip(routine.data["tasks"][0], routine))
        mock_task_notify.assert_called_once()
        mock_routine_notify.assert_called_once()

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_complete(self, mock_notify):

        todo = self.sample.todo("unit")

        routine_id = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [{
                "text": "do it",
                "todo": todo.id
            }]
        }).id

        @klotio_sqlalchemy_restful.session
        def complete():
            routine = self.session.query(nandyio_chore_models.Routine).get(flask.request.json["complete"])
            response = {"complete": service.Task.complete(routine.data["tasks"][0], routine)}
            flask.request.session.commit()
            return response

        self.app.add_url_rule('/complete/task', 'complete', complete)

        self.assertTrue(self.api.get("/complete/task", json={"complete": routine_id}).json["complete"])

        routine = self.session.query(nandyio_chore_models.Routine).get(routine_id)

        self.assertTrue(routine.data["tasks"][0]["end"], 7)
        self.assertEqual(routine.status, "closed")

        self.assertEqual(mock_notify.call_args_list[0].args[0], {
            "kind": "task",
            "action": "complete",
            "routine": {
                "id": 1,
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 7,
                "updated": 7,
                "data":{
                    "text": "hey",
                    "language": "cursing",
                    "tasks": [
                        {
                            "text":"do it",
                            "todo": 1,
                            "end": 7,
                            "start": 7,
                            "notified": 7
                        }
                    ],
                    "notified": 7
                },
                "yaml": "language: cursing\nnotified: 7\ntasks:\n- end: 7\n  notified: 7\n  start: 7\n  text: do it\n  todo: 1\ntext: hey\n"
            },
            "task": {
                "end": 7,
                "notified": 7,
                "start": 7,
                "text": "do it",
                "todo": 1
            },
            "person": nandyio_people_integrations.Person.model(name="unit")
        })
        self.assertEqual(mock_notify.call_args_list[1].args[0], {
            "kind": "routine",
            "action": "complete",
            "routine": service.Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        self.assertFalse(self.api.get("/complete/task", json={"complete": routine_id}).json["complete"])

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio_sqlalchemy_restful.notify")
    def test_uncomplete(self, mock_notify):

        todo = self.sample.todo("unit", status="closed", data={"end": 0})

        routine_id = self.sample.routine("unit", "hey", status="closed", data={
            "text": "hey",
            "language": "cursing",
            "end": 0,
            "tasks": [{
                "text": "do it",
                "end": 0,
                "todo": todo.id
            }]
        }).id

        @klotio_sqlalchemy_restful.session
        def uncomplete():
            routine = self.session.query(nandyio_chore_models.Routine).get(flask.request.json["uncomplete"])
            response = {"uncomplete": service.Task.uncomplete(routine.data["tasks"][0], routine)}
            flask.request.session.commit()
            return response

        self.app.add_url_rule('/uncomplete/task', 'uncomplete', uncomplete)

        self.assertTrue(self.api.get("/uncomplete/task", json={"uncomplete": routine_id}).json["uncomplete"])

        routine = self.session.query(nandyio_chore_models.Routine).get(routine_id)
        self.session.commit()

        self.assertNotIn("end", routine.data["tasks"][0])
        self.assertEqual(routine.status, "opened")

        item = self.session.query(nandyio_chore_models.ToDo).get(todo.id)
        self.assertEqual(item.status, "opened")

        self.assertEqual(mock_notify.call_args_list[0].args[0], {
            "kind": "task",
            "action": "uncomplete",
            "routine": {
                "id": 1,
                "person_id": 1,
                "name": "hey",
                "status": "closed",
                "created": 7,
                "updated": 7,
                "data":  {
                    "text": "hey",
                    "language": "cursing",
                    "tasks": [
                        {
                            "text": "do it",
                            "todo": 1,
                            "notified": 7
                        }
                    ],
                    "notified": 7,
                    "end": 0
                },
                "yaml": "end: 0\nlanguage: cursing\nnotified: 7\ntasks:\n- notified: 7\n  text: do it\n  todo: 1\ntext: hey\n"
            },
            "task": {
                "notified": 7,
                "text": "do it",
                "todo": 1
            },
            "person": nandyio_people_integrations.Person.model(name="unit")
        })
        self.assertEqual(mock_notify.call_args_list[1].args[0], {
            "kind": "routine",
            "action": "uncomplete",
            "routine": service.Routine.response(routine),
            "person": nandyio_people_integrations.Person.model(name="unit")
        })

        self.assertFalse(self.api.get("/uncomplete/task", json={"uncomplete": routine_id}).json["uncomplete"])

class TestTaskA(TestRestful):

    @unittest.mock.patch("nandyio_people_integrations.Person", nandyio_people_unittest.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [
                {
                    "text": "do it"
                }
            ]
        })

        # remind

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/remind"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.data["tasks"][0]["notified"], 7)

        self.assertLogged(self.app.logger, "debug", "response", extra={
            "response": {
                "status_code": 202,
                "json": {
                    "updated": True
                }
            }
        })

        # pause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/pause"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["tasks"][0]["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/pause"), 202, "updated", False)

        # unpause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unpause"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["tasks"][0]["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unpause"), 202, "updated", False)

        # skip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/skip"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["tasks"][0]["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/skip"), 202, "updated", False)

        # unskip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unskip"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["tasks"][0]["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unskip"), 202, "updated", False)

        # complete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/complete"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "closed")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/complete"), 202, "updated", False)

        # uncomplete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/uncomplete"), 202, "updated", True)
        item = self.session.query(nandyio_chore_models.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "opened")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/uncomplete"), 202, "updated", False)
