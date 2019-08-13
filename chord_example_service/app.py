import chord_example_service
import datetime
import os
import sqlite3

from flask import Flask, g, json, jsonify, request
from uuid import uuid4

DATA_TYPE_SCHEMA = {
    "demo1": {
        "$id": "TODO_1",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "Dummy data type 1",
        "type": "object",
        "required": ["id", "content"],
        "properties": {
            "id": {
                "type": "string",
                "search": {
                    "operations": ["eq", "lt", "le", "gt", "ge", "co"],
                    "canNegate": True,
                    "required": False,
                    "type": "unlimited",  # single / unlimited
                    "order": 0
                }
            },
            "content": {
                "type": "string",
                "search": {
                    "operations": ["eq", "lt", "le", "gt", "ge", "co"],
                    "canNegate": True,
                    "required": False,
                    "type": "unlimited",  # single / unlimited
                    "order": 1
                }
            }
        }
    },
    "demo2": {
        "$id": "TODO_2",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "description": "Dummy data type 2",
        "type": "object",
        "required": ["id", "content"],
        "properties": {
            "id": {
                "type": "string",
                "search": {
                    "operations": ["eq", "lt", "le", "gt", "ge", "co"],
                    "canNegate": True,
                    "required": False,
                    "type": "unlimited",  # single / unlimited
                    "order": 0
                }
            },
            "content": {
                "type": "string",
                "search": {
                    "operations": ["eq", "lt", "le", "gt", "ge", "co"],
                    "canNegate": True,
                    "required": False,
                    "type": "unlimited",  # single / unlimited
                    "order": 1
                }
            }
        }
    }
}


application = Flask(__name__)
application.config.from_mapping(
    DATABASE=os.environ.get("DATABASE", "chord_example_service.db")
)


def data_type_404(data_type_id):
    return json.dumps({
        "code": 404,
        "message": "Data type not found",
        "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
        "errors": [{"code": "not_found", "message": f"Data type with ID {data_type_id} was not found"}]
    })


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(application.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with application.open_resource("schema.sql") as sf:
        db.executescript(sf.read().decode("utf-8"))

    db.commit()

    # Dummy values
    c = db.cursor()

    for dt in ("demo1", "demo2"):
        c.execute("INSERT INTO data_types VALUES (?, ?)", (dt, json.dumps(DATA_TYPE_SCHEMA[dt])))
        for _ in range(5):
            new_id = str(uuid4())
            c.execute("INSERT INTO datasets VALUES (?, ?)", (new_id, dt))
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


application.teardown_appcontext(close_db)

with application.app_context():
    if not os.path.exists(os.path.join(os.getcwd(), application.config["DATABASE"])):
        init_db()
    else:
        update_db()


@application.route("/data-types", methods=["GET"])
def data_type_list():
    # Data types are basically stand-ins for schema blocks

    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM data_types")

    dts = c.fetchall()

    return jsonify([{"id": t["id"], "schema": json.loads(t["schema"])} for t in dts])


@application.route("/data-types/<string:data_type_id>", methods=["GET"])
def data_type_detail(data_type_id: str):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM data_types WHERE id = ?", (data_type_id,))

    data_type = c.fetchone()
    if data_type is None:
        return application.response_class(response=data_type_404(data_type_id))

    return jsonify({
        "id": data_type["id"],
        "schema": json.loads(data_type["schema"])
    })


@application.route("/data-types/<string:data_type_id>/schema", methods=["GET"])
def data_type_schema(data_type_id: str):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT schema FROM data_types WHERE id = ?", (data_type_id,))

    data_type = c.fetchone()
    if data_type is None:
        return application.response_class(response=data_type_404(data_type_id))

    return jsonify(json.loads(data_type[0]))


@application.route("/datasets", methods=["GET"])
def dataset_list():
    dt = request.args.get("data-type", default="")

    db = get_db()
    c = db.cursor()
    c.execute("SELECT d.id AS dataset, t.schema AS schema FROM datasets as d, data_types as t "
              "WHERE d.data_type = t.id AND {}".format("d.data_type = ?" if dt != "" else "1"),
              (dt,) if dt != "" else ())

    data_sets = c.fetchall()

    return jsonify([{
        "id": d["dataset"],
        "schema": json.loads(d["schema"])
    } for d in data_sets])


@application.route("/datasets/<uuid:dataset_id>", methods=["GET"])
def dataset_detail(dataset_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT d.id AS id, t.schema AS schema FROM datasets AS d, data_types AS t WHERE d.data_type = t.id "
              "AND d.id = ?", (str(dataset_id),))

    dataset = c.fetchone()
    if dataset is None:
        return application.response_class(
            response=json.dumps({
                "code": 404,
                "message": "Dataset not found",
                "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
                "errors": [{"code": "not_found", "message": f"Dataset with ID {dataset_id} was not found"}]
            })
        )

    c.execute("SELECT * FROM entries WHERE dataset = ?", (str(dataset_id),))

    entries = c.fetchall()

    return jsonify({
        "objects": [{"id": e["id"], "content": e["content"]} for e in entries],
        "schema": json.loads(dataset["schema"])  # TODO
    })


SEARCH_CONDITIONS = ("eq", "lt", "le", "gt", "ge", "co")
SQL_SEARCH_OPERATIONS = {
    "eq": "=",
    "lt": "<",
    "le": "<=",
    "gt": ">",
    "ge": ">=",
    "co": "LIKE"
}


@application.route("/search", methods=["POST"])
def search_endpoint():
    # TODO: NO SPEC FOR THIS YET SO I JUST MADE SOME STUFF UP
    # TODO: PROBABLY VULNERABLE IN SOME WAY

    dt = request.json["dataTypeID"]
    conditions = request.json["conditions"]
    conditions_filtered = [c for c in conditions if c["field"].split(".")[-1] in ("id", "content") and
                           isinstance(c["negated"], bool) and c["operation"] in SEARCH_CONDITIONS]
    query = ("SELECT * FROM datasets AS d WHERE d.data_type = ? AND d.id IN ("
             "SELECT dataset FROM entries WHERE {})".format(
                 " AND ".join(["{}({} {} ?)".format("NOT " if c["negated"] else "",
                                                    c["field"].split(".")[-1],
                                                    SQL_SEARCH_OPERATIONS[c["operation"]])
                               for c in conditions_filtered])))

    db = get_db()
    c = db.cursor()

    c.execute(query, (dt,) + tuple([f"%{c['searchValue']}%" if c["operation"] == "co" else c["searchValue"]
                                    for c in conditions_filtered]))

    return jsonify({"results": [dict(c) for c in c.fetchall()]})


@application.route("/service-info", methods=["GET"])
def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info

    return jsonify({
        "id": "ca.distributedgenomics.chord_example_service",  # TODO: Should be globally unique
        "name": "CHORD Example Service",                       # TODO: Should be globally unique
        "type": "urn:ga4gh:search",                            # TODO
        "description": "Example service for a CHORD application.",
        "organization": "GenAP",
        "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
        "version": chord_example_service.__version__,
        "extension": {}
    })
