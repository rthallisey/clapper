#!/usr/bin/env python

import datetime
import threading
import uuid

from flask import Flask, abort, json, make_response, url_for, request
from flask.ext.cors import CORS

import validations


DB = {
    'validations': {},
    'types': {},
}
DB_VALIDATIONS = DB['validations']  # TODO: OMG THREAD SAFETY


app = Flask(__name__)
CORS(app)


def thread_run_validation(validation, cancel_event):
    global DB_VALIDATIONS
    db_validation = DB_VALIDATIONS[validation['uuid']]
    db_results = db_validation.setdefault('results', {})

    result_id = str(uuid.uuid4())
    # TODO: proper formatting
    result_start_time = datetime.datetime.utcnow().isoformat() + 'Z'
    new_result = {
        'uuid': result_id,
        'date': result_start_time,
        'validation': validation['ref'],
        'status': 'running',
    }
    db_results[result_id] = new_result

    validation_run_result = validations.run(validation, cancel_event)

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


@app.route('/v1/validations/<validation_id>/run', methods=['PUT'])
def run_validation(validation_id):
    try:
        validation = validations.get_all_validations()[validation_id]
        validation['ref'] = url_for('show_validation', uuid=validation_id)
    except KeyError:
        return json_response(404, {'error': "validation not found"})

    global DB_VALIDATIONS
    db_validation = DB_VALIDATIONS.setdefault(validation_id, {})
    previous_thread = db_validation.get('current_thread', None)
    if previous_thread and previous_thread.is_alive():
        return json_response(400, {'error': "validation already running"})

    cancel_event = threading.Event()
    thread = threading.Thread(
        target=thread_run_validation,
        args=(validation, cancel_event))
    thread.cancel_event = cancel_event
    db_validation['current_thread'] = thread
    thread.start()
    return json_response(204, {})


@app.route('/v1/validations/<validation_id>/stop', methods=['PUT'])
def stop_validation(validation_id):
    if validation_id not in validations.get_all_validations():
        return json_response(404, {'error': "validation not found"})
    global DB_VALIDATIONS
    db_validation = DB_VALIDATIONS.setdefault(validation_id, {})
    thread = db_validation.get('current_thread', None)
    if thread and thread.is_alive():
        thread.cancel_event.set()
        return json_response(204, {})
    else:
        return json_response(400, {'error': "validation is not running"})


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


@app.route('/v1/validation_types/<type_uuid>/')
def show_validation_type(type_uuid):
    try:
        validation_type = validations.get_all_validation_types()[type_uuid]
    except KeyError:
        return json_response(404, {})
    formatted_validations = [{
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=validation['uuid']),
            'name': validation['name'],
        }
        for validation in validation_type['validations']
    ]
    validation_type['validations'] = formatted_validations
    return json_response(200, validation_type)


@app.route('/v1/validation_types/<type_uuid>/run', methods=['PUT'])
def run_validation_type(type_uuid):
    global DB_VALIDATIONS
    try:
        validation_type = validations.get_all_validation_types()[type_uuid]
    except KeyError:
        return json_response(404, {})
    for validation in validation_type['validations']:
        db_validation = DB_VALIDATIONS.setdefault(validation['uuid'], {})
        validation['ref'] = url_for('show_validation', uuid=validation['uuid'])
        thread = threading.Thread(
            target=thread_run_validation,
            args=(validation, None))
        thread.start()
    return json_response(204, {})


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
            if result['uuid'] == result_id:
                return json_response(200, result)
    return json_response(404, {})


if __name__ == '__main__':
    # Prepare the "database":
    all_validations = validations.get_all_validations().values()
    all_validation_types = validations.get_all_validation_types().values()
    for validation in all_validations:
        validation['results'] = {}
        validation['current_thread'] = None
        DB_VALIDATIONS[validation['uuid']] = validation
    for validation_type in all_validation_types:
        validations = {}
        for loaded_validation in validation_type['validations']:
            validation_id = loaded_validation['uuid']
            validations[validation_id] = DB_VALIDATIONS[validation_id]
        validation_type['validations'] = validations
        DB['types'][validation_type['uuid']] = validation_type

    # Run the API server:
    app.run(debug=True, host='0.0.0.0', port=5001)
