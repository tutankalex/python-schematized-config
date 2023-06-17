# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['logger', 'load_json', 'coerce_primitive_values', 'extract_declared_items', 'ConfigValidatorException',
           'ConfigValidator']

# %% ../nbs/00_core.ipynb 2
from nbdev.showdoc import *
from fastcore.test import *

import dotenv
import json
import os
import jsonschema
import logging
from jsonschema import validate, ValidationError
from typing import Union


logger = logging.getLogger(__name__)

# %% ../nbs/00_core.ipynb 3
def load_json(json_source: Union[str, dict]=None) -> dict:
    '''
    convenience method to return a dict from either
    a file path or an already-loaded dict
    '''
    if isinstance(json_source, str):
        with open(json_source) as ifile:
            return json.load(ifile)
    elif isinstance(json_source, dict):
        return json_source

# %% ../nbs/00_core.ipynb 4
def coerce_primitive_values(json_schema: dict, data: dict) -> dict:
    '''
    given a JSON schema dict, return a dict where the values that have
    primitive types (`string`, `integer`, `number`, `boolean`) as described
    in the schema are converted to the corresponding types from `str`
    
    :param json_schema: expected (but not validated) to be a json schema
    :param data: the data (e.g. dotenv, os.environ) to extract from
    :return: coerced dict
    '''
    if not isinstance(data, dict):
        return data
    out = data.copy()
    # use the json schema to convert types on known properties
    for property_name, property_schema in json_schema['properties'].items():
        property_type = property_schema.get('type')
        property_value = data.get(property_name)
        if property_value is None:
            continue
        # property_value should be a string at this point
        try:
            if property_type == 'integer':
                out[property_name] = int(data[property_name])
            elif property_type == 'number':
                out[property_name] = float(data[property_name])
            elif property_type == 'boolean':
                parsed_boolean = None
                if property_value.lower() in (
                    'true', 'yes', 'y', '1', 'on',
                ):
                    parsed_boolean = True
                elif property_value.lower() in (
                    'false', 'no', 'n', '0', 'off',
                ):
                    parsed_boolean = False
                out[property_name] = parsed_boolean
        except:
            # leave any validation error descriptions to json schema
            continue
    return out

# %% ../nbs/00_core.ipynb 7
def extract_declared_items(json_schema: dict, data: dict) -> dict:
    '''
    given a JSON schema dict, return a dict where
    - all keys that are not declared in the schema are removed
    - all keys that are declared in the schem are present;
      if a key is declared in the schema with a default,
      BUT NOT present in the original data, it will be added
      using the 'default' value
      
    :param json_schema: expected (but not validated) to be a json schema
    :param data: the data (e.g. dotenv, os.environ) to extract from
    :return: extracted dict
    '''
    properties = json_schema['properties']
    out = {key: value for (key, value) in data.items() if key in properties}
    for required_property, property_schema in properties.items():
        if required_property not in out and 'default' in property_schema:
            out[required_property] = property_schema['default']
    return out

# %% ../nbs/00_core.ipynb 9
class ConfigValidatorException(Exception):
    
    def __init__(self, errors):
        super().__init__('config failed to validate against JSON schema')
        self.errors = errors


class ConfigValidator(object):
    
    CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME = 'CONFIG_VALIDATOR_JSON_SCHEMA'
    
    @classmethod
    def get_default_json_schema(cls):
        if cls.CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME in os.environ:
            expected_json_schema_path = \
                os.environ[cls.CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME]
            with open(expected_json_schema_path) as ifile:
                return json.load(ifile)
        return None

    def __init__(self, json_schema: Union[str, dict]=None):
        '''
        :param json_schema: a str path to a json schema file, or a schema in dict form
        
        if no value is provided, it will fall back to looking for
        an environment variable corresponding to the class variable
        `CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME`
        to find a JSON schema file
        '''
        if isinstance(json_schema, (str, dict)):
            self._json_schema = load_json(json_schema)
        elif (default_schema := self.__class__.get_default_json_schema()):
            self._json_schema = default_schema
        else:
            raise Exception('did not receive or find a JSON schema')

    def load_config(self, config: dict):
        extracted_config = extract_declared_items(self._json_schema, config)
        coerced_config = coerce_primitive_values(self._json_schema, extracted_config)
        validator = jsonschema.Draft4Validator(self._json_schema)
        errors = list(validator.iter_errors(coerced_config))
        if errors:
            for error in errors:
                logger.error(f'{error.json_path}:\t{error.message}')
            raise ConfigValidatorException(errors)
        return coerced_config
    
    @classmethod
    def load_validated_config(cls, json_schema: Union[str, dict], config: dict):
        return cls(json_schema).load_config(config)

    @classmethod
    def load_validated_environment(cls, json_schema: Union[str, dict]=None):
        return cls.load_validated_config(json_schema, dict(os.environ))
        
    @classmethod
    def load_dotenv(cls, json_schema: Union[str, dict]=None, dotenv_path: str=None):
        config = dotenv.dotenv_values(dotenv_path)
        return cls.load_validated_config(
            json_schema or cls.get_default_json_schema(), config)