{ lib, config, pkgs, ... }:

let
  rCfg = config.rubikoid.ctf;
  cfg = rCfg.k3s;
in
{
  options.rubikoid.ctf.k3s = with lib; {
    enable = mkEnableOption "k3s";

    role = mkOption {
      type = types.enum [
        "server"
        "agent"
      ];
    };

    token = mkOption {
      type = types.str;
    };

    master = mkOption {
      type = types.str;
    };

    slaves = mkOption {
      type = types.listOf types.str;
      default = [ ];
    };
  };

  config = lib.mkIf cfg.enable {
    rubikoid.ctf.k3s = lib.mkMerge [
      (lib.mkIf (cfg.role == "server") {
        master = rCfg.cluster.${config.device}.internal;
      })
      (lib.mkIf (cfg.role == "agent") {
        slaves = [ rCfg.cluster.${config.device}.internal ];
      })
    ];

    environment.systemPackages = with pkgs; [
      k9s
      kubevirt
      calicoctl
      iptables
    ];

    environment.etc."rancher/k3s/registries.yaml".source = pkgs.writeText "registries.yaml" (
      lib.generators.toYAML { } {
        mirrors."registry.local".endpoint = [ "http://${cfg.master}:5000/v2" ];
      }
    );

    services.k3s = lib.mkMerge [
      {
        enable = true;

        role = cfg.role;
        token = cfg.token;

        disableAgent = false;

        environmentFile = pkgs.writeText "k3s.env" ''
          K3S_KUBECONFIG_MODE="644"
        '';

        extraFlags = builtins.concatStringsSep " " (
          [
            # "--tls-san='yatb-kube-master.nodes.internal.rubikoid.ru'"
            "--node-name=${config.device}"
            # "--node-ip=${rCfg.cluster.${config.device}.internal}"
            "--node-external-ip=${rCfg.cluster.${config.device}.external}"
            # "--kube-proxy-arg='--proxy-mode=ipvs'"
            "--flannel-iface=ens3"
          ]
          ++ (
            if cfg.role == "server" then
              [
                "--cluster-cidr=10.42.0.0/16"
                "--service-cidr=10.43.0.0/16"
                # "--flannel-backend=none"
                # "--disable-network-policy"
                # "--disable=traefik"
              ]
            else
              [ ]
          )
        );

        manifests = { };
      }
      (lib.mkIf (cfg.role == "server") {
        clusterInit = true;
      })
      (lib.mkIf (cfg.role == "agent") {
        serverAddr = "https://${cfg.master}:6443";
      })
    ];

    services.dockerRegistry = lib.mkIf (cfg.role == "server") {
      enable = true;

      extraConfig = { };

      listenAddress = "${cfg.master}";
      port = 5000;
      openFirewall = false; # TODO: thonk
    };

    networking.firewall = {
      interfaces.${rCfg.internalIface} = {
        allowedTCPPorts = [
          443 # k3s???
          6443 # k3s: required so that pods can reach the API server (running on port 6443 by default)
          2379 # k3s, etcd clients: required if using a "High Availability Embedded etcd" configuration
          2380 # k3s, etcd peers: required if using a "High Availability Embedded etcd" configuration
          10250 # k3s metrics
          #
          5000 # docker registry
          9000 # minio
          9001 # minio ui
        ];

        allowedUDPPorts = [
          8472 # k3s, flannel: required if using multi-node for inter-node networking
        ];
      };

      allowedTCPPorts = [
        6443 # k3s: required so that pods can reach the API server (running on port 6443 by default)
      ];

      allowedUDPPortRanges = [
        {
          from = rCfg.dynamicPorts.start;
          to = rCfg.dynamicPorts.end;
        }
      ];

      allowedTCPPortRanges = [
        {
          from = rCfg.dynamicPorts.start;
          to = rCfg.dynamicPorts.end;
        }
      ];
    };
  };
}
