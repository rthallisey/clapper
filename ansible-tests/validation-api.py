#!/usr/bin/env python

import datetime
import threading
import uuid

from flask import Flask, abort, json, make_response, url_for, request
from flask.ext.cors import CORS

import validations


DB_VALIDATIONS = {}  # TODO: OMG THREAD SAFETY


app = Flask(__name__)
CORS(app)


def thread_run_validation(validation_id, validation_url):
    global DB_VALIDATIONS
    validation = validations.get_all_validations()[validation_id]
    db_validation = DB_VALIDATIONS.setdefault(validation_id, {})
    db_results = db_validation.setdefault('results', {})

    result_id = str(uuid.uuid4())
    # TODO: proper formatting
    result_start_time = datetime.datetime.utcnow().isoformat() + 'Z'
    new_result = {
        'uuid': result_id,
        'date': result_start_time,
        'validation': validation_url,
        'status': 'running',
    }
    db_results[result_id] = new_result

    validation_run_result = validations.run(validation)

    db_results[result_id]['detailed_description'] = validation_run_result
    success = all((result.get('success') for result in validation_run_result.values()))
    if success:
        db_results[result_id]['status'] = 'success'
    else:
        db_results[result_id]['status'] = 'failed'


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
        'description': validation['description'],
    }
    for validation in validations.get_all_validations().values()]
    return json_response(200, result)


@app.route('/v1/validations/<uuid>/')
def show_validation(uuid):
    global DB_VALIDATIONS
    try:
        validation = validations.get_all_validations()[uuid]
        db_validation = DB_VALIDATIONS.get(uuid, {})
        db_results = db_validation.get('results', {});

        results = sorted(db_results.values(), key=lambda r: r['date'])
        if results:
            latest_result = results[-1]
            validation_status = latest_result.get('status', 'new')
        else:
            validation_status = 'new'
            latest_result = None
        return json_response(200, {
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=uuid),
            'status': validation_status,
            'latest_result': latest_result,
            'results': [url_for('show_validation_result', result_id=r['uuid']) for r in results],
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


@app.route('/v1/validation_types/')
def list_validation_types():
    validation_types = validations.get_all_validation_types().values()
    for validation_type in validation_types:
        formatted_validations = [{
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=validation['uuid']),
            'name': validation['name'],
        }
        for validation in validation_type['validations']]
        validation_type['validations'] = formatted_validations
    return json_response(200, validation_types)


@app.route('/v1/validation_results/')
def list_validation_results():
    global DB_VALIDATIONS
    all_results = []
    for validation in DB_VALIDATIONS.values():
        all_results.extend(validation.get('results', {}).values())
    all_results.sort(key=lambda x: x['date'])
    return json_response(200, all_results)


@app.route('/v1/validation_results/<result_id>/')
def show_validation_result(result_id):
    global DB_VALIDATIONS
    for validation in DB_VALIDATIONS.values():
        for result in validation.get('results', {}).values():
            print repr(result)
            if result['uuid'] == result_id:
                return json_response(200, result)
    return json_response(404, {})


app.run(debug=True, host='0.0.0.0', port=5001)
