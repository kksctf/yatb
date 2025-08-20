{ lib, config, pkgs, ... }:

let
  rCfg = config.rubikoid.ctf;
  cfg = rCfg.s3;
  minio = rCfg.minio;
in
{
  options.rubikoid.ctf.s3 = with lib; {
    enable = mkEnableOption "s3";

    http = {
      host = mkOption {
        type = types.str;
        default = "127.0.0.1";
        example = "::1";
        description = "Only listen to incoming requests on specific IP/host.";
      };

      port = mkOption {
        type = types.port;
        default = 8991;
        description = "The port on which to listen.";
      };
    };

    proxyDomain = mkOption {
      type = types.str;
      description = "public address of s3";
      default = "s3.${rCfg.rootDomain}";
    };

    rawProxyDomain = mkOption {
      type = types.str;
      description = "public address of s3";
      default = "rawS3.${rCfg.rootDomain}";
    };

    extraArgs = mkOption {
      type = types.listOf types.str;
      default = [ ];
      example = [ ];
      description = "Extra cmd for uvicorn";
    };
  };

  config = lib.mkIf cfg.enable {
    networking.firewall.allowedTCPPorts = [
      80
      443
    ];

    networking.domains = {
      enable = true;
      baseDomains = {
        ${cfg.proxyDomain} = {
          a.data = rCfg.cluster.${config.device}.external;
        };
        ${cfg.rawProxyDomain} = {
          a.data = rCfg.cluster.${config.device}.external;
        };
      };
      subDomains."${cfg.proxyDomain}" = { };
      subDomains."${cfg.rawProxyDomain}" = { };
    };

    services.caddy = {
      enable = true;

      virtualHosts."${cfg.proxyDomain}".extraConfig = ''
        ${rCfg.caddyExtra}
        reverse_proxy http://127.0.0.1:${toString cfg.http.port}
      '';

      virtualHosts."${cfg.rawProxyDomain}".extraConfig = ''
        reverse_proxy http://127.0.0.1:${toString minio.port}
      '';
    };

    systemd.services.s3proxy = {
      enable = true;
      description = "YATB's dynamic tasks s3 proxy";
      wants = [ "minio.service" ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        S3_HOST = "127.0.0.1"; # TODO: normal ip lol
        S3_PORT = toString minio.port;
        S3_ACCESS = minio.accessKey;
        S3_SECRET = minio.secretKey;

        JWT_SECRET_KEY = "";
        FLAG_SIGN_KEY = "";
        API_TOKEN = "";
        WS_API_TOKEN = "";

        ADMIN_PASSWORD = "";

        S3_HOST_KANIKO = "";
        DOCKER_REGISTRY_HOST = "";
        EXTERNAL_TO_INTERNAL_IPS_MAPPING = "{}";
        DYNAMIC_TASKS_ETCD = "";
      };

      serviceConfig = {
        ExecStart = "${rCfg.yatb.package}/bin/uvicorn dtc.s3_serve:app --host '${cfg.http.host}' --port '${toString (cfg.http.port)}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
        Restart = "on-failure";
        KillSignal = "SIGINT";
        # DynamicUser = "yes";
        User = "root";
      };
    };
  };
}
