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

  cfg = config.services.yatb.yatb;
  ctfCfg = config.ctf;

  settings = cfg.settings;

  k3sSettings = config.rubikoid.services.k3s;
  dtcConfig = config.rubikoid.services.dtc;

  yatb = (inputs.self.yatb_source pkgs);
  package = cfg.package;
in
# env = cfg.env;
{
  options.services.yatb.yatb = with lib; {
    enable = mkEnableOption "The yatb service";

    package = mkOption {
      type = types.package;
      default = yatb.env;
      defaultText = literalExpression "yatb.env";
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
        default = 9900;
        description = "The port on which to listen.";
      };
    };

    settings = {
      docsPrefix = mkOption {
        type = types.nullOr types.str;
        default = null;
        description = "__secret__ prefix for docs";
      };

      flagBase = mkOption {
        type = types.str;
        default = "flag";
        description = "flag base ({this}{some_flag_body})";
      };

      ctfName = mkOption {
        type = types.str;
        default = "NIX-Based CTF";
        description = "name of the ctf (draws on front-end)";
      };

      keys = {
        jwt = mkOption {
          type = types.str;
          description = "jwt secret key";
        };

        flagSign = mkOption {
          type = types.str;
          description = "flag signing key";
        };

        apiToken = mkOption {
          type = types.str;
          description = "api token";
        };

        wsApiToken = mkOption {
          type = types.str;
          description = "websockets api token";
        };
      };

      authWays = mkOption {
        type = types.listOf types.str;
        default = [ ];
        description = "Enabled auth ways";
      };

      dynamic = {
        controller = mkOption {
          type = types.nullOr types.str;
          default = null;
          description = "address of dynamic tasks controller";
        };

        token = mkOption {
          type = types.nullOr types.str;
          default = null;
          description = "token for controller";
        };
      };

      extra = mkOption {
        type = types.attrs;
      };
    };

    publicAddr = mkOption {
      type = types.str;
      description = "public address of yatb";
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

  config = lib.mkIf cfg.enable {
    services.ferretdb = {
      enable = true;
      settings = {
        FERRETDB_LISTEN_ADDR = "127.0.0.1:27017";
        FERRETDB_TELEMETRY = "disabled";
      };
    };

    networking.firewall.allowedTCPPorts = lib.mkIf cfg.openFirewall [
      80
      443
    ];

    services.caddy = {
      enable = true;

      virtualHosts =
        let
          yatbCaddyCfg = ''
            root /static/* ${cfg.package + "/lib/python3.12/site-packages/app/view/static"}
            file_server /static/*

            reverse_proxy http://127.0.0.1:${toString cfg.http.port}
          '';
        in
        {
          ${cfg.publicAddr}.extraConfig = yatbCaddyCfg;
          # "yatb.prod.${cfg.publicAddr}".extraConfig = yatbCaddyCfg;

          ${ctfCfg.staticDomain}.extraConfig = ''
            root * ${ctfCfg.staticFolder}
            file_server browse
          '';

          "http://${dtcConfig.s3PublicAddr}".extraConfig = ''
            reverse_proxy http://127.0.0.1:${toString (cfg.http.port + 1)}
          '';
        };
    };

    systemd.tmpfiles.settings = {
      "11-ctf-static" = {
        ${ctfCfg.staticFolder} = {
          d = {
            mode = "0775";
            user = "root";
            group = "root";
          };
        };
      };
    };

    systemd.services.yatb = {
      enable = true;
      description = "YATB";
      wantedBy = [ "multi-user.target" ];

      environment = {
        DEBUG = "False";
        TESTING = "False";
        PROFILING = "False";

        MONGO = "mongodb://127.0.0.1:27017";

        JWT_SECRET_KEY = settings.keys.jwt;
        FLAG_SIGN_KEY = settings.keys.flagSign;

        FASTAPI_DOCS_URL = "/${settings.docsPrefix}-docs";
        FASTAPI_REDOC_URL = "/${settings.docsPrefix}-redoc";
        FASTAPI_OPENAPI_URL = "/${settings.docsPrefix}-openapi.json";

        FLAG_BASE = settings.flagBase;
        CTF_NAME = settings.ctfName;

        API_TOKEN = settings.keys.apiToken;
        WS_API_TOKEN = settings.keys.wsApiToken;

        ENABLED_AUTH_WAYS = builtins.toJSON settings.authWays;

        DYNAMIC_TASKS_CONTROLLER = settings.dynamic.controller;
        DYNAMIC_TASKS_CONTROLLER_TOKEN = settings.dynamic.token;
      } // settings.extra;

      serviceConfig = {
        ExecStart = "${package}/bin/uvicorn app:app --host '${cfg.http.host}' --port '${toString cfg.http.port}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
        Restart = "on-failure";
        KillSignal = "SIGINT";

        StateDirectory = "yatb";
        # DynamicUser = "yes";
        User = "root";
      };
    };

    systemd.services.s3proxy = {
      enable = true;
      description = "YATB's dynamic tasks s3 proxy";
      wants = [ "minio.service" ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        DOCKER_REGISTRY_HOST = "0";
        EXTERNAL_IPS = "[]";
        EXTERNAL_TO_INTERNAL_IPS_MAPPING = "{}";

        S3_HOST = k3sSettings.domain;
        S3_PORT = k3sSettings.minio.port;
        S3_ACCESS = k3sSettings.minio.accessKey;
        S3_SECRET = k3sSettings.minio.secretKey;

        DYNAMIC_TASKS_CONTROLLER_TOKEN = settings.dynamic.token;
      };

      serviceConfig = {
        ExecStart = "${package}/bin/uvicorn dynamic_tasks_app.s3_serve:app --host '${cfg.http.host}' --port '${toString (cfg.http.port + 1)}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
        Restart = "on-failure";
        KillSignal = "SIGINT";
        # DynamicUser = "yes";
        User = "root";
      };
    };
  };
}
