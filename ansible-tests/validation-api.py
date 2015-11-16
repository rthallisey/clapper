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


def prepare_database():
    all_validations = validations.get_all_validations().values()
    all_validation_types = validations.get_all_validation_types().values()
    for validation in all_validations:
        validation['results'] = {}
        validation['current_thread'] = None
        DB_VALIDATIONS[validation['uuid']] = validation
    for validation_type in all_validation_types:
        included_validations = {}
        for loaded_validation in validation_type['validations']:
            validation_id = loaded_validation['uuid']
            included_validations[validation_id] = DB_VALIDATIONS[validation_id]
        validation_type['validations'] = included_validations
        DB['types'][validation_type['uuid']] = validation_type


def thread_run_validation(validation, validation_url, cancel_event):
    global DB_VALIDATIONS
    results = DB_VALIDATIONS[validation['uuid']]['results']

    result_id = str(uuid.uuid4())
    # TODO: proper datetime formatting
    result_start_time = datetime.datetime.utcnow().isoformat() + 'Z'
    new_result = {
        'uuid': result_id,
        'date': result_start_time,
        'validation': validation_url,
        'status': 'running',
    }
    results[result_id] = new_result

    validation_run_result = validations.run(validation, cancel_event)

    results[result_id]['detailed_description'] = validation_run_result
    success = all((result.get('success') for result in validation_run_result.values()))
    if success:
        results[result_id]['status'] = 'success'
    else:
        results[result_id]['status'] = 'failed'


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
    global DB_VALIDATIONS
    result = [{
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=validation['uuid']),
            'name': validation['name'],
            'description': validation['description'],
        }
        for validation in DB_VALIDATIONS.values()]
    return json_response(200, result)


@app.route('/v1/validations/<uuid>/')
def show_validation(uuid):
    global DB_VALIDATIONS
    try:
        validation = DB_VALIDATIONS[uuid]
    except KeyError:
        return json_response(404, {})
    results = validation['results']

    sorted_results = sorted(results.values(), key=lambda r: r['date'])
    if sorted_results:
        latest_result = sorted_results[-1]
        validation_status = latest_result.get('status', 'new')
    else:
        validation_status = 'new'
        latest_result = None
    return json_response(200, {
        'uuid': validation['uuid'],
        'ref': url_for('show_validation', uuid=uuid),
        'status': validation_status,
        'latest_result': latest_result,
        'results': [url_for('show_validation_result', result_id=r['uuid'])
                    for r in sorted_results],
    })


@app.route('/v1/validations/<validation_id>/run', methods=['PUT'])
def run_validation(validation_id):
    global DB_VALIDATIONS
    try:
        validation = DB_VALIDATIONS[validation_id]
    except KeyError:
        return json_response(404, {'error': "validation not found"})

    previous_thread = validation['current_thread']
    if previous_thread and previous_thread.is_alive():
        return json_response(400, {'error': "validation already running"})

    validation_url = url_for('show_validation', uuid=validation_id)
    cancel_event = threading.Event()
    thread = threading.Thread(
        target=thread_run_validation,
        args=(validation, validation_url, cancel_event))
    thread.cancel_event = cancel_event
    validation['current_thread'] = thread
    thread.start()
    return json_response(204, {})


@app.route('/v1/validations/<validation_id>/stop', methods=['PUT'])
def stop_validation(validation_id):
    global DB_VALIDATIONS
    try:
        validation = DB_VALIDATIONS[validation_id]
    except KeyError:
        return json_response(404, {'error': "validation not found"})
    thread = validation['current_thread']
    if thread and thread.is_alive():
        validation['results'].values()[-1]['status'] = 'canceled'
        thread.cancel_event.set()
        return json_response(204, {})
    else:
        return json_response(400, {'error': "validation is not running"})


@app.route('/v1/validation_types/')
def list_validation_types():
    global DB
    validation_types = DB['types'].values()
    result = []
    for validation_type in validation_types:
        formatted_validations = [{
                'uuid': validation['uuid'],
                'ref': url_for('show_validation', uuid=validation['uuid']),
                'name': validation['name'],
            }
            for validation in validation_type['validations'].values()]
        formatted_type = {
            'uuid': validation_type['uuid'],
            'ref': url_for('show_validation_type', type_uuid=validation_type['uuid']),
            'name': validation_type['name'],
            'description': validation_type['description'],
            'validations': formatted_validations,
        }
        result.append(formatted_type)
    return json_response(200, result)


@app.route('/v1/validation_types/<type_uuid>/')
def show_validation_type(type_uuid):
    global DB
    try:
        validation_type = DB['types'][type_uuid]
    except KeyError:
        return json_response(404, {})
    formatted_validations = [{
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=validation['uuid']),
            'name': validation['name'],
        }
        for validation in validation_type['validations'].values()]
    formatted_type = {
        'uuid': validation_type['uuid'],
        'ref': url_for('show_validation_type', type_uuid=validation_type['uuid']),
        'name': validation_type['name'],
        'description': validation_type['description'],
        'validations': formatted_validations,
    }
    return json_response(200, formatted_type)


@app.route('/v1/validation_types/<type_uuid>/run', methods=['PUT'])
def run_validation_type(type_uuid):
    global DB
    try:
        validation_type = DB['types'][type_uuid]
    except KeyError:
        return json_response(404, {})
    for validation in validation_type['validations'].values():
        validation_url = url_for('show_validation', uuid=validation['uuid'])
        thread = threading.Thread(
            target=thread_run_validation,
            args=(validation, validation_url, None))
        thread.start()
    return json_response(204, {})


@app.route('/v1/validation_results/')
def list_validation_results():
    global DB_VALIDATIONS
    all_results = []
    for validation in DB_VALIDATIONS.values():
        all_results.extend(validation['results'].values())
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
    prepare_database()

    # Run the API server:
    app.run(debug=True, host='0.0.0.0', port=5001)
