{
  nixConfig.bash-prompt = ''\033[1;32m\[[nix-develop:\[\033[36m\]\w\[\033[32m\]]$\033[0m '';

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/23.05";
    whacked-setup = {
      url = "github:whacked/setup/58bdbff2eec48980b010048032382bed3a152e7e";
      flake = false;
    };
  };
  outputs = { self, nixpkgs, flake-utils, whacked-setup }:
    flake-utils.lib.eachDefaultSystem
    (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      whacked-helpers = import (whacked-setup + /nix/flake-helpers.nix) { inherit pkgs; };
    in {
      devShell = whacked-helpers.mkShell {
        flakeFile = __curPos.file;  # used to forward current file to echo-shortcuts
        includeScripts = [
          # e.g. for node shortcuts
          # (whacked-setup + /bash/node_shortcuts.sh)
        ];
      } {
        nativeBuildInputs = (
          if pkgs.stdenv.isDarwin then [
          ] else [
            pkgs.quarto
          ]
        );

        buildInputs = [
          pkgs.python3
        ];

        shellHook = (
          if pkgs.stdenv.isDarwin then ''
          ### PREFLIGHT
          if ! command -v quarto &> /dev/null; then
            pastel paint red "program 'quarto' not found in the path. nbdev requires it to work"
            echo -n "you can obtain it manually from "
            pastel paint yellow https://quarto.org/docs/get-started
            exit
          fi
          '' else ''
          '') + ''
          ### SETUP
          export VIRTUAL_ENV=''${VIRTUAL_ENV-$PWD/venv}
          # FIX for ImportError: libstdc++.so.6: cannot open shared object file: No such file or directory
          # but note that gcc may be a costly import
          export LD_LIBRARY_PATH=${pkgs.gcc-unwrapped.lib}/lib:$LD_LIBRARY_PATH
          export JUPYTER_CONFIG_DIR=''${JUPYTER_CONFIG_DIR-$PWD/.jupyter}
          if [ ! -e $JUPYTER_CONFIG_DIR ]; then
            mkdir $JUPYTER_CONFIG_DIR
          fi
          setup-venv() {  # install all expected virutalenv packages
            # see note at https://stackoverflow.com/a/65599505
            # on nb extensions (in)compatibility.
            # below versions are from trial and error
            pip install \
              twine==4.0.2 \
              notebook==6.2.0 \
              jupyter_server==2.3.0 \
              jupyter_core==5.2.0 \
              nbconvert==7.2.9 \
              nbformat==5.7.3 \
              nbdev==2.3.12 \
              jupytext==1.14.5 \
              jupyter_contrib_nbextensions==0.5.1 \
              jupyter_nbextensions_configurator
            jupyter contrib nbextension install --user
            ENABLE_BUNDLED_EXTENSIONS=(
                code_prettify/autopep8
                codefolding/main
                collapsible_headings/main
                contrib_nbextensions_help_item/main
                datestamper/main
                execute_time/ExecuteTime
                freeze/main
                scratchpad/main
                toc2/main
                toggle_all_line_numbers/main
                varInspector/main
            );
          }
          ensure-venv setup-venv
        '' + ''
          ### SHORTCUTS
          alias check='python -m schematized_config'
          alias start-jupyter='jupyter notebook'
          alias build='NIXPKGS_ALLOW_UNSUPPORTED_SYSTEM=1 nix build --impure'  # quarto unsupported on mac, but not needed at runtime
        '';  # join strings with +
      };

      packages = {
        default = pkgs.python3Packages.buildPythonPackage rec {
          pname = "schematized-config";
          version = "0.0.10";

          src = ./.;

          # these deps need to be outputted with the package output.
          # NOTE that these are duplicated by settings.ini!
          propagatedBuildInputs = with pkgs.python3Packages; [
            fs
            jsonschema
            nbdev
            python-dotenv
          ];

          # these deps are not needed at runtime
          buildInputs = with pkgs.python3Packages; [
            setuptools
          ];
        };
      };
    }
  );
}
