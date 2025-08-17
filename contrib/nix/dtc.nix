{
  lib,
  config,
  pkgs,
  inputs,
  simpleSecrets,
  ...
}:

let
  rCfg = config.rubikoid.ctf;
  cfg = rCfg.dtc;

  k3s = rCfg.k3s;
  yatb = rCfg.yatb;

  settings = cfg.settings;
in
{
  options.rubikoid.ctf.dtc = with lib; {
    enable = mkEnableOption "The yatb's dynamic task controller service";

    package = mkOption {
      type = types.package;
      default = inputs.yatb.packages.x86_64-linux.default;
      defaultText = literalExpression "inputs.yatb.packages.x86_64-linux.default";
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

        KUBE_CONFIG_PATH = settings.k3s;

        S3_HOST = k3s.clusterHead;
        S3_PORT = toString k3s.minio.port;
        S3_ACCESS = k3s.minio.accessKey;
        S3_SECRET = k3s.minio.secretKey;
        S3_HOST_KANIKO = k3s.clusterHead;

        DYNAMIC_TASKS_ETCD = simpleSecrets.cluster.${config.device}.internal;
        DYNAMIC_TASKS_ETCD_PORT = toString config.rubikoid.ctf.etcd.port;

        DOCKER_REGISTRY_HOST = k3s.clusterHead;

        EXTERNAL_TO_INTERNAL_IPS_MAPPING = builtins.toJSON {
          master = [
            simpleSecrets.cluster.pod1.internal
            simpleSecrets.cluster.pod1.wg
          ];
        };

        S3_PROXY_HOST = "https://${yatb.s3ProxyAddr}";

        # DO_WORK = "false";

        ADMIN_PASSWORD = "oiyuv4b5o2ivu34tbvknjy34g5khv23g5";

        JWT_SECRET_KEY = yatb.settings.keys.jwt;
        FLAG_SIGN_KEY = yatb.settings.keys.flagSign;
        API_TOKEN = yatb.settings.keys.apiToken;
        WS_API_TOKEN = yatb.settings.keys.wsApiToken;
        # PORT_START = toString settings.ports.start;
        # PORT_END = toString settings.ports.end;
      };
    in
    {
      systemd.services = {
        dtc = {
          enable = true;
          description = "YATB's dynamic tasks controller";
          wants = [ "k3s.service" ];
          wantedBy = [ "multi-user.target" ];

          environment = env;

          serviceConfig = {
            ExecStart = "${cfg.package}/bin/uvicorn dynamic_tasks_app.web:app --host '${cfg.http.host}' --port '${toString cfg.http.port}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
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
