import datetime
import json
import sqlite3

from flask import current_app, g
from uuid import uuid4

from .schemas import DATA_TYPE_SCHEMA


__all__ = [
    "get_db",
    "close_db",
    "init_db",
    "update_db",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource("schema.sql") as sf:
        db.executescript(sf.read().decode("utf-8"))

    db.commit()

    # Dummy values
    c = db.cursor()

    for dt in ("demo1", "demo2"):
        c.execute("INSERT INTO data_types VALUES (?, ?)", (dt, json.dumps(DATA_TYPE_SCHEMA[dt])))
        for _ in range(5):
            new_id = str(uuid4())
            c.execute("INSERT INTO datasets (id, data_type, metadata) VALUES (?, ?, ?)", (new_id, dt, json.dumps({
                "created": datetime.datetime.utcnow().isoformat() + "Z",
                "updated": datetime.datetime.utcnow().isoformat() + "Z"
            })))
            for e in range(20):
                c.execute("INSERT INTO entries (content, dataset) VALUES (?, ?)", ("test content {}".format(e),
                                                                                   new_id))

    db.commit()


def update_db():
    db = get_db()
    c = db.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='datasets'")
    if c.fetchone() is None:
        init_db()
        return

    # TODO
