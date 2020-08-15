#!/usr/bin/env python

import klotio
import nandyio_chore_models

logger = klotio.logger('nandy-io-chore-db')

logger.debug("init", extra={
    "init": {
        "mysql": {
            "database": nandyio_chore_models.MySQL.DATABASE
        }
    }
})

nandyio_chore_models.MySQL.create_database()
nandyio_chore_models.MySQL.Base.metadata.create_all(nandyio_chore_models.MySQL().engine)
