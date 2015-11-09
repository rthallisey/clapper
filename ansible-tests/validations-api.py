#!/usr/bin/env python

from flask import Flask, abort, json, make_response, url_for, request

import validations


DB_VALIDATIONS = {}  # TODO: OMG THREAD SAFETY


app = Flask(__name__)


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

        return json_response(200, {
            'uuid': validation['uuid'],
            'ref': url_for('show_validation', uuid=uuid),
            'status': db_validation.get('status', 'new'),
            'results': db_validation.get('results', []),
        })
    except KeyError:
        return json_response(404, {})


@app.route('/v1/validations/<uuid>/run', methods=['PUT'])
def run_validation(uuid):
    global DB_VALIDATIONS
    try:
        validation = validations.get_all()[uuid]
        db_validation = DB_VALIDATIONS.setdefault(uuid, {})
        db_validation['status'] = 'running'
        # TODO: this blocks. Run it in the background
        results = validations.run(validation)
        # TODO: add timestamp to the results
        success = all((result.get('success') for result in results.values()))
        if success:
            db_validation['status'] = 'success'
        else:
            db_validation['status'] = 'failed'
        db_validation.setdefault('results', []).append(results)
        #return json_response(204, results)
        return json_response(200, results)
    except KeyError:
        return json_response(404, {})


app.run(debug=True)
