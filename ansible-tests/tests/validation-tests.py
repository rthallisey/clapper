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


def wait_for_request_to_be_processed(sleep_time=0.002):
    # Wait for a previous request to be processes
    # This is an ugly hack to deal with concurency issues
    time.sleep(sleep_time)


class ValidationAPITestCase(unittest.TestCase):

    def setUp(self):
        validation_api.app.config['TESTING'] = True
        self.app = validation_api.app.test_client()
        validation_api.prepare_database()

    def tearDown(self):
        # Ensure we run tests in isolation
        validation_api.DB_VALIDATIONS = validation_api.DB['validations']


class ValidationsTestCase(ValidationAPITestCase):

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
        wait_for_request_to_be_processed()
        self.assertEqual(validations.run.call_count, 1)

    def test_run_unknown_validation(self):
        rv = self.app.put('/v1/validations/100/run')
        self.assertEqual(rv.content_type, 'application/json')
        json_response(rv, 404)

    def test_get_running_validation_content(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'running',
            }, json_response(rv))

    def test_get_successful_validation_content(self):
        validations.run = mock.Mock(side_effect=passing_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'success',
            }, json_response(rv))

    def test_get_failed_validation_content(self):
        validations.run = mock.Mock(side_effect=failing_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'failed',
            }, json_response(rv))

    def test_validation_stop_running(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.put('/v1/validations/1/stop')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 204)
        wait_for_request_to_be_processed()

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

    def test_validation_rerun_running(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.put('/v1/validations/1/run')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

        rv = self.app.get('/v1/validations/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'running',
            }, json_response(rv))


class ValidationTypesTestCase(ValidationAPITestCase):

    def test_list_validation_types(self):
        rv = self.app.get('/v1/validation_types/')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(len(json_response(rv)), 3)

    def test_list_validation_types_content(self):
        rv = self.app.get('/v1/validation_types/')
        json = json_response(rv)[0]
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'name': 'First validation type',
                'description': 'The first validation type',
                'stage': 'discovery',
            }, json)
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'ref': '/v1/validations/1/',
                'name': 'Basic connectivity',
            }, json['validations'][0])

    def test_list_validation_typess_missing_metadata(self):
        rv = self.app.get('/v1/validation_types/')
        json = json_response(rv)[1]
        self.assertDictContainsSubset(
            {
                'uuid': '3',
                'name': 'Unnamed',
                'description': 'No description',
                'stage': 'Default stage',
            }, json)

    def test_get_validation_type(self):
        rv = self.app.get('/v1/validation_types/1/')
        self.assertEqual(rv.content_type, 'application/json')
        json_response(rv)

    def test_get_unknown_validation_type(self):
        rv = self.app.get('/v1/validation_types/100/')
        self.assertEqual(rv.content_type, 'application/json')
        json_response(rv, 404)

    def test_get_new_validation_type_content(self):
        rv = self.app.get('/v1/validation_types/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'new',
            }, json_response(rv))

    def test_get_success_validation_type_content(self):
        validations.run = mock.Mock(side_effect=passing_validation)
        self.app.put('/v1/validation_types/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.get('/v1/validation_types/1/')
        self.assertDictContainsSubset(
            {
                'uuid': '1',
                'status': 'success',
            }, json_response(rv))


class ValidationResultsTestCase(ValidationAPITestCase):

    def test_list_validation_results_empty(self):
        rv = self.app.get('/v1/validation_results/')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(len(json_response(rv)), 0)

    def test_list_validation_results(self):
        validations.run = mock.Mock(side_effect=passing_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()

        rv = self.app.get('/v1/validation_results/')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(len(json_response(rv)), 1)

    def test_passing_validation_result(self):
        validations.run = mock.Mock(side_effect=passing_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()
        validation = json_response(self.app.get('/v1/validations/1/'))

        rv = self.app.get(validation['results'][0])
        json = json_response(rv)
        self.assertIn('date', json)
        self.assertDictContainsSubset(
            {
                'status': 'success',
                'validation': '/v1/validations/1/',
                'detailed_description': passing_validation(),
            }, json)

        self.assertEqual(json, validation['latest_result'])

    def test_failed_validation_result(self):
        validations.run = mock.Mock(side_effect=failing_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()
        validation = json_response(self.app.get('/v1/validations/1/'))

        rv = self.app.get(validation['results'][0])
        json = json_response(rv)
        self.assertIn('date', json)
        self.assertDictContainsSubset(
            {
                'status': 'failed',
                'validation': '/v1/validations/1/',
                'detailed_description': failing_validation(),
            }, json)

        self.assertEqual(json, validation['latest_result'])

    def test_running_validation_result(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()
        validation = json_response(self.app.get('/v1/validations/1/'))

        rv = self.app.get(validation['results'][0])
        json = json_response(rv)
        self.assertIn('date', json)
        self.assertDictContainsSubset(
            {
                'status': 'running',
                'validation': '/v1/validations/1/',
            }, json)

        self.assertEqual(json, validation['latest_result'])

    def test_canceled_validation_result(self):
        validations.run = mock.Mock(side_effect=running_validation)
        self.app.put('/v1/validations/1/run')
        wait_for_request_to_be_processed()
        rv = self.app.put('/v1/validations/1/stop')
        wait_for_request_to_be_processed()
        validation = json_response(self.app.get('/v1/validations/1/'))

        rv = self.app.get(validation['results'][0])
        json = json_response(rv)
        self.assertIn('date', json)
        self.assertDictContainsSubset(
            {
                'status': 'canceled',
                'validation': '/v1/validations/1/',
            }, json)

        self.assertEqual(json, validation['latest_result'])

    def test_unknown_validation_result(self):
        rv = self.app.get('/v1/validation_results/100/')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

if __name__ == '__main__':
    unittest.main()
