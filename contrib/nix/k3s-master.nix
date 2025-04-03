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
  cfg = config.services.yatb.k3s;

  registrySetup = pkgs.writeText "registries.yaml" (
    lib.generators.toYAML { } {
      mirrors."registry.local".endpoint = [ "http://${cfg.domain}:5000/v2" ];
    }
  );
in
{
  options.services.yatb.k3s = with lib; {
    enable = mkEnableOption "k3s";

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

    domain = mkOption {
      type = types.str;
    };

    token = mkOption {
      type = types.str;
    };

    dockerRegistry = {
      domain = mkOption {
        type = types.str;
      };

      port = mkOption {
        type = types.int;
        default = 5000;
      };
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = with pkgs; [
      htop
      tmux
      tcpdump
      tshark
      k9s
    ];

    services.minio = {
      enable = true;
      listenAddress = ":${cfg.minio.port}";

      inherit (cfg.minio) secretKey accessKey;
    };

    services.dockerRegistry = {
      enable = true;

      extraConfig = { };

      listenAddress = "0.0.0.0";
      port = cfg.dockerRegistry.port;
      openFirewall = true;
    };

    environment.etc."rancher/k3s/registries.yaml".source = registrySetup;

    services.k3s = {
      enable = true;
      role = "server"; # force server...
      disableAgent = lib.mkDefault true;
      token = cfg.token;
      extraFlags = builtins.concatStringsSep " " [
        "--tls-san='${cfg.domain}'"
      ];
    };

    networking.firewall.interfaces.${config.rubikoid.ctf.internalIface} = {
      allowedTCPPorts = [
        6443 # k8s api
        10250 # need for k3s

        cfg.minio.port # minio
        # 9001 # minio ui
        cfg.dockerRegistry.port
      ];
      allowedUDPPorts = [
        8472 # need for k3s
      ];
    };
  };
}
