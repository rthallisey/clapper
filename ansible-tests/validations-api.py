#!/usr/bin/env python

from flask import Flask, abort, jsonify

import validations


app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({"msg": "Hello World!"})


@app.route('/v1/validations/')
def list_validations():
    result = [{
        'uuid': validation['uuid'],
        'ref': '/v1/validations/' + validation['uuid'],
        'name': validation['name'],
    }
    for validation in validations.get_all().values()]
    return jsonify({'validations': result})


@app.route('/v1/validations/<uuid>/')
def show_validation(uuid):
    try:
        validation = validations.get_all()[uuid]
        return jsonify({
            'uuid': validation['uuid'],
            'ref': '/v1/validations/' + validation['uuid'],
            'name': validation['name'],
            'status': 'new',
            'results': [],
        })
    except KeyError:
        abort(404)


@app.route('/v1/validations/<uuid>/run', methods=['PUT'])
def run_validation(uuid):
    return jsonify({
        'TODO': "run the given validation",
    })


app.run(debug=True)
