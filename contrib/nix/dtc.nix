{
  lib,
  my-lib,
  config,
  pkgs,
  inputs,
  ...
}:

let
  types = lib.types;

  cfg = config.services.yatb.dtc;
  ctfCfg = config.ctf;

  settings = cfg.settings;

  yatbSettings = config.services.yatb.yatb.settings;
  k3sSettings = config.services.yatb.k3s;

  package = cfg.package;
in
{
  options.services.yatb.dtc = with lib; {
    enable = mkEnableOption "The yatb's dynamic task controller service";

    package = mkOption {
      type = types.package;
      default = pkgs.yatb;
      defaultText = literalExpression "pkgs.yatb";
      description = "YATB env";
    };

    http = {
      host = mkOption {
        type = types.str;
        default = "127.0.0.1";
        example = "::1";
        description = "Only listen to incoming requests on specific IP/host.";
      };

      port = mkOption {
        type = types.port;
        default = 9800;
        description = "The port on which to listen.";
      };
    };

    settings = {
      token = mkOption {
        type = types.nullOr types.str;
        default = yatbSettings.dynamic.token;
        description = "token for controller";
      };

      k3s = mkOption {
        type = types.str;
        default = "/etc/rancher/k3s/k3s.yaml";
        description = "path to k3s config";
      };

      ports = {
        start = mkOption {
          type = types.port;
        };
        end = mkOption {
          type = types.port;
        };
      };

      externalIps = mkOption {
        type = types.listOf types.str;
        default = [ ];
      };
    };

    publicAddr = mkOption {
      type = types.str;
      description = "public address of dtc";
    };

    s3PublicAddr = mkOption {
      type = types.str;
      description = "public address of s3 proxy";
    };

    openFirewall = mkOption {
      default = false;
      type = types.bool;
      description = "Whether to open the firewall for the specified port.";
    };

    extraArgs = mkOption {
      type = types.listOf types.str;
      default = [ ];
      example = [ ];
      description = "Extra cmd for uvicorn";
    };
  };

  config = lib.mkIf cfg.enable (
    let
      env = {
        DEBUG = "False";
        TESTING = "False";
        PROFILING = "False";

        LOGURU_LEVEL = "TRACE";

        DYNAMIC_TASKS_CONTROLLER_TOKEN = settings.token;

        KUBE_CONFIG_PATH = settings.k3s;

        DOCKER_REGISTRY_HOST = k3sSettings.dockerDomain;

        S3_HOST = k3sSettings.domain;
        S3_PORT = k3sSettings.minio.port;
        S3_ACCESS = k3sSettings.minio.accessKey;
        S3_SECRET = k3sSettings.minio.secretKey;

        PORT_START = toString settings.ports.start;
        PORT_END = toString settings.ports.end;

        UUID_TO_PATH_MAPPING = builtins.toJSON ctfCfg.pathToUUIDMapping;

        EXTERNAL_TO_INTERNAL_IPS_MAPPING = builtins.toJSON ctfCfg.externalToInternalMapping;

        S3_PROXY_HOST = "http://${cfg.s3PublicAddr}";
      };
    in
    {
      networking.firewall.allowedTCPPorts = lib.mkIf cfg.openFirewall [
        cfg.http.port
        8443
      ];

      services.caddy = {
        enable = true;

        virtualHosts = {
          "${cfg.publicAddr}:8443".extraConfig = ''
            tls internal
            reverse_proxy http://127.0.0.1:${toString cfg.http.port}
          '';
        };
      };

      systemd.services.caddy.path = with pkgs; [ nss ];

      systemd.services = {
        dtc = {
          enable = true;
          description = "YATB's dynamic tasks controller";
          wants = [ "k3s.service" ];
          wantedBy = [ "multi-user.target" ];

          environment = env;

          serviceConfig = {
            ExecStart = "${package}/bin/uvicorn dynamic_tasks_app.web:app --host '${cfg.http.host}' --port '${toString cfg.http.port}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
            Restart = "on-failure";
            KillSignal = "SIGINT";
            # DynamicUser = "yes";
            User = "root";
          };
        };
      };
    }
  );
}
