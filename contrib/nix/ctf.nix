{
  pkgs,
  config,
  inputs,
  secrets,
  lib,
  ...
}:
let
  cfg = config.rubikoid.ctf;
in
{
  options.rubikoid.ctf = with lib; {
    rootDomain = mkOption {
      type = types.str;
    };

    externalIface = mkOption {
      type = types.str;
    };

    internalIface = mkOption {
      type = types.str;
      default = "lo";
    };

    cluster = lib.mkOption {
      type = types.attrsOf (
        types.submodule (
          { name, ... }:
          let
            conf = cfg.cluster.name;
          in
          {
            options = {
              name = lib.mkOption {
                type = types.str;
                default = name;
              };

              external = mkOption {
                type = types.nullOr types.str;
                default = null;
              };

              internal = mkOption {
                type = types.str;
                default = "127.0.0.1";
              };
            };
          }
        )
      );
      default = { };
    };
  };

  config = {
    rubikoid.ctf = { };
  };
}
