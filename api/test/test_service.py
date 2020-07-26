import unittest
import unittest.mock
import klotio.unittest
import nandyio.unittest.people

import os
import json
import yaml

import flask
import opengui
import sqlalchemy.exc

import mysql
import test_mysql

import service

class TestRest(klotio.unittest.TestCase):

    maxDiff = None

    @classmethod
    @unittest.mock.patch.dict(os.environ, {
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_CHANNEL": "stuff"
    })
    @unittest.mock.patch("redis.StrictRedis", klotio.unittest.MockRedis)
    def setUpClass(cls):

        cls.app = service.app()
        cls.api = cls.app.test_client()

    def setUp(self):

        self.app.mysql.drop_database()
        self.app.mysql.create_database()

        self.session = self.app.mysql.session()
        self.sample = test_mysql.Sample(self.session)

        self.app.mysql.Base.metadata.create_all(self.app.mysql.engine)

    def tearDown(self):

        self.session.close()
        self.app.mysql.drop_database()


class TestHealth(TestRest):

    def test_get(self):

        self.assertEqual(self.api.get("/health").json, {"message": "OK"})


class TestGroup(TestRest):

    @unittest.mock.patch.dict(os.environ, {
        "NODE_NAME": "barry"
    })
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
            unittest.mock.call("http://barry:8083/app/chore.nandy.io/member"),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call().json()
        ])


class TestTemplate(TestRest):

    def test_validate(self):

        fields = service.TemplateCL.fields()

        self.assertFalse(service.Template.validate(fields))

        self.assertFields(fields, [
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
        ])

        self.assertEqual(fields.errors, [])

        fields = service.TemplateCL.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Template.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

        fields = service.TemplateRUD.fields()

        self.assertFalse(service.Template.validate(fields))

        self.assertFields(fields, [
            {
                "name": "id",
                "readonly": True
            },
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
        ])

        self.assertEqual(fields.errors, [])

        fields = service.TemplateRUD.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Template.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

    @unittest.mock.patch("flask.request")
    def test_retrieve(self, mock_request):

        mock_request.session = self.session

        template = self.sample.template("unit", "todo", {"a": 1})

        self.assertEqual(service.Template.retrieve(template.id).name, "unit")

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    def test_integrations(self, mock_open, mock_glob):

        def glob(pattern):

            return [f"/opt/service/config/integration_unit.test_{pattern.split('_')[-1].split('.')[0]}.fields.yaml"]

        mock_glob.side_effect = glob

        def contents(path, mode):

            return unittest.mock.mock_open(read_data=yaml.safe_dump({"description": path.split('_')[-1].split('.')[0]})).return_value

        mock_open.side_effect = contents

        self.assertEqual(service.Template.integrations("template"), [{
            "name": "unit.test",
            "description": "template"
        }])

        mock_glob.assert_called_once_with("/opt/service/config/integration_*_template.fields.yaml")

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_template.fields.yaml", "r")

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

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    def test_request(self, mock_open, mock_glob):

        def glob(pattern):

            return [f"/opt/service/config/integration_unit.test_{pattern.split('_')[-1].split('.')[0]}.fields.yaml"]

        mock_glob.side_effect = glob

        def contents(path, mode):

            return unittest.mock.mock_open(read_data=yaml.safe_dump({"description": path.split('_')[-1].split('.')[0]})).return_value

        mock_open.side_effect = contents

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

        mock_glob.assert_called_once_with("/opt/service/config/integration_*_area.fields.yaml")

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_area.fields.yaml", "r")

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

        mock_glob.assert_called_with("/opt/service/config/integration_*_template.fields.yaml")

        mock_open.assert_called_with("/opt/service/config/integration_unit.test_template.fields.yaml", "r")

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    def test_response(self, mock_open, mock_glob):

        def glob(pattern):

            return [f"/opt/service/config/integration_unit.test_{pattern.split('_')[-1].split('.')[0]}.fields.yaml"]

        mock_glob.side_effect = glob

        def contents(path, mode):

            return unittest.mock.mock_open(read_data=yaml.safe_dump({"description": path.split('_')[-1].split('.')[0]})).return_value

        mock_open.side_effect = contents

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

        mock_glob.assert_called_once_with("/opt/service/config/integration_*_area.fields.yaml")

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_area.fields.yaml", "r")

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

        mock_glob.assert_called_with("/opt/service/config/integration_*_template.fields.yaml")

        mock_open.assert_called_with("/opt/service/config/integration_unit.test_template.fields.yaml", "r")

    @unittest.mock.patch("flask.request")
    def test_choices(self, mock_request):

        mock_request.session = self.session

        unit = self.sample.template("unit", "todo")
        test = self.sample.template("test", "act")
        rest = self.sample.template("rest", "todo")

        (ids, labels) = service.Template.choices("todo")

        self.assertEqual(ids, [rest.id, unit.id])
        self.assertEqual(labels, {rest.id: "rest", unit.id: "unit"})

    def test_form(self):

        self.assertEqual(service.Template.form({"kind": "unit"}, {"kind": "test"}), "unit")
        self.assertEqual(service.Template.form({}, {"kind": "test"}), "test")
        self.assertEqual(service.Template.form({}, {}), "template")

