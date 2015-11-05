#!/usr/bin/env python

from flask import Flask, abort, json, make_response

import validations


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
        'ref': '/v1/validations/' + validation['uuid'],
        'name': validation['name'],
    }
    for validation in validations.get_all().values()]
    return json_response(200, result)


@app.route('/v1/validations/<uuid>/')
def show_validation(uuid):
    try:
        validation = validations.get_all()[uuid]
        return json_response(200, {
            'uuid': validation['uuid'],
            'ref': '/v1/validations/' + validation['uuid'],
            'name': validation['name'],
            'status': 'new',
            'results': [],
        })
    except KeyError:
        return json_response(404, {})


@app.route('/v1/validations/<uuid>/run', methods=['PUT'])
def run_validation(uuid):
    try:
        validation = validations.get_all()[uuid]
        # TODO: this blocks. Run it in the background
        results = validations.run(validation)
        #return json_response(204, results)
        return json_response(200, results)
    except KeyError:
        return json_response(404, {})


app.run(debug=True)
