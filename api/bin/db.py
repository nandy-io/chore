#!/usr/bin/env python

import mysql

mysql.MySQL.create_database()
mysql.MySQL.Base.metadata.create_all(mysql.MySQL().engine)
