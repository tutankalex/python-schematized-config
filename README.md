schematized config
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

## Install

``` sh
pip install python_schematized_config
```

## usage

``` python
from schematized_config.core import ConfigValidator
```

``` python
import os
import os.path as _p

if _p.exists('.env') and 'CONFIG_VALIDATOR_JSON_SCHEMA' in os.environ:
    ConfigValidator.load_dotenv()  # use defaults of .env and CONFIG_VALIDATOR_JSON_SCHEMA
```

# development

<details>
<summary>
entering the development environment
</summary>

assuming you have [nix](https://nixos.org/download.html) installed and
ready, make sure `nix-command` and `flake` are enabled (oneliner: run
`export NIX_CONFIG="experimental-features = nix-command flakes"` in the
terminal), then enter the dev shell using `nix develop`

start the jupyter notebook using the provided alias or just
`jupyter notebook`, and hack away
</details>

## nbdev

this package is developed using [nbdev](https://nbdev.fast.ai/), so we
use an nbdev-centric development flow. For a quick guide, we recommend
checking out the [end-to-end
walkthrough](https://nbdev.fast.ai/tutorials/tutorial.html). But in
short: edit notebooks, then run the `nbdev_*` management commands. The
most essential flow is as follows:

1.  edit the notebook files (core fore core, and cli for the command
    line interface)
2.  `python setup.py install` \# note we don’t use `nbdev_install`
    because we manage `quarto` using `nix`
3.  `nbdev_prepare`
4.  run code using the package
5.  `nbdev_release`
6.  `nbdev_pypi`

### running tests

if you share variables between cells in your test blocks, this causes
trouble during `nbdev_prepare` as it tries to run cells in isolation,
leading to e.g.

    NameError: name 'example_properties_schema' is not defined

to deal with this, you can merge cells that use a common variable

### updating package dependencies

note that package dependencies are specified in
[settings.ini](./settings.ini); you shouldn’t be editing `setup.py` by
hand. To add a requirement, add it to the `requuirements` entry in
`settings.ini`, then run `python setup.py install`
