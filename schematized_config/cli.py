# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_cli.ipynb.

# %% auto 0
__all__ = ['VERSION', 'EXECUTABLE_NAME', 'validate_env', 'generate_sample_dotenv', 'main']

# %% ../nbs/01_cli.ipynb 2
import argparse
import os
import sys
from typing import Union

import dotenv
from fastcore.script import anno_parser, call_parse

from .core import (ConfigValidator, ConfigValidatorException,
                                     extract_declared_items)

# %% ../nbs/01_cli.ipynb 3
def validate_env(json_schema: Union[str, dict], dotenv_path: str=None) -> bool:
    validator = ConfigValidator(json_schema)
    try:
        validator.load_config(dotenv.dotenv_values(dotenv_path))
        return True
    except ConfigValidatorException as ex:
        sys.stderr.write(f'{str(ex)}\n')
        for error in ex.errors:
            sys.stderr.write(f'{error.json_path}:\t{error.message}\n')
        return False

# %% ../nbs/01_cli.ipynb 4
def generate_sample_dotenv(json_schema: Union[str, dict], seed_config: dict=None) -> str:
    schema_dict = ConfigValidator.load_json(json_schema)
    merged_config = dict(os.environ)
    default_dotenv = dotenv.dotenv_values()
    merged_config.update(default_dotenv)
    merged_config.update(seed_config or {})
    extracted_config = extract_declared_items(schema_dict, merged_config)
    out = [
        f'{key}={value}'
        for key, value in extracted_config.items()
    ]
    # for all keys that are in the schema, but NOT in the current config,
    # add them as comments
    for (key, value_schema) in schema_dict['properties'].items():
        if key not in extracted_config:
            out.append(f'# {key}=<{value_schema.get("type")}>')
    return '\n'.join(out)

# %% ../nbs/01_cli.ipynb 6
import importlib

_self_module = importlib.import_module(
    ".",
    __name__.split('.')[0]  #  module_name
)
VERSION = getattr(_self_module, '__version__', 'NOT-IN-MODULE')  # fails in notebook, works in module
EXECUTABLE_NAME = 'schematized-config'

def _hack_docstring(func):
    # hack the docstring to inject the version
    # the docstring gets rendered as the second line in the CLI help,
    # but it doesn't simply take an f-string, so we hack it in
    func.__doc__ = f"{_self_module.__name__}: {func.__doc__} (v{VERSION})"
    return func

@call_parse
@_hack_docstring
def main(
    generate: str = None,  # path to a json schema that validates a dotenv
    schema: str = None,    # path to json schema used for validation
    validate: str = 'env',  # validate a dotenv; requires <schema>
):
    "friendly tools to work with schemas and dotenv"
    
    if generate:
        sys.stdout.write(generate_sample_dotenv(generate))
    elif schema and validate:
        dotenv_path = validate
        if validate_env(schema, dotenv_path):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        anno_parser(main, EXECUTABLE_NAME).print_help()
