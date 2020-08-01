#!/usr/bin/env python

import models

models.MySQL.create_database()
models.MySQL.Base.metadata.create_all(models.MySQL().engine)
