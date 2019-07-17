import chord_example_service
import datetime
import os
import sqlite3

from flask import Flask, g, json, jsonify, request

DATASET_SCHEMA = {
    "$id": "TODO",
    "$schema": "http://json-schema.org/draft-07/schema#",
    "description": "Dummy dataset",
    "type": "object",
    "required": ["id", "content"],
    "properties": {
        "id": {
            "type": "string"
        },
        "content": {
            "type": "string"
        }
    }
}

application = Flask(__name__)
application.config.from_mapping(
    DATABASE=os.environ.get("DATABASE", "chord_example_service.db")
)


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


def update_db():
    db = get_db()
    c = db.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services'")
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


@application.route("/datasets", methods=["GET"])
def datasets():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT DISTINCT dataset FROM entries")

    dataset_ids = c.fetchall()

    return jsonify([{
        "id": d["dataset"],
        "schema": DATASET_SCHEMA
    } for d in dataset_ids])


@application.route("/datasets/<uuid:dataset_id>", methods=["GET"])
def dataset_by_id(dataset_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM entries WHERE dataset = ?", (str(dataset_id),))

    entries = c.fetchall()
    if len(entries) == 0:
        return application.response_class(
            response=json.dumps({
                "code": 404,
                "message": "Dataset not found",
                "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
                "errors": [{"code": "not_found", "message": f"Dataset with ID {dataset_id} was not found"}]
            })
        )

    return jsonify({
        "objects": [{"id": e["id"], "content": e["content"]} for e in entries],
        "schema": DATASET_SCHEMA
    })


SEARCH_NEGATION = ("pos", "neg")
SEARCH_CONDITIONS = ("eq", "lt", "le", "gt", "ge", "co")
SQL_SEARCH_CONDITIONS = {
    "eq": "=",
    "lt": "<",
    "le": "<=",
    "gt": ">",
    "ge": ">=",
    "co": "LIKE"
}


@application.route("/search", methods=["POST"])
def service_types():
    # TODO: NO SPEC FOR THIS YET SO I JUST MADE SOME STUFF UP
    # TODO: PROBABLY VULNERABLE IN SOME WAY

    conditions = request.json
    conditions_filtered = [c for c in conditions if c["searchField"].split(".")[-1] in ("id", "content") and
                           c["negation"] in SEARCH_NEGATION and c["condition"] in SEARCH_CONDITIONS]
    query = "SELECT * FROM entries WHERE {}".format(" AND ".join(
        ["{}({} {} ?)".format("NOT " if c["negation"] == "neg" else "", c["searchField"].split(".")[-1],
                              SQL_SEARCH_CONDITIONS[c["condition"]])
         for c in conditions_filtered]))

    db = get_db()
    c = db.cursor()

    c.execute(query, tuple([f"%{c['searchValue']}%" if c["condition"] == "co" else c["searchValue"]
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
