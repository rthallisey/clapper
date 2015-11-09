#!/usr/bin/env python

import datetime
import threading
import uuid

from flask import Flask, abort, json, make_response, url_for, request

import validations


DB_VALIDATIONS = {}  # TODO: OMG THREAD SAFETY


app = Flask(__name__)


def thread_run_validation(validation_id, validation_url):
    global DB_VALIDATIONS
    validation = validations.get_all()[validation_id]
    db_validation = DB_VALIDATIONS.setdefault(validation_id, {})
    db_results = db_validation.setdefault('results', {})
    db_validation['status'] = 'running'

    result_id = str(uuid.uuid4())
    # TODO: proper formatting
    result_start_time = datetime.datetime.utcnow().isoformat() + 'Z'
    new_result = {
        'uuid': result_id,
        'date': result_start_time,
        'validation': validation_url,
        'status': 'running',
    }
    db_results['uuid'] = new_result

    validation_run_result = validations.run(validation)

    db_results['uuid']['detailed_description'] = validation_run_result
    success = all((result.get('success') for result in validation_run_result.values()))
    if success:
        db_results['uuid']['status'] = 'success'
    else:
        db_results['uuid']['status'] = 'failed'


def json_response(code, result):
    # NOTE: flask.jsonify doesn't handle lists, so we need to do it manually:
    response = make_response(json.dumps(result), code)
    response.headers['Content-Type'] = 'application/json'
    response.code = code
    return response


@app.route('/')
def index():
    return json_response(200, {"TODO": "Print the API routes."})


@app.route('/v1/validations/')
def list_validations():
    result = [{
        'uuid': validation['uuid'],
        'ref': url_for('show_validation', uuid=validation['uuid']),
        'name': validation['name'],
    }
    for validation in validations.get_all().values()]
    return json_response(200, result)


@app.route('/v1/validations/<uuid>/')
def show_validation(uuid):
    global DB_VALIDATIONS
    try:
        validation = validations.get_all()[uuid]
        db_validation = DB_VALIDATIONS.get(uuid, {})
        db_results = db_validation.get('results', {});

        results = sorted(db_results.values(), key=lambda r: r['date'])
        if results:
            latest_result = results[-1]
            validation_status = latest_result.get('status', 'new')
        else:
            validation_status = 'new'
        return json_response(200, {
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=uuid),
            'status': validation_status,
            'results': db_results.values(),
        })
    except KeyError:
        return json_response(404, {})


@app.route('/v1/validations/<uuid>/run', methods=['PUT'])
def run_validation(uuid):
    try:
        validation = threading.Thread(
            target=thread_run_validation,
            args=(uuid, url_for('show_validation', uuid=uuid)))
        validation.start()
        return json_response(204, {})
    except KeyError:
        return json_response(404, {})


app.run(debug=True)
