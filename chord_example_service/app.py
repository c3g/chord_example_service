import chord_lib.search
import chord_example_service
import datetime
import os

from flask import Flask, json, jsonify, request

from .db import get_db, init_db, update_db, close_db
from .schemas import TABLE_METADATA_SCHEMA


SERVICE_TYPE = "ca.c3g.chord:example:{}".format(chord_example_service.__version__)
SERVICE_ID = os.environ.get("SERVICE_ID", SERVICE_TYPE)


application = Flask(__name__)
application.config.from_mapping(
    DATABASE=os.environ.get("DATABASE", "chord_example_service.db")
)

application.teardown_appcontext(close_db)

with application.app_context():
    if not os.path.exists(os.path.join(os.getcwd(), application.config["DATABASE"])):
        init_db()
    else:
        update_db()


def data_type_404(data_type_id):
    return jsonify({
        "code": 404,
        "message": "Data type not found",
        "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
        "errors": [{"code": "not_found", "message": f"Data type with ID {data_type_id} was not found"}]
    }), 404


@application.route("/data-types", methods=["GET"])
def data_type_list():
    # Data types are basically stand-ins for schema blocks

    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM data_types")

    dts = c.fetchall()

    return jsonify([{
        "id": t["id"],
        "schema": json.loads(t["schema"]),
        "metadata_schema": TABLE_METADATA_SCHEMA
    } for t in dts])


@application.route("/data-types/<string:data_type_id>", methods=["GET"])
def data_type_detail(data_type_id: str):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM data_types WHERE id = ?", (data_type_id,))

    data_type = c.fetchone()
    if data_type is None:
        return data_type_404(data_type_id)

    return jsonify({
        "id": data_type["id"],
        "schema": json.loads(data_type["schema"]),
        "metadata_schema": TABLE_METADATA_SCHEMA
    })


@application.route("/data-types/<string:data_type_id>/schema", methods=["GET"])
def data_type_schema(data_type_id: str):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT schema FROM data_types WHERE id = ?", (data_type_id,))

    data_type = c.fetchone()
    if data_type is None:
        return data_type_404(data_type_id)

    return jsonify(json.loads(data_type[0]))


@application.route("/data-types/<string:_data_type_id>/metadata_schema", methods=["GET"])
def data_type_metadata_schema(_data_type_id: str):
    return jsonify(TABLE_METADATA_SCHEMA)


@application.route("/datasets", methods=["GET"])
def dataset_list():
    dt = request.args.getlist("data-type")

    # TODO: Support querying multiple data types at once

    db = get_db()
    c = db.cursor()
    c.execute("SELECT d.id AS dataset, d.metadata as metadata, t.schema AS schema FROM datasets as d, data_types as t "
              "WHERE d.data_type = t.id AND {}".format("d.data_type = ?" if dt != "" else "1"),
              (dt[0],) if len(dt) > 0 else ())

    data_sets = c.fetchall()

    return jsonify([{
        "id": d["dataset"],
        "metadata": json.loads(d["metadata"]),
        "schema": json.loads(d["schema"])
    } for d in data_sets])


@application.route("/datasets/<uuid:dataset_id>", methods=["GET"])
def dataset_detail(dataset_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT d.id AS id, d.metadata as metadata, t.schema AS schema FROM datasets AS d, data_types AS t "
              "WHERE d.data_type = t.id AND d.id = ?", (str(dataset_id),))

    dataset = c.fetchone()
    if dataset is None:
        return jsonify({
            "code": 404,
            "message": "Dataset not found",
            "timestamp": datetime.datetime.utcnow().isoformat("T") + "Z",
            "errors": [{"code": "not_found", "message": f"Dataset with ID {dataset_id} was not found"}]
        }), 404

    c.execute("SELECT * FROM entries WHERE dataset = ?", (str(dataset_id),))

    entries = c.fetchall()

    return jsonify({
        "objects": [{"id": e["id"], "content": e["content"]} for e in entries],
        "schema": json.loads(dataset["schema"]),  # TODO
        "metadata": json.loads(dataset["metadata"])
    })


def format_search_fragment(negated, field, operator):
    return "{negated}(e.{field} {operator} ?)".format(
        negated="NOT " if negated else "",
        field=field,
        operator=chord_lib.search.SQL_SEARCH_OPERATORS[operator]
    )


@application.route("/search", methods=["POST"])
def search_endpoint():
    # TODO: NO SPEC FOR THIS YET SO I JUST MADE SOME STUFF UP
    # TODO: PROBABLY VULNERABLE IN SOME WAY

    start = datetime.datetime.now()

    dt = request.json["dataTypeID"]
    conditions = request.json["conditions"]
    conditions_filtered = [c for c in conditions if c["field"].split(".")[-1] in ("id", "content") and
                           isinstance(c["negated"], bool) and c["operation"] in chord_lib.search.SEARCH_OPERATIONS]
    query = ("SELECT * FROM datasets AS d WHERE d.data_type = ? AND d.id IN ("
             "SELECT dataset FROM entries WHERE {})".format(
                 " AND ".join([format_search_fragment(c["negated"], c["field"].split(".")[-1], c["operation"])
                               for c in conditions_filtered])))

    db = get_db()
    c = db.cursor()

    c.execute(query, (dt,) + tuple([f"%{c['searchValue']}%" if c["operation"] == "co" else c["searchValue"]
                                    for c in conditions_filtered]))

    return jsonify(chord_lib.search.build_search_response([dict(c) for c in c.fetchall()], start))


@application.route("/private/search", methods=["POST"])
def private_search_endpoint():
    # TODO: NO SPEC FOR THIS YET SO I JUST MADE SOME STUFF UP
    # TODO: PROBABLY VULNERABLE IN SOME WAY

    start = datetime.datetime.now()

    dt = request.json["dataTypeID"]
    conditions = request.json["conditions"]
    conditions_filtered = [c for c in conditions if c["field"].split(".")[-1] in ("id", "content") and
                           isinstance(c["negated"], bool) and c["operation"] in chord_lib.search.SEARCH_OPERATIONS]

    query = (
        "SELECT d.id as dataset_id, e.id as id, e.content as content FROM datasets AS d, entries AS e "
        "WHERE d.data_type = ? AND d.id = e.dataset AND {}".format(
            " AND ".join([format_search_fragment(c["negated"], "e." + c["field"].split(".")[-1], c["operation"])
                          for c in conditions_filtered])))

    db = get_db()
    db.set_trace_callback(print)
    c = db.cursor()

    c.execute(query, (dt,) + tuple([f"%{c['searchValue']}%" if c["operation"] == "co" else c["searchValue"]
                                    for c in conditions_filtered]))

    results_by_dataset_id = {}
    for entry in c.fetchall():
        # noinspection PyUnresolvedReferences
        results_by_dataset_id[entry[0]] = results_by_dataset_id.get(entry[0], []) + \
            [{"id": entry[1], "content": entry[2]}]

    return jsonify(chord_lib.search.build_search_response(results_by_dataset_id, start))


@application.route("/service-info", methods=["GET"])
def service_info():
    # Spec: https://github.com/ga4gh-discovery/ga4gh-service-info

    return jsonify({
        "id": SERVICE_ID,
        "name": "CHORD Example Service",  # TODO: Should be globally unique?
        "type": SERVICE_TYPE,
        "description": "Example service for a CHORD application.",
        "organization": {
            "name": "C3G",
            "url": "http://www.computationalgenomics.ca"
        },
        "contactUrl": "mailto:david.lougheed@mail.mcgill.ca",
        "version": chord_example_service.__version__
    })
