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
  cfg = rCfg.yatb;

  settings = cfg.settings;
in
{
  options.rubikoid.ctf.yatb = with lib; {
    enable = mkEnableOption "yatb";

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
        default = 9000;
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

      extra = mkOption {
        type = types.attrs;
        default = { };
      };
    };

    publicAddr = mkOption {
      type = types.str;
      description = "public address of yatb";
      default = rCfg.rootDomain;
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
        FERRETDB_TELEMETRY = "disable";
      };
    };

    networking.firewall.allowedTCPPorts = [
      80
      443
    ];

    networking.domains = {
      enable = true;
      baseDomains = {
        ${rCfg.rootDomain} = {
          a.data = rCfg.cluster.${config.device}.external;
        };
      };
      subDomains."${cfg.publicAddr}" = { };
    };

    services.caddy = {
      enable = true;

      virtualHosts = {
        ${cfg.publicAddr}.extraConfig = ''
          root /static/* ${cfg.package + "/lib/python3.12/site-packages/app/view/static"}
          file_server /static/*

          reverse_proxy http://127.0.0.1:${toString cfg.http.port}
        '';
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

        DYNAMIC_TASKS_ETCD = "127.0.0.1"; # TODO: select ip properly
        DYNAMIC_TASKS_ETCD_PORT = toString rCfg.etcd.clientPort;
      } // settings.extra;

      serviceConfig = {
        ExecStart = "${cfg.package}/bin/uvicorn yatb.app:app --host '${cfg.http.host}' --port '${toString cfg.http.port}' ${lib.strings.escapeShellArgs cfg.extraArgs}";
        Restart = "on-failure";
        KillSignal = "SIGINT";

        StateDirectory = "yatb";
        # DynamicUser = "yes";
        User = "root";
      };
    };
  };
}
