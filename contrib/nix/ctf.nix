{
  pkgs,
  config,
  inputs,
  secrets,
  lib,
  ...
}:
let
  cfg = config.ctf;
in
{
  imports = with lib.r.modules; [
    ./k3s-master.nix
    ./yatb.nix
    ./dtc.nix
  ];

  options.ctf = {
    rootDomain = lib.mkOption {
      type = lib.types.str;
    };

    internalIface = lib.mkOption {
      type = lib.types.str;
    };

    staticDomain = lib.mkOption {
      type = lib.types.str;
    };

    staticFolder = lib.mkOption {
      type = lib.types.str;
    };

    pathToUUIDMapping = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
    };

    externalToInternalMapping = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
    };
  };

  config = {
    config.services.yatb = {
      k3s = {
        domain = lib.mkDefault "k3s.internal.${cfg.rootDomain}";
        docker.domain = lib.mkDefault "docker.internal.${cfg.rootDomain}";
      };

      dtc = {
        publicAddr = lib.mkDefault "dtc.prod.${cfg.rootDomain}";
        s3PublicAddr = lib.mkDefault "dynamic.${cfg.rootDomain}";

        settings = {
          ports = {
            start = lib.mkDefault 20000;
            end = lib.mkDefault 30000;
          };
        };
      };

      yatb = {
        publicAddr = lib.mkDefault "${cfg.rootDomain}";
        settings.dynamic.controller = lib.mkDefault "https://${config.services.yatb.dtc.publicAddr}";
      };
    };
  };
}
