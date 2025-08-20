{ inputs, lib, config, pkgs, ... }:

let
  rCfg = config.rubikoid.ctf;
  cfg = rCfg.dtc;

  k3s = rCfg.k3s;
  yatb = rCfg.yatb;
  s3 = rCfg.s3;
  minio = rCfg.minio;

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

        S3_HOST = "127.0.0.1"; # TODO: select ip properly
        S3_HOST_KANIKO = "s3-fwr.kube-system.svc.cluster.local";
        S3_PORT_KANIKO = "9002";

        DOCKER_REGISTRY_HOST = "docker-registry-fwr.kube-system.svc.cluster.local";
        DOCKER_REGISTRY_PORT = "5001";
        DOCKER_REGISTRY_HOST_LOCAL = "127.0.0.1"; # TODO: make it better
        DOCKER_REGISTRY_PORT_LOCAL = "5000"; # TODO: make it better

        S3_PORT = toString minio.port;
        S3_ACCESS = minio.accessKey;
        S3_SECRET = minio.secretKey;

        DYNAMIC_TASKS_ETCD = "127.0.0.1"; # TODO: select ip properly
        DYNAMIC_TASKS_ETCD_PORT = toString rCfg.etcd.clientPort;

        EXTERNAL_TO_INTERNAL_IPS_MAPPING = builtins.toJSON {
          "${rCfg.cluster.${config.device}.external}" = [
            "192.168.199.35"
            # rCfg.cluster.${config.device}.external
          ];
        };

        S3_PROXY_HOST = "https://${s3.proxyDomain}";

        ADMIN_PASSWORD = "oiyuv4b5o2ivu34tbvknjy34g5khv23g5";

        JWT_SECRET_KEY = yatb.settings.keys.jwt;
        FLAG_SIGN_KEY = yatb.settings.keys.flagSign;
        API_TOKEN = yatb.settings.keys.apiToken;
        WS_API_TOKEN = yatb.settings.keys.wsApiToken;

        PORT_START = toString rCfg.dynamicPorts.start;
        PORT_END = toString rCfg.dynamicPorts.end;
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
            ExecStart = "${cfg.package}/bin/uvicorn dtc.web:app --host '${cfg.http.host}' --port '${toString cfg.http.port}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
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
