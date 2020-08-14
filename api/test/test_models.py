import unittest
import unittest.mock
import nandyio_people_unittest

import os
import time
import json
import pymysql

import sqlalchemy
import sqlalchemy.ext.mutable
import sqlalchemy_jsonfield

import models


class Sample:

    def __init__(self, session):

        self.session = session

    def template(self, name, kind, data=None):

        template = models.Template(name=name, kind=kind, data=data)
        self.session.add(template)
        self.session.commit()

        return template

    def area(self, person, name, status=None, created=7, updated=8, data=None):

        area = models.Area(
            person_id=nandyio_people_unittest.MockPerson.model(name=person)["id"],
            name=name,
            status=status,
            created=created,
            updated=updated,
            data=data
        )
        self.session.add(area)
        self.session.commit()

        return area

    def act(self, person, name="Unit", status=None, created=7, updated=8, data=None):

        act = models.Act(
            person_id=nandyio_people_unittest.MockPerson.model(name=person)["id"],
            name=name,
            status=status,
            created=created,
            updated=updated,
            data=data
        )
        self.session.add(act)
        self.session.commit()

        return act

    def todo(self, person, name="Unit", status=None, created=7, updated=8, data=None):

        if data is None:
            data = {}

        base = {
            "text": "todo it"
        }

        base.update(data)

        todo = models.ToDo(
            person_id=nandyio_people_unittest.MockPerson.model(name=person)["id"],
            name=name,
            status=status,
            created=created,
            updated=updated,
            data=base
        )

        self.session.add(todo)
        self.session.commit()

        return todo

    def routine(self, person, name="Unit", status=None, created=7, updated=8, data=None, tasks=None):

        if data is None:
            data = {}

        base = {
            "text": "routine it"
        }

        base.update(data)

        if tasks is not None:
            base["tasks"] = tasks

        routine = models.Routine(
            person_id=nandyio_people_unittest.MockPerson.model(name=person)["id"],
            name=name,
            status=status,
            created=created,
            updated=updated,
            data=base
        )

        self.session.add(routine)
        self.session.commit()

        return routine


class TestMySQL(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.mysql = models.MySQL()
        self.session = self.mysql.session()
        self.mysql.drop_database()
        self.mysql.create_database()
        self.mysql.Base.metadata.create_all(self.mysql.engine)

    def tearDown(self):

        self.session.close()
        self.mysql.drop_database()

    def test_Template(self):

        self.session.add(models.Template(
            name='Unit Test',
            kind="routine",
            data={"a": 1}
        ))
        self.session.commit()

        template = self.session.query(models.Template).one()
        self.assertEqual(str(template), "<Template(name='Unit Test',kind='routine')>")
        self.assertEqual(template.name, "Unit Test")
        self.assertEqual(template.kind, "routine")
        self.assertEqual(template.data, {"a": 1})

        template.data["a"] = 2
        self.session.commit()
        template = self.session.query(models.Template).one()
        self.assertEqual(template.data, {"a": 2})

    @unittest.mock.patch("models.time.time", unittest.mock.MagicMock(return_value=7))
    def test_Area(self):

        self.session.add(models.Area(
            person_id=1,
            name='Unit Test',
            data={"a": 1}
        ))
        self.session.commit()

        area = self.session.query(models.Area).one()
        self.assertEqual(str(area), "<Area(name='Unit Test')>")
        self.assertEqual(area.person_id, 1)
        self.assertEqual(area.name, "Unit Test")
        self.assertEqual(area.status, "positive")
        self.assertEqual(area.created, 7)
        self.assertEqual(area.updated, 7)
        self.assertEqual(area.data, {"a": 1})

        area.data["a"] = 2
        self.session.commit()
        area = self.session.query(models.Area).one()
        self.assertEqual(area.data, {"a": 2})

    @unittest.mock.patch("models.time.time", unittest.mock.MagicMock(return_value=7))
    def test_Act(self):

        self.session.add(models.Act(
            person_id=1,
            name='Unit Test',
            data={"a": 1}
        ))
        self.session.commit()

        act = self.session.query(models.Act).one()
        self.assertEqual(str(act), "<Act(name='Unit Test',person_id=1,created=7)>")
        self.assertEqual(act.person_id, 1)
        self.assertEqual(act.name, "Unit Test")
        self.assertEqual(act.status, "positive")
        self.assertEqual(act.created, 7)
        self.assertEqual(act.updated, 7)
        self.assertEqual(act.data, {"a": 1})

        act.data["a"] = 2
        self.session.commit()
        act = self.session.query(models.Act).one()
        self.assertEqual(act.data, {"a": 2})

    @unittest.mock.patch("models.time.time", unittest.mock.MagicMock(return_value=7))
    def test_Todo(self):

        self.session.add(models.ToDo(
            person_id=1,
            name='Unit Test',
            data={"a": 1}
        ))
        self.session.commit()

        todo = self.session.query(models.ToDo).one()
        self.assertEqual(str(todo), "<ToDo(name='Unit Test',person_id=1,created=7)>")
        self.assertEqual(todo.person_id, 1)
        self.assertEqual(todo.name, "Unit Test")
        self.assertEqual(todo.status, "opened")
        self.assertEqual(todo.created, 7)
        self.assertEqual(todo.updated, 7)
        self.assertEqual(todo.data, {"a": 1})

        todo.data["a"] = 2
        self.session.commit()
        todo = self.session.query(models.ToDo).one()
        self.assertEqual(todo.data, {"a": 2})

    @unittest.mock.patch("models.time.time", unittest.mock.MagicMock(return_value=7))
    def test_Routine(self):

        self.session.add(models.Routine(
            person_id=1,
            name='Unit Test',
            data={"a": 1}
        ))
        self.session.commit()

        routine = self.session.query(models.Routine).one()
        self.assertEqual(str(routine), "<Routine(name='Unit Test',person_id=1,created=7)>")
        self.assertEqual(routine.person_id, 1)
        self.assertEqual(routine.name, "Unit Test")
        self.assertEqual(routine.status, "opened")
        self.assertEqual(routine.created, 7)
        self.assertEqual(routine.updated, 7)
        self.assertEqual(routine.data, {"a": 1})

        routine.data["a"] = 2
        self.session.commit()
        routine = self.session.query(models.Routine).one()
        self.assertEqual(routine.data, {"a": 2})
