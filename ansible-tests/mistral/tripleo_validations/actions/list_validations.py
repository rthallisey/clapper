import glob
import logging
import os
import yaml

from mistral.actions import base

LOG = logging.getLogger(__name__)

DEFAULT_METADATA = {
    'name': 'Unnamed',
    'description': 'No description',
    'stage': 'No stage',
    'require_plan': True,
}

VALIDATIONS_DIR = '/usr/share/tripleo-validations/validations'


def get_validation_metadata(validation, key):
    try:
        return validation[0]['vars']['metadata'][key]
    except KeyError:
        return DEFAULT_METADATA.get(key)
    except TypeError:
        LOG.exception("Failed to get validation metadata.")


def load_validations():
    '''Loads all validations.'''
    paths = glob.glob('{}/*.yaml'.format(VALIDATIONS_DIR))
    result = {}
    for index, validation_path in enumerate(sorted(paths)):
        with open(validation_path) as f:
            validation = yaml.safe_load(f.read())
            validation_id = os.path.splitext(
                os.path.basename(validation_path))[0]
            result[validation_id] = {
                'name': get_validation_metadata(validation, 'name'),
                'description': get_validation_metadata(validation,
                                                       'description'),
                'require_plan': get_validation_metadata(validation,
                                                        'require_plan'),
                'metadata': get_remaining_metadata(validation)
            }
    return result


def get_remaining_metadata(validation):
    try:
        for (k, v) in validation[0]['vars']['metadata'].items():
            if len(bytes(k)) > 255 or len(bytes(v)) > 255:
                LOG.error("Metadata is too long.")
                return dict()

        return {k: v for k, v in validation[0]['vars']['metadata'].items()
                if k not in ['name', 'description', 'require_plan']}
    except KeyError:
        return dict()


class ListValidations(base.Action):
    def __init__(self):
        pass

    def run(self):
        return load_validations()
