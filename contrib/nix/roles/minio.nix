{ lib, config, pkgs, ... }:

let
  rCfg = config.rubikoid.ctf;
  cfg = rCfg.minio;
in
{
  options.rubikoid.ctf.minio = with lib; {
    enable = mkEnableOption "minio";

    minio = {
      secretKey = mkOption {
        type = types.str;
      };

      accessKey = mkOption {
        type = types.str;
      };

      port = mkOption {
        type = types.int;
        default = 9000;
      };
    };
  };

  config = lib.mkIf cfg.enable {
    services.minio = {
      enable = true;
      listenAddress = ":${toString cfg.minio.port}"; # FIXME: all hosts mb not?

      inherit (cfg.minio) secretKey accessKey;
    };
  };
}