class TestTemplateCL(TestRest):

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    def test_fields(self, mock_open, mock_glob):

        def glob(pattern):

            return [f"/opt/service/config/integration_unit.test_{pattern.split('_')[-1].split('.')[0]}.fields.yaml"]

        mock_glob.side_effect = glob

        def contents(path, mode):

            return unittest.mock.mock_open(read_data=yaml.safe_dump({"description": path.split('_')[-1].split('.')[0]})).return_value

        mock_open.side_effect = contents

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

class TestTemplateRUD(TestRest):

    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    def test_fields(self, mock_open, mock_glob):

        def glob(pattern):

            return [f"/opt/service/config/integration_unit.test_{pattern.split('_')[-1].split('.')[0]}.fields.yaml"]

        mock_glob.side_effect = glob

        def contents(path, mode):

            return unittest.mock.mock_open(read_data=yaml.safe_dump({"description": path.split('_')[-1].split('.')[0]})).return_value

        mock_open.side_effect = contents

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

    def test_delete(self):

        template = self.sample.template("unit", "todo")

        self.assertStatusValue(self.api.delete(f"/template/{template.id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/template"), 200, "templates", [])


class TestArea(TestRest):

    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_validate(self, mock_request):

        mock_request.session = self.session

        template = self.sample.template("test", "area", {"a": 1})

        fields = service.AreaCL.fields()

        self.assertFalse(service.Area.validate(fields))

        self.assertFields(fields, [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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
        ])

        self.assertEqual(fields.errors, [])

        fields = service.AreaCL.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Area.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

        fields = service.AreaRUD.fields()

        self.assertFalse(service.Area.validate(fields))

        self.assertFields(fields, [
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
                    1: "unit",
                    2: "test"
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
                "name": "name",
                "errors": ["missing value"]
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
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(fields.errors, [])

        fields = service.AreaRUD.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Area.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

    @unittest.mock.patch("flask.request")
    def test_retrieve(self, mock_request):

        mock_request.session = self.session

        area = self.sample.area("unit", "test")

        self.assertEqual(service.Area.retrieve(area.id).name, "test")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self, mock_request):

        mock_request.session = self.session

        # basic

        self.assertEqual(service.Area.build(**{
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "positive",
                "created": 1,
                "updated": 2
            }
        }), {
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

        self.assertEqual(service.Area.build(**{
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template = self.sample.template("unit", "area", data={
            "by": "template_id",
            "status": "negative",
            "person": "unit"
        })

        self.assertEqual(service.Area.build(**{
            "name": "hey",
            "template_id": template.id
        }), {
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

        self.assertEqual(service.Area.build(**{
            "name": "hey",
            "template": "unit"
        }), {
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_notify(self, mock_notify):

        model = self.sample.area("unit", "test")

        service.Area.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "area",
            "action": "test",
            "area": service.Area.response(model),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_create(self, mock_notify, mock_request):

        mock_request.session = self.session

        model = service.Area.create(**{
            "person_id": 1,
            "name": "unit",
            "created": 6,
            "data": {
                "text": "hey"
            }
        })

        self.assertEqual(model.person_id, 1)
        self.assertEqual(model.name, "unit")
        self.assertEqual(model.status, "positive")
        self.assertEqual(model.created, 6)
        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data, {
            "text": "hey",
            "notified": 7
        })

        item = self.session.query(mysql.Area).get(model.id)
        flask.request.session.commit()
        self.assertEqual(item.name, "unit")

        mock_notify.assert_called_once_with({
            "kind": "area",
            "action": "create",
            "area": service.Area.response(model),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Status.notify")
    def test_wrong(self, mock_notify, mock_request):

        mock_request.session = self.session

        model = self.sample.area("unit", "hey", data={
            "todo": {
                "name": "Unit",
                "text": "test"
            }
        })

        self.assertTrue(service.Area.wrong(model))
        self.assertEqual(model.status, "negative")
        item = self.session.query(mysql.ToDo).all()[0]
        self.assertEqual(item.person_id, model.person_id)
        self.assertEqual(item.name, "Unit")
        self.assertEqual(item.data["text"], "test")
        self.assertEqual(item.data["area"], model.id)
        mock_notify.assert_has_calls([
            unittest.mock.call("wrong", model),
            unittest.mock.call("create", item)
        ])

        self.assertFalse(service.Area.wrong(model))
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

class TestAreaCL(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_klotio_open, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_area.fields.yaml":
                return ["/opt/service/config/integration_unit.test_area.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_klotio_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value,
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        template = self.sample.template("test", "area", {"a": 1})

        self.assertEqual(service.AreaCL.fields().to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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

        mock_klotio_open.assert_called_once_with("/opt/service/config/integration_unit.test_area.fields.yaml", "r")

        self.assertEqual(service.AreaCL.fields({"template_id": template.id}).to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
                "style": "select",
                "trigger": True,
                "value": template.id,
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_area.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        template = self.sample.template("test", "area", {"a": 1})

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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
            "template_id": template.id
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
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

        area_id = response.json["area"]["id"]

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

        self.assertStatusModels(self.api.get("/area?since=0&status=positive"), 200, "areas", [
            {
                "name": "unit"
            }
        ])

class TestAreaRUD(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_area.fields.yaml":
                return ["/opt/service/config/integration_unit.test_area.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        self.assertEqual(service.AreaRUD.fields().to_list(), [
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_area.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        area = self.sample.area("unit", "test", status="positive", data={"a": 1})

        response = self.api.options(f"/area/{area.id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": area.id,
                "original": area.id
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

        response = self.api.options(f"/area/{area.id}", json={"area": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": area.id,
                "original": area.id
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


        response = self.api.options(f"/area/{area.id}", json={"area": {
            "person_id": 2,
            "name": "yup",
            "status": "negative",
            "yaml": 'b: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": area.id,
                "original": area.id
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

        area = self.sample.area("unit", "test")

        self.assertStatusModel(self.api.get(f"/area/{area.id}"), 200, "area", {
            "name": "test"
        })

    def test_patch(self):

        area = self.sample.area("unit", "test")

        self.assertStatusValue(self.api.patch(f"/area/{area.id}", json={
            "area": {
                "status": "negative"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/area/{area.id}"), 200, "area", {
            "name": "test",
            "status": "negative"
        })

    def test_delete(self):

        area = self.sample.area("unit", "test")

        self.assertStatusValue(self.api.delete(f"/area/{area.id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/area"), 200, "areas", [])

class TestAreaA(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        model = self.sample.area("unit", "hey")

        # wrong

        self.assertStatusValue(self.api.patch(f"/area/{model.id}/wrong"), 202, "updated", True)
        item = self.session.query(mysql.Area).get(model.id)
        self.session.commit()
        self.assertEqual(item.status, "negative")
        self.assertStatusValue(self.api.patch(f"/area/{model.id}/wrong"), 202, "updated", False)

        # right

        self.assertStatusValue(self.api.patch(f"/area/{model.id}/right"), 202, "updated", True)
        item = self.session.query(mysql.Area).get(model.id)
        self.session.commit()
        self.assertEqual(item.status, "positive")
        self.assertStatusValue(self.api.patch(f"/area/{model.id}/right"), 202, "updated", False)


class TestAct(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    def test_validate(self, mock_request):

        mock_request.session = self.session

        template = self.sample.template("test", "act", {"a": 1})

        fields = service.ActCL.fields()

        self.assertFalse(service.Act.validate(fields))

        self.assertFields(fields, [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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
        ])

        self.assertEqual(fields.errors, [])

        fields = service.ActCL.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Act.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

        fields = service.ActRUD.fields()

        self.assertFalse(service.Act.validate(fields))

        self.assertFields(fields, [
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
                    1: "unit",
                    2: "test"
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
                "name": "name",
                "errors": ["missing value"]
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
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(fields.errors, [])

        fields = service.ActRUD.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Act.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

    @unittest.mock.patch("flask.request")
    def test_retrieve(self, mock_request):

        mock_request.session = self.session

        act = self.sample.act("unit", "test")

        self.assertEqual(service.Act.retrieve(act.id).name, "test")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self, mock_request):

        mock_request.session = self.session

        # basic

        self.assertEqual(service.Act.build(**{
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "positive",
                "created": 1,
                "updated": 2
            }
        }), {
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

        self.assertEqual(service.Act.build(**{
            "template": {
                "by": "template",
                "name": "hey",
                "person": "unit",
                "person": "nope"
            },
            "person": "unit"
        }), {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template = self.sample.template("unit", "act", data={
            "by": "template_id",
            "status": "negative",
            "person": "unit"
        })

        self.assertEqual(service.Act.build(**{
            "name": "hey",
            "template_id": template.id
        }), {
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

        self.assertEqual(service.Act.build(**{
            "name": "hey",
            "template": "unit"
        }), {
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_notify(self, mock_notify):

        model = self.sample.act("unit", "test")

        service.Act.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "act",
            "action": "test",
            "act": service.Act.response(model),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_create(self, mock_notify, mock_request):

        mock_request.session = self.session

        model = service.Act.create(**{
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
        })

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

        todo = self.session.query(mysql.ToDo).filter_by(name="Unit").all()[0]
        flask.request.session.commit()
        self.assertEqual(todo.data["text"], "test")

        item = self.session.query(mysql.Act).get(model.id)
        flask.request.session.commit()
        self.assertEqual(item.name, "unit")

        mock_notify.assert_has_calls([
            unittest.mock.call({
                "kind": "act",
                "action": "create",
                "act": service.Act.response(model),
                "person": nandyio.unittest.people.MockPerson.model(id=1)
            }),
            unittest.mock.call({
                "kind": "todo",
                "action": "create",
                "todo": service.ToDo.response(todo),
                "person": nandyio.unittest.people.MockPerson.model(id=1)
            })
        ])

        model = service.Act.create(**{
            "person_id": 1,
            "name": "test",
            "status": "negative",
            "created": 6,
            "data": {
                "text": "hey",
                "todo": True
            }
        })

        todo = self.session.query(mysql.ToDo).filter_by(name="test").all()[0]
        flask.request.session.commit()
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

class TestActCL(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_klotio_open, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_act.fields.yaml":
                return ["/opt/service/config/integration_unit.test_act.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_klotio_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value,
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        template = self.sample.template("test", "act", {"a": 1})

        self.assertEqual(service.ActCL.fields().to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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

        mock_klotio_open.assert_called_once_with("/opt/service/config/integration_unit.test_act.fields.yaml", "r")

        self.assertEqual(service.ActCL.fields({"template_id": template.id}).to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_act.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        template = self.sample.template("test", "act", {"a": 1})

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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
            "template_id": template.id
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
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

        act_id = response.json["act"]["id"]

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

        self.assertStatusModels(self.api.get("/act?since=0&status=positive"), 200, "acts", [
            {
                "name": "unit"
            }
        ])

class TestActRUD(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_act.fields.yaml":
                return ["/opt/service/config/integration_unit.test_act.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        self.assertEqual(service.ActRUD.fields().to_list(), [
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_act.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        act = self.sample.act("unit", "test", status="positive", data={"a": 1})

        response = self.api.options(f"/act/{act.id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": act.id,
                "original": act.id
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

        response = self.api.options(f"/act/{act.id}", json={"act": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": act.id,
                "original": act.id
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

        response = self.api.options(f"/act/{act.id}", json={"act": {
            "person_id": 2,
            "name": "yup",
            "status": "negative",
            "yaml": 'b: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": act.id,
                "original": act.id
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

        act = self.sample.act("unit", "test")

        self.assertStatusModel(self.api.get(f"/act/{act.id}"), 200, "act", {
            "name": "test"
        })

    def test_patch(self):

        act = self.sample.act("unit", "test")

        self.assertStatusValue(self.api.patch(f"/act/{act.id}", json={
            "act": {
                "status": "negative"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/act/{act.id}"), 200, "act", {
            "name": "test",
            "status": "negative"
        })

    def test_delete(self):

        act = self.sample.act("unit", "test")

        self.assertStatusValue(self.api.delete(f"/act/{act.id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/act"), 200, "acts", [])

class TestActA(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        model = self.sample.act("unit", "hey")

        # wrong

        self.assertStatusValue(self.api.patch(f"/act/{model.id}/wrong"), 202, "updated", True)
        item = self.session.query(mysql.Act).get(model.id)
        self.session.commit()
        self.assertEqual(item.status, "negative")
        self.assertStatusValue(self.api.patch(f"/act/{model.id}/wrong"), 202, "updated", False)

        # right

        self.assertStatusValue(self.api.patch(f"/act/{model.id}/right"), 202, "updated", True)
        item = self.session.query(mysql.Act).get(model.id)
        self.session.commit()
        self.assertEqual(item.status, "positive")
        self.assertStatusValue(self.api.patch(f"/act/{model.id}/right"), 202, "updated", False)

class TestToDo(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    def test_validate(self, mock_request):

        mock_request.session = self.session

        template = self.sample.template("test", "todo", {"a": 1})

        fields = service.ToDoCL.fields()

        self.assertFalse(service.ToDo.validate(fields))

        self.assertFields(fields, [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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
        ])

        self.assertEqual(fields.errors, [])

        fields = service.ToDoCL.fields(values={"yaml": "a:1"})

        self.assertFalse(service.ToDo.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

        fields = service.ToDoRUD.fields()

        self.assertFalse(service.ToDo.validate(fields))

        self.assertFields(fields, [
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
                    1: "unit",
                    2: "test"
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
                "name": "name",
                "errors": ["missing value"]
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
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(fields.errors, [])

        fields = service.ToDoRUD.fields(values={"yaml": "a:1"})

        self.assertFalse(service.ToDo.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

    @unittest.mock.patch("flask.request")
    def test_retrieve(self, mock_request):

        mock_request.session = self.session

        todo = self.sample.todo("unit", "test")

        self.assertEqual(service.ToDo.retrieve(todo.id).name, "test")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self, mock_request):

        mock_request.session = self.session

        # basic

        self.assertEqual(service.ToDo.build(**{
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2
            }
        }), {
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

        self.assertEqual(service.ToDo.build(**{
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template = self.sample.template("unit", "todo", data={
            "by": "template_id",
            "status": "closed",
            "person": "unit"
        })

        self.assertEqual(service.ToDo.build(**{
            "name": "hey",
            "template_id": template.id
        }), {
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

        self.assertEqual(service.ToDo.build(**{
            "name": "hey",
            "template": "unit"
        }), {
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_notify(self, mock_notify):

        model = self.sample.todo("unit", "test")

        service.ToDo.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "todo",
            "action": "test",
            "todo": service.ToDo.response(model),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_create(self, mock_notify, mock_request):

        mock_request.session = self.session

        model = service.ToDo.create(**{
            "person_id": 1,
            "name": "unit",
            "created": 6,
            "data": {
                "text": "hey"
            }
        })

        self.assertEqual(model.person_id, 1)
        self.assertEqual(model.name, "unit")
        self.assertEqual(model.status, "opened")
        self.assertEqual(model.created, 6)
        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data, {
            "text": "hey",
            "notified": 7
        })

        item = self.session.query(mysql.ToDo).get(model.id)
        flask.request.session.commit()
        self.assertEqual(item.name, "unit")

        mock_notify.assert_called_once_with({
            "kind": "todo",
            "action": "create",
            "todo": service.ToDo.response(model),
            "person": nandyio.unittest.people.MockPerson.model(id=1)
        })

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_todos(self, mock_notify, mock_request):

        mock_request.session = self.session

        self.sample.todo("unit", status="closed")
        self.sample.todo("test")

        self.assertFalse(service.ToDo.todos({
            "person": "unit"
        }))
        mock_notify.assert_not_called()

        todo = self.sample.todo("unit")

        self.assertTrue(service.ToDo.todos({
            "person": "unit"
        }))
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.assertEqual(item.updated, 7)
        self.assertEqual(item.data["notified"], 7)
        mock_notify.assert_called_once_with({
            "kind": "todos",
            "action": "remind",
            "person": nandyio.unittest.people.MockPerson.model(name="unit"),
            "chore-speech.nandy.io": {},
            "todos": service.ToDo.responses([todo])
        })

        self.assertTrue(service.ToDo.todos({
            "person_id": 1,
            "chore-speech.nandy.io": {
                "language": "cursing"
            }
        }))
        mock_notify.assert_called_with({
            "kind": "todos",
            "action": "remind",
            "person": nandyio.unittest.people.MockPerson.model(name="unit"),
            "chore-speech.nandy.io": {"language": "cursing"},
            "todos": service.ToDo.responses([todo])
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.ToDo.notify")
    @unittest.mock.patch("klotio.service.notify", unittest.mock.MagicMock())
    def test_complete(self, mock_notify, mock_request):

        mock_request.session = self.session

        area = self.sample.area("unit", "test", status="negative")

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey",
            "area": area.id,
            "act": {
                "name": "Unit",
                "text": "test"
            }
        })

        self.assertTrue(service.ToDo.complete(todo))
        self.assertEqual(todo.status, "closed")
        self.assertTrue(todo.data["end"], 7)

        item = self.session.query(mysql.Area).get(area.id)
        self.assertEqual(item.status, "positive")
        mock_notify.assert_called_once_with("complete", todo)

        act = self.session.query(mysql.Act).filter_by(name="Unit").all()[0]
        self.assertEqual(act.person_id, todo.person_id)
        self.assertEqual(act.status, "positive")
        self.assertEqual(act.data["text"], "test")

        self.assertFalse(service.ToDo.complete(todo))
        mock_notify.assert_called_once()

        todo = self.sample.todo("unit", "hey", data={
            "text": "you",
            "area": area.id,
            "act": True,
            "notified": 7
        })

        service.ToDo.complete(todo)
        self.assertEqual(todo.status, "closed")
        self.assertTrue(todo.data["end"], 7)

        act = self.session.query(mysql.Act).filter_by(name="hey").all()[0]
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

class TestToDoCL(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_klotio_open, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_todo.fields.yaml":
                return ["/opt/service/config/integration_unit.test_todo.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_klotio_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value,
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        template = self.sample.template("test", "todo", {"a": 1})

        self.assertEqual(service.ToDoCL.fields().to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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

        mock_klotio_open.assert_called_once_with("/opt/service/config/integration_unit.test_todo.fields.yaml", "r")

        self.assertEqual(service.ToDoCL.fields({"template_id": template.id}).to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_todo.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        template = self.sample.template("test", "todo", {"a": 1})

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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
            "template_id": template.id
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
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

        todo_id = response.json["todo"]["id"]

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

        self.assertStatusModels(self.api.get("/todo?since=0&status=opened"), 200, "todos", [
            {
                "name": "unit"
            }
        ])

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify", unittest.mock.MagicMock)
    def test_patch(self):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        self.assertStatusValue(self.api.patch(f"/todo", json={
            "todos": {
                "person": "unit"
            }
        }), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.data["notified"], 7)

class TestToDoRUD(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_todo.fields.yaml":
                return ["/opt/service/config/integration_unit.test_todo.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        self.assertEqual(service.ToDoRUD.fields().to_list(), [
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_todo.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        todo = self.sample.todo("unit", "test", status="opened", data={"text": 1})

        response = self.api.options(f"/todo/{todo.id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": todo.id,
                "original": todo.id
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

        response = self.api.options(f"/todo/{todo.id}", json={"todo": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": todo.id,
                "original": todo.id
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

        response = self.api.options(f"/todo/{todo.id}", json={"todo": {
            "person_id": 2,
            "name": "yup",
            "status": "closed",
            "yaml": 'text: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": todo.id,
                "original": todo.id
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

        todo = self.sample.todo("unit", "test")

        self.assertStatusModel(self.api.get(f"/todo/{todo.id}"), 200, "todo", {
            "name": "test"
        })

    def test_patch(self):

        todo = self.sample.todo("unit", "test")

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}", json={
            "todo": {
                "status": "closed"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/todo/{todo.id}"), 200, "todo", {
            "name": "test",
            "status": "closed"
        })

    def test_delete(self):

        todo = self.sample.todo("unit", "test")

        self.assertStatusValue(self.api.delete(f"/todo/{todo.id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/todo"), 200, "areas", [])

class TestToDoA(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_patch(self):

        todo = self.sample.todo("unit", "hey", data={
            "text": "hey"
        })

        # remind

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/remind"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.data["notified"], 7)

        # pause

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/pause"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertTrue(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/pause"), 202, "updated", False)

        # unpause

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unpause"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertFalse(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unpause"), 202, "updated", False)

        # skip

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/skip"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertTrue(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/skip"), 202, "updated", False)

        # unskip

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unskip"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertFalse(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unskip"), 202, "updated", False)

        # complete

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/complete"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.status, "closed")
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/complete"), 202, "updated", False)

        # uncomplete

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/uncomplete"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertEqual(item.status, "opened")
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/uncomplete"), 202, "updated", False)

        # expire

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/expire"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertTrue(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/expire"), 202, "updated", False)

        # unexpire

        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unexpire"), 202, "updated", True)
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.session.commit()
        self.assertFalse(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/todo/{todo.id}/unexpire"), 202, "updated", False)

class TestRoutine(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    def test_validate(self, mock_request):

        mock_request.session = self.session

        template = self.sample.template("test", "routine", {"a": 1})

        fields = service.RoutineCL.fields()

        self.assertFalse(service.Routine.validate(fields))

        self.assertFields(fields, [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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
        ])

        self.assertEqual(fields.errors, [])

        fields = service.RoutineCL.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Routine.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

        fields = service.RoutineRUD.fields()

        self.assertFalse(service.Routine.validate(fields))

        self.assertFields(fields, [
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
                    1: "unit",
                    2: "test"
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
                "name": "name",
                "errors": ["missing value"]
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
                "name": "yaml",
                "style": "textarea",
                "optional": True
            }
        ])

        self.assertEqual(fields.errors, [])

        fields = service.RoutineRUD.fields(values={"yaml": "a:1"})

        self.assertFalse(service.Routine.validate(fields))

        self.assertEqual(fields["yaml"].errors, ["must be dict"])

    @unittest.mock.patch("flask.request")
    def test_retrieve(self, mock_request):

        mock_request.session = self.session

        routine = self.sample.routine("test", "unit")

        self.assertEqual(service.Routine.retrieve(routine.id).name, "unit")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_build(self, mock_request):

        mock_request.session = self.session

        # basic

        self.assertEqual(service.Routine.build(**{
            "template_id": 0,
            "data": {
                "by": "data",
                "person_id": 1,
                "name": "hey",
                "status": "opened",
                "created": 1,
                "updated": 2
            }
        }), {
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

        self.assertEqual(service.Routine.build(**{
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template = self.sample.template("unit", "routine", data={
            "by": "template_id",
            "status": "closed",
            "person": "unit"
        })

        self.assertEqual(service.Routine.build(**{
            "name": "hey",
            "template_id": template.id
        }), {
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

        self.assertEqual(service.Routine.build(**{
            "name": "hey",
            "template": "unit"
        }), {
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_tasks(self, mock_request):

        mock_request.session = self.session

        todo = self.sample.todo("unit")
        self.sample.todo("unit", status="closed")
        self.sample.todo("test")

        # explicit

        self.assertEqual(service.Routine.tasks(service.Routine.build(**{
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
        })), {
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

        # template by data, person by name

        self.assertEqual(service.Routine.build(**{
            "template": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            },
            "person": "unit"
        }), {
            "name": "hey",
            "person_id": 1,
            "data": {
                "by": "template",
                "name": "hey",
                "person": "nope"
            }
        })

        # template by id, person by name in template

        template = self.sample.template("unit", "routine", data={
            "by": "template_id",
            "status": "closed",
            "person": "unit"
        })

        self.assertEqual(service.Routine.build(**{
            "name": "hey",
            "template_id": template.id
        }), {
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

        self.assertEqual(service.Routine.build(**{
            "name": "hey",
            "template": "unit"
        }), {
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
    def test_notify(self, mock_notify):

        model = self.sample.routine("unit", "test")

        service.Routine.notify("test", model)

        self.assertEqual(model.updated, 7)
        self.assertEqual(model.data["notified"], 7)

        mock_notify.assert_called_once_with({
            "kind": "routine",
            "action": "test",
            "routine": service.Routine.response(model),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
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
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

        service.Routine.check(routine)

        mock_notify.assert_called_once_with({
            "kind": "task",
            "action": "start",
            "task": routine.data["tasks"][0],
            "routine": service.Routine.response(routine),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

        routine.data["tasks"][0]["end"] = 0

        service.Routine.check(routine)

        self.assertEqual(routine.data["tasks"][0]["start"], 7)

        mock_notify.assert_called_with({
            "kind": "task",
            "action": "pause",
            "task": routine.data["tasks"][1],
            "routine": service.Routine.response(routine),
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
        })

        routine.data["tasks"][1]["end"] = 0

        service.Routine.check(routine)

        self.assertEqual(routine.status, "closed")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify", unittest.mock.MagicMock)
    def test_create(self, mock_request):

        mock_request.session = self.session

        routine = service.Routine.create(**{
            "person_id": 1,
            "name": "unit",
            "status": "opened",
            "created": 6,
            "data": {
                "text": "hey",
                "tasks": [{}]
            }
        })

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

        item = self.session.query(mysql.Routine).get(routine.id)
        flask.request.session.commit()
        self.assertEqual(item.name, "unit")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify", unittest.mock.MagicMock)
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

class TestRoutineCL(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("service.open", create=True)
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_klotio_open, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_routine.fields.yaml":
                return ["/opt/service/config/integration_unit.test_routine.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_klotio_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value,
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        template = self.sample.template("test", "routine", {"a": 1})

        self.assertEqual(service.RoutineCL.fields().to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
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

        mock_klotio_open.assert_called_once_with("/opt/service/config/integration_unit.test_routine.fields.yaml", "r")

        self.assertEqual(service.RoutineCL.fields({"template_id": template.id}).to_list(), [
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
                "options": [template.id],
                "labels": {template.id: "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_routine.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        template = self.sample.template("test", "routine", {"a": 1})

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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
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
            "template_id": template.id
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
                "options": [template.id],
                "labels": {str(template.id): "test"},
                "style": "select",
                "trigger": True,
                "optional": True,
                "value": template.id
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

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
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

        self.assertStatusModels(self.api.get("/routine?since=0&status=opened"), 200, "routines", [
            {
                "name": "test"
            }
        ])

class TestRoutineRUD(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("glob.glob")
    @unittest.mock.patch("klotio.service.open", create=True)
    @unittest.mock.patch("flask.request")
    def test_fields(self, mock_request, mock_open, mock_glob):

        def glob(pattern):

            if pattern == "/opt/service/config/integration_*_routine.fields.yaml":
                return ["/opt/service/config/integration_unit.test_routine.fields.yaml"]

            return []

        mock_glob.side_effect = glob

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data=yaml.safe_dump({"description": "integrate"})).return_value
        ]

        mock_request.session = self.session

        self.assertEqual(service.RoutineRUD.fields().to_list(), [
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

        mock_open.assert_called_once_with("/opt/service/config/integration_unit.test_routine.fields.yaml", "r")

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    def test_options(self):

        routine = self.sample.routine("unit", "test", status="opened", data={"text": 1})

        response = self.api.options(f"/routine/{routine.id}")

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": routine.id,
                "original": routine.id
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

        response = self.api.options(f"/routine/{routine.id}", json={"routine": {
            "nope": "bad"
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": routine.id,
                "original": routine.id
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

        response = self.api.options(f"/routine/{routine.id}", json={"routine": {
            "person_id": 2,
            "name": "yup",
            "status": "closed",
            "yaml": 'text: 2'
        }})

        self.assertStatusFields(response, 200, [
            {
                "name": "id",
                "readonly": True,
                "value": routine.id,
                "original": routine.id
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

    def test_patch(self):

        routine = self.sample.routine("test", "unit")

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}", json={
            "routine": {
                "status": "closed"
            }
        }), 202, "updated", 1)

        self.assertStatusModel(self.api.get(f"/routine/{routine.id}"), 200, "routine", {
            "status": "closed"
        })

    def test_delete(self):

        routine = self.sample.routine("test", "unit")

        self.assertStatusValue(self.api.delete(f"/routine/{routine.id}"), 202, "deleted", 1)

        self.assertStatusModels(self.api.get("/routine"), 200, "routines", [])

class TestRoutineA(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
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
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.data["notified"], 7)

        # next

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/next"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.data["tasks"][0]["end"], 7)

        # pause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/pause"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/pause"), 202, "updated", False)

        # unpause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unpause"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unpause"), 202, "updated", False)

        # skip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/skip"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/skip"), 202, "updated", False)

        # unskip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unskip"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unskip"), 202, "updated", False)

        # complete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/complete"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "closed")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/complete"), 202, "updated", False)

        # uncomplete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/uncomplete"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "opened")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/uncomplete"), 202, "updated", False)

        # expire

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/expire"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/expire"), 202, "updated", False)

        # unexpire

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unexpire"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["expired"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/unexpire"), 202, "updated", False)


class TestTask(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("klotio.service.notify")
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
            "person": nandyio.unittest.people.MockPerson.model(name="unit")
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


    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    @unittest.mock.patch("service.Routine.notify")
    @unittest.mock.patch("service.ToDo.notify", unittest.mock.MagicMock())
    def test_complete(self, mock_routine_notify, mock_task_notify, mock_request):

        mock_request.session = self.session

        todo = self.sample.todo("unit")

        routine = self.sample.routine("unit", "hey", data={
            "text": "hey",
            "language": "cursing",
            "tasks": [{
                "text": "do it",
                "todo": todo.id
            }]
        })

        self.assertTrue(service.Task.complete(routine.data["tasks"][0], routine))
        self.assertTrue(routine.data["tasks"][0]["end"], 7)
        self.assertEqual(routine.status, "closed")
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.assertEqual(item.status, "closed")
        mock_task_notify.assert_called_once_with("complete", routine.data["tasks"][0], routine)
        mock_routine_notify.assert_called_once_with("complete", routine)

        self.assertFalse(service.Task.complete(routine.data["tasks"][0], routine))
        mock_task_notify.assert_called_once()
        mock_routine_notify.assert_called_once()

    @unittest.mock.patch("flask.request")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    @unittest.mock.patch("service.Task.notify")
    @unittest.mock.patch("service.Routine.notify")
    @unittest.mock.patch("service.ToDo.notify", unittest.mock.MagicMock())
    def test_uncomplete(self, mock_routine_notify, mock_task_notify, mock_request):

        mock_request.session = self.session

        todo = self.sample.todo("unit", status="closed", data={"end": 0})

        routine = self.sample.routine("unit", "hey", status="closed", data={
            "text": "hey",
            "language": "cursing",
            "end": 0,
            "tasks": [{
                "text": "do it",
                "end": 0,
                "todo": todo.id
            }]
        })

        self.assertTrue(service.Task.uncomplete(routine.data["tasks"][0], routine))
        self.assertNotIn("end", routine.data["tasks"][0])
        self.assertEqual(routine.status, "opened")
        item = self.session.query(mysql.ToDo).get(todo.id)
        self.assertEqual(item.status, "opened")
        mock_task_notify.assert_called_once_with("uncomplete", routine.data["tasks"][0], routine)
        mock_routine_notify.assert_called_once_with("uncomplete", routine)

        self.assertFalse(service.Task.uncomplete(routine.data["tasks"][0], routine))
        mock_task_notify.assert_called_once()
        mock_routine_notify.assert_called_once()

class TestTaskA(TestRest):

    @unittest.mock.patch("nandyio.people.Person", nandyio.unittest.people.MockPerson)
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
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.data["tasks"][0]["notified"], 7)

        # pause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/pause"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["tasks"][0]["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/pause"), 202, "updated", False)

        # unpause

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unpause"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["tasks"][0]["paused"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unpause"), 202, "updated", False)

        # skip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/skip"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertTrue(item.data["tasks"][0]["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/skip"), 202, "updated", False)

        # unskip

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unskip"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertFalse(item.data["tasks"][0]["skipped"])
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/unskip"), 202, "updated", False)

        # complete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/complete"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "closed")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/complete"), 202, "updated", False)

        # uncomplete

        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/uncomplete"), 202, "updated", True)
        item = self.session.query(mysql.Routine).get(routine.id)
        self.session.commit()
        self.assertEqual(item.status, "opened")
        self.assertStatusValue(self.api.patch(f"/routine/{routine.id}/task/0/uncomplete"), 202, "updated", False)
