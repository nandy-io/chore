"""
Module for Chore models
"""

import time

import sqlalchemy
import sqlalchemy.ext.mutable
import sqlalchemy_jsonfield

import klotio_sqlalchemy_models

class MySQL(klotio_sqlalchemy_models.MySQL):
    """
    MySQL Class that hodls teh DB
    """

    DATABASE = "nandy_chore"

def now():
    """
    Mockable function for time
    """
    return time.time()


class Template(MySQL.Base):
    """
    Template model, serves as base data for other models
    """

    __tablename__ = "template"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String(128), nullable=False)
    kind = sqlalchemy.Column(sqlalchemy.Enum("area", "act", "todo", "routine"))
    data = sqlalchemy.Column(
        sqlalchemy.ext.mutable.MutableDict.as_mutable(
            sqlalchemy_jsonfield.JSONField(enforce_string=True, enforce_unicode=False)
        ),
        nullable=False,
        default=dict
    )

    sqlalchemy.schema.UniqueConstraint('name', 'kind', name='label')

    def __repr__(self):
        return "<Template(name='%s',kind='%s')>" % (self.name, self.kind)


class Area(MySQL.Base):
    """
    Area model, a place to keep in order
    """

    __tablename__ = "area"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    status = sqlalchemy.Column(sqlalchemy.Enum("positive", "negative"), default="positive")
    created = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    updated = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    data = sqlalchemy.Column(
        sqlalchemy.ext.mutable.MutableDict.as_mutable(
            sqlalchemy_jsonfield.JSONField(enforce_string=True, enforce_unicode=False)
        ),
        nullable=False,
        default=dict
    )

    sqlalchemy.schema.UniqueConstraint('name', name='label')

    def __repr__(self):
        return "<Area(name='%s')>" % (self.name)


class Act(MySQL.Base):
    """
    Act mode, something done good or bad
    """

    __tablename__ = "act"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String(128), nullable=False)
    status = sqlalchemy.Column(sqlalchemy.Enum("positive", "negative"), default="positive")
    created = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    updated = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    data = sqlalchemy.Column(
        sqlalchemy.ext.mutable.MutableDict.as_mutable(
            sqlalchemy_jsonfield.JSONField(enforce_string=True, enforce_unicode=False)
        ),
        nullable=False,
        default=dict
    )

    sqlalchemy.schema.UniqueConstraint('name', 'person_id', 'created', name='label')

    def __repr__(self):
        return "<Act(name='%s',person_id=%s,created=%s)>" % (self.name, self.person_id, self.created)


class ToDo(MySQL.Base):
    """
    ToDo model, something that needs to get done eventually
    """

    __tablename__ = "todo"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    status = sqlalchemy.Column(sqlalchemy.Enum("opened", "closed"), default="opened")
    created = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    updated = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    data = sqlalchemy.Column(
        sqlalchemy.ext.mutable.MutableDict.as_mutable(
            sqlalchemy_jsonfield.JSONField(enforce_string=True, enforce_unicode=False)
        ),
        nullable=False,
        default=dict
    )

    sqlalchemy.schema.UniqueConstraint('name', 'person_id', 'created', name='label')

    def __repr__(self):
        return "<ToDo(name='%s',person_id=%s,created=%s)>" % (self.name, self.person_id, self.created)


class Routine(MySQL.Base):
    """
    Routine model, a list of task that need to be done now
    """

    __tablename__ = "routine"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    person_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    status = sqlalchemy.Column(sqlalchemy.Enum("opened", "closed"), default="opened")
    created = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    updated = sqlalchemy.Column(sqlalchemy.Integer, default=now)
    data = sqlalchemy.Column(
        sqlalchemy.ext.mutable.MutableDict.as_mutable(
            sqlalchemy_jsonfield.JSONField(enforce_string=True, enforce_unicode=False)
        ),
        nullable=False,
        default=dict
    )

    sqlalchemy.schema.UniqueConstraint('name', 'person_id', 'created', name='label')

    def __repr__(self):
        return "<Routine(name='%s',person_id=%s,created=%s)>" % (self.name, self.person_id, self.created)
