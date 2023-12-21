# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['logger', 'coerce_primitive_values', 'extract_declared_items', 'ConfigValidatorException', 'ConfigValidator']

# %% ../nbs/00_core.ipynb 2
from nbdev.showdoc import *
from fastcore.test import *
from unittest.mock import patch

import dotenv
import json
import os
import jsonschema
import logging
from jsonschema import validate, ValidationError
from typing import Union
from fs.base import FS
from fs.osfs import OSFS


logger = logging.getLogger(__name__)

# %% ../nbs/00_core.ipynb 3
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

# %% ../nbs/00_core.ipynb 6
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

# %% ../nbs/00_core.ipynb 8
class ConfigValidatorException(Exception):
    
    def __init__(self, errors):
        super().__init__('config failed to validate against JSON schema')
        self.errors = errors


class ConfigValidator(object):

    DEFAULT_STORAGE_DRIVER: FS = OSFS('.')
    
    CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME = 'CONFIG_VALIDATOR_JSON_SCHEMA'

    @classmethod
    def load_json(cls, json_source: Union[str, dict]=None, storage_driver: FS = None) -> dict:
        '''
        convenience method to return a dict from either
        a file path or an already-loaded dict
        '''
        storage_driver = storage_driver or cls.DEFAULT_STORAGE_DRIVER
        if isinstance(json_source, str):
            with storage_driver.open(json_source) as ifile:
                return json.load(ifile)
        elif isinstance(json_source, dict):
            return json_source

    @classmethod
    def get_default_json_schema(cls, storage_driver: FS = None) -> dict:
        storage_driver = storage_driver or cls.DEFAULT_STORAGE_DRIVER
        if cls.CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME in os.environ:
            expected_json_schema_path = \
                os.environ[cls.CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME]
            with storage_driver.open(expected_json_schema_path) as ifile:
                return json.load(ifile)
        return None

    def __init__(self, json_schema: Union[str, dict]=None, storage_driver: FS=None):
        '''
        :param json_schema: a str path to a json schema file, or a schema in dict form
        
        if no value is provided, it will fall back to looking for
        an environment variable corresponding to the class variable
        `CONFIG_VALIDATOR_JSON_SCHEMA_ENVVAR_NAME`
        to find a JSON schema file
        '''
        self.storage_driver = storage_driver or self.__class__.DEFAULT_STORAGE_DRIVER
        if isinstance(json_schema, (str, dict)):
            self._json_schema = self.__class__.load_json(json_schema, storage_driver=self.storage_driver)
        elif (default_schema := self.__class__.get_default_json_schema(storage_driver=self.storage_driver)):
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
    def load_validated_config(cls, json_schema: Union[str, dict], config: dict, **kwargs):
        return cls(json_schema, **kwargs).load_config(config)

    @classmethod
    def load_validated_environment(cls, json_schema: Union[str, dict]=None, **kwargs):
        return cls.load_validated_config(json_schema, dict(os.environ), **kwargs)
        
    @classmethod
    def load_dotenv(cls,
                    json_schema: Union[str, dict]=None,
                    dotenv_path: str=None,
                    storage_driver: FS=None,
                    override: bool=False,
                   ):
        '''
        :param override: set variables into os.environ where applicable; i.e.
        - if set in os.environ already and valid, leave alone
        - if not set in os.environ already, read from .env or schema default
        '''
        
        storage_driver = storage_driver or cls.DEFAULT_STORAGE_DRIVER
        if dotenv_path is None:
            maybe_dotenv_path = dotenv.find_dotenv()  # '' if not exist
            if maybe_dotenv_path:
                logger.debug(f'using detected dotenv path; {maybe_dotenv_path}')
                dotenv_path = maybe_dotenv_path
        if dotenv_path:
            with storage_driver.open(dotenv_path) as ifile:
                config = dotenv.dotenv_values(stream=ifile)
        else:
            config = {}
        loaded_config = config.copy()
        
        json_schema_dict = cls.load_json(json_schema, storage_driver=storage_driver) or {}
        for key in json_schema_dict.get('properties', []):
            if key not in os.environ:
                continue
            if key in config and config[key] != os.environ[key]:
                logger.debug(f'os.environ key "{key}" overriding value present in {dotenv_path}')
            config[key] = os.environ[key]
        validated_config = cls.load_validated_config(
            json_schema or cls.get_default_json_schema(storage_driver=storage_driver),
            config, storage_driver=storage_driver)
        
        if override:
            for key, value in validated_config.items():
                if key in os.environ:
                    continue
                os.environ[key] = value
                
        return validated_config
