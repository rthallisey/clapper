#!/usr/bin/env python

from flask import Flask, jsonify


app = Flask(__name__)


@app.route('/')
def index():
    return jsonify({"msg": "Hello World!"})


@app.route('/v1/validations/')
def list_validations():
    return jsonify({"TODO": "List existing validations"})


@app.route('/v1/validations/<uuid>/')
def show_validation(uuid):
    return jsonify({
        'uuid': uuid,
        'TODO': "return validation info",
    })


@app.route('/v1/validations/<uuid>/run', methods=['PUT'])
def run_validation(uuid):
    return jsonify({
        'TODO': "run the given validation",
    })


app.run(debug=True)
