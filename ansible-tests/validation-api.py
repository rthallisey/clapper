#!/usr/bin/env python

import datetime
import threading
import uuid

from flask import Flask, abort, json, make_response, url_for, redirect, request
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
    all_stages = validations.get_all_stages().values()
    for validation in all_validations:
        validation['results'] = {}
        validation['current_thread'] = None
        DB_VALIDATIONS[validation['uuid']] = validation
    for stage in all_stages:
        included_validations = {}
        for loaded_validation in stage['validations']:
            validation_id = loaded_validation['uuid']
            # XXX(mandre) we want a reference and not a copy
            included_validations[validation_id] = DB_VALIDATIONS[validation_id]
        stage['validations'] = included_validations
        DB['types'][stage['uuid']] = stage


def thread_run_validation(validation, validation_url, cancel_event, arguments):
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
        'arguments': arguments,
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
    return redirect(url_for('v1_index'))


@app.route('/v1/')
def v1_index():
    return json_response(200, [
        url_for('list_validations'),
        url_for('show_validation', validation_id='ID'),
        url_for('run_validation', validation_id='ID'),
        url_for('stop_validation', validation_id='ID'),
        url_for('list_stages'),
        url_for('show_stage', stage_id='ID'),
        url_for('run_stage', stage_id='ID'),
        url_for('list_results'),
        url_for('show_result', result_id='ID'),
    ])


@app.route('/v1/validations/')
def list_validations():
    global DB_VALIDATIONS
    result = [formatted_validation(validation)
              for validation in DB_VALIDATIONS.values()]
    return json_response(200, result)


@app.route('/v1/validations/<validation_id>/')
def show_validation(validation_id):
    global DB_VALIDATIONS
    try:
        validation = DB_VALIDATIONS[validation_id]
    except KeyError:
        return json_response(404, {})
    return json_response(200, formatted_validation(validation))


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

    validation_url = url_for('show_validation', validation_id=validation_id)
    cancel_event = threading.Event()
    validation_arguments = {
        'plan_id': request.args.get('plan_id'),
    }
    thread = threading.Thread(
        target=thread_run_validation,
        args=(validation, validation_url, cancel_event, validation_arguments))
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


def validation_status(validation):
    sorted_results = sorted(validation['results'].values(), key=lambda r: r['date'])
    if sorted_results:
        return sorted_results[-1].get('status', 'new')
    else:
        return 'new'


def aggregate_status(stage):
    all_statuses = [validation_status(k) for k in stage['validations'].values()]
    if all(status == 'new' for status in all_statuses):
        return 'new'
    elif all(status == 'success' for status in all_statuses):
        return 'success'
    elif any(status == 'canceled' for status in all_statuses):
        return 'canceled'
    elif any(status == 'failed' for status in all_statuses):
        return 'failed'
    elif any(status == 'running' for status in all_statuses):
        return 'running'
    else:
        # Should never happen
        return 'unknown'

def formatted_validation(validation):
    results = validation['results']
    sorted_results = sorted(results.values(), key=lambda r: r['date'])
    if sorted_results:
        latest_result = sorted_results[-1]
    else:
        latest_result = None
    return {
        'uuid': validation['uuid'],
        'name': validation['name'],
        'description': validation['description'],
        'ref': url_for('show_validation', validation_id=validation['uuid']),
        'status': validation_status(validation),
        'latest_result': latest_result,
        'results': [url_for('show_result', result_id=r['uuid'])
                    for r in sorted_results],
    }

def formatted_stage(stage):
    formatted_validations = [formatted_validation(validation)
                             for validation in stage['validations'].values()]
    return {
        'uuid': stage['uuid'],
        'ref': url_for('show_stage', stage_id=stage['uuid']),
        'name': stage['name'],
        'description': stage['description'],
        'stage': stage['stage'],
        'status': aggregate_status(stage),
        'validations': formatted_validations,
    }


@app.route('/v1/stages/')
def list_stages():
    global DB
    stages = DB['types'].values()
    result = []
    for stage in stages:
        result.append(formatted_stage(stage))
    return json_response(200, result)


@app.route('/v1/stages/<stage_id>/')
def show_stage(stage_id):
    global DB
    try:
        stage = DB['types'][stage_id]
    except KeyError:
        return json_response(404, {})
    return json_response(200, formatted_stage(stage))


@app.route('/v1/stages/<stage_id>/run', methods=['PUT'])
def run_stage(stage_id):
    global DB
    try:
        stage = DB['types'][stage_id]
    except KeyError:
        return json_response(404, {})
    for validation in stage['validations'].values():
        validation_url = url_for('show_validation', validation_id=validation['uuid'])
        validation_arguments = {
            'plan_id': request.args.get('plan_id'),
        }
        thread = threading.Thread(
            target=thread_run_validation,
            args=(validation, validation_url, None, validation_arguments))
        thread.start()
    return json_response(204, {})


@app.route('/v1/results/')
def list_results():
    global DB_VALIDATIONS
    all_results = []
    for validation in DB_VALIDATIONS.values():
        all_results.extend(validation['results'].values())
    all_results.sort(key=lambda x: x['date'])
    return json_response(200, all_results)


@app.route('/v1/results/<result_id>/')
def show_result(result_id):
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
