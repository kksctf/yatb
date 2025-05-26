{
  inputs = {
    nixpkgs.url = "nixpkgs";

    base = {
      url = "github:rubikoid/nix-base";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { self, nixpkgs, base, ... }@inputs:
    let
      lib = base.lib.r.extender base.lib ({ lib, prev, r, prevr }: { });
    in
    {

    }
    // lib.r.mkFlake nixpkgs (
      { system, pkgs, ... }:
      let
        pythonOptions = {
          name = "yatb";
          source = ./.;

          sourcePreference = "wheel";
          python = pkgs: pkgs.python312;

          overrides =
            _final: _prev:
            let
              fixSetupTools =
                pkgName:
                _prev.${pkgName}.overrideAttrs (old: {
                  # nativeBuildInputs = old.nativeBuildInputs ++ [ ];
                  buildInputs = (old.buildInputs or [ ]) ++ [ _final.setuptools ];
                });
            in
            {
              formgen = fixSetupTools "formgen";
              www-authenticate = fixSetupTools "www-authenticate";
              "ruamel.yaml" = fixSetupTools "ruamel.yaml";
              "ruamel.yaml.clib" = fixSetupTools "ruamel.yaml.clib";
              "ruamel-yaml-clib" = fixSetupTools "ruamel-yaml-clib";
            };

          inherit inputs pkgs;
        };

        pythonSetup = lib.r.helpers.python.setupPythonEnvs pythonOptions;
      in
      {
        packages = {
          default = pythonSetup.simple.set.mkVirtualEnv "${pythonOptions.name}-env" pythonSetup.workspace.deps.all; # pythonSetup.simple.env;
        };

        devShells = {
          default = pkgs.mkShell {
            packages =
              (with pkgs; [
                k9s
                kubevirt
              ])
              ++ pythonSetup.editable.packages;

            nativeBuildInputs = with pkgs; [

            ];

            shellHook = ''
              ${pythonSetup.editable.shellHook}
            '';
          };

          # It is of course perfectly OK to keep using an impure virtualenv workflow and only use uv2nix to build packages.
          # This devShell simply adds Python and undoes the dependency leakage done by Nixpkgs Python infrastructure.
          impure = pkgs.mkShell {
            packages = [
              pkgs.python312
              pkgs.uv
            ];
            shellHook = ''
              unset PYTHONPATH
            '';
          };

        };
      }
    );
}
