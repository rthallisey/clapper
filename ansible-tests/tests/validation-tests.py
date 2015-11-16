import json
import mock
import time
import unittest

import validation_api
import validations


def json_response(response, code=200):
    assert response.status_code == code
    return json.loads(response.data)


def passing_validation(*args):
    return { 'hostname': { 'success': True } }


def failing_validation(*args):
    return { 'hostname': { 'success': False } }


def running_validation(*args):
    time.sleep(0.1)
    return {}


class ValidationsTestCase(unittest.TestCase):

    def setUp(self):
        validation_api.app.config['TESTING'] = True
        self.app = validation_api.app.test_client()
        validation_api.prepare_database()

    def tearDown(self):
        # Ensure we run tests in isolation
        validation_api.DB_VALIDATIONS = validation_api.DB['validations']

    def test_root(self):
        rv = self.app.get('/')
        self.assertIn('Print the API routes.', rv.data)

    def test_list_validations(self):
        rv = self.app.get('/v1/validations/')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(len(json_response(rv)), 3)

    def test_list_validations_content(self):
        rv = self.app.get('/v1/validations/')
        json = json_response(rv)[0]
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'name': 'Basic connectivity',
                'description': 'A simple ping test',
            }, json)

    def test_list_validations_missing_metadata(self):
        rv = self.app.get('/v1/validations/')
        json = json_response(rv)[2]
        self.assertDictContainsSubset(
            {
                'uuid': '2',
                'name': 'Unnamed',
                'description': 'No description',
            }, json)

    def test_get_validation(self):
        rv = self.app.get('/v1/validations/1/')
        self.assertEqual(rv.content_type, 'application/json')
        json_response(rv)

    def test_get_unknown_validation(self):
        rv = self.app.get('/v1/validations/100/')
        self.assertEqual(rv.content_type, 'application/json')
        json_response(rv, 404)

    def test_get_new_validation_content(self):
        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'new',
                'latest_result': None,
                'results': [],
            }, json_response(rv))

    def test_validation_run(self):
        validations.run = mock.Mock(side_effect=passing_validation)
        rv = self.app.put('/v1/validations/1/run')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 204)
        time.sleep(0.01)  # XXX this is really ugly
        self.assertEqual(validations.run.call_count, 1)

    def test_run_unknown_validation(self):
        rv = self.app.put('/v1/validations/100/run')
        self.assertEqual(rv.content_type, 'application/json')
        json_response(rv, 404)

    def test_get_running_validation_content(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        time.sleep(0.01)
        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'running',
            }, json_response(rv))

    def test_get_successful_validation_content(self):
        validations.run = mock.Mock(side_effect=passing_validation)
        self.app.put('/v1/validations/1/run')
        time.sleep(0.01)
        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'success',
            }, json_response(rv))

    def test_get_failed_validation_content(self):
        validations.run = mock.Mock(side_effect=failing_validation)
        self.app.put('/v1/validations/1/run')
        time.sleep(0.01)
        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'failed',
            }, json_response(rv))

    def test_validation_stop_running(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        time.sleep(0.01)
        rv = self.app.put('/v1/validations/1/stop')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 204)
        time.sleep(0.01)
        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'canceled',
            }, json_response(rv))

    def test_validation_stop_non_running(self):
        rv = self.app.put('/v1/validations/1/stop')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

    def test_validation_stop_unknown(self):
        rv = self.app.put('/v1/validations/100/stop')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

if __name__ == '__main__':
    unittest.main()
