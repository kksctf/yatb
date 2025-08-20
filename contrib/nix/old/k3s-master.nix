{ simpleSecrets, lib, config, pkgs, ... }:
let
  cfg = config.rubikoid.ctf.k3s;

  kubevirt-src = rec {
    version = "v1.5.1";

    operator = pkgs.fetchurl {
      url = "https://github.com/kubevirt/kubevirt/releases/download/${version}/kubevirt-operator.yaml";
      hash = "sha256-tmYjXqqTD+FNjIryGNgTPhvmGEsW0bBVVOsDy53QL5E=";
    };

    cr = pkgs.writeText "kubevirt-cr.yaml" (
      lib.generators.toYAML { } {
        apiVersion = "kubevirt.io/v1";
        kind = "KubeVirt";
        metadata = {
          name = "kubevirt";
          namespace = "kubevirt";
        };
        spec = {
          certificateRotateStrategy = { };
          configuration = {
            developerConfiguration = {
              useEmulation = true;

              # featureGates = [
              #   "HostDisk"
              # ];
              # logVerbosity = {
              #   virtLauncher = 3;
              #   virtHandler = 3;
              # };
            };
          };
          customizeComponents = { };
          imagePullPolicy = "IfNotPresent";
          workloadUpdateStrategy = { };
        };
      }
    );
  };

  calico-src = rec {
    version = "v3.30.0";

    operator = pkgs.fetchurl {
      url = "https://raw.githubusercontent.com/projectcalico/calico/${version}/manifests/operator-crds.yaml";
      hash = "sha256-NTP8fVygu15ZXS/maWWtkZnnK00hOWX1Z6Zrn8XXEro=";
    };

    tigera-operator = pkgs.fetchurl {
      url = "https://raw.githubusercontent.com/projectcalico/calico/${version}/manifests/tigera-operator.yaml";
      hash = "sha256-T82nFRWrNYqUxOgbEpY+UImejG6qdXqftYfRfEeZ96s=";
    };

    rawCrs = [
      {
        apiVersion = "operator.tigera.io/v1";
        kind = "Installation";
        metadata.name = "default";
        spec.calicoNetwork = {
          nodeAddressAutodetectionV4 = {
            firstFound = false;
            # interface = "ens8";
            skipInterface = "wg.*";
          };
          ipPools = [
            {
              name = "default-ipv4-ippool";
              blockSize = 26;
              cidr = "10.42.0.0/16";
              encapsulation = "VXLAN";
              natOutgoing = "Enabled";
              nodeSelector = "all()";
            }
            # {
            #   name = "default-ipv4-ippool-2";
            #   blockSize = 26;
            #   cidr = "10.43.0.0/16";
            #   encapsulation = "VXLANCrossSubnet";
            #   natOutgoing = "Enabled";
            #   nodeSelector = "all()";
            # }
          ];
        };
      }
      {
        apiVersion = "operator.tigera.io/v1";
        kind = "APIServer";
        metadata.name = "default";
        spec = { };
      }
      {
        apiVersion = "operator.tigera.io/v1";
        kind = "Goldmane";
        metadata.name = "default";
      }
      {
        apiVersion = "operator.tigera.io/v1";
        kind = "Whisker";
        metadata.name = "default";
      }
    ];

    cr = pkgs.writeText "calico-cr.yaml" (
      builtins.concatStringsSep "\n---\n" (map (entry: lib.generators.toYAML { } entry) rawCrs)
    );
  };

  registrySetup = pkgs.writeText "registries.yaml" (
    lib.generators.toYAML { } {
      mirrors."registry.local".endpoint = [ "http://${cfg.clusterHead}:5000/v2" ];
    }
  );
in
{
  options.rubikoid.ctf.k3s = with lib; {
    enable = mkEnableOption "k3s";

    iface = mkOption {
      type = types.str;
    };

    role = mkOption {
      type = types.enum [
        "agent"
        "server"
      ];
    };

    clusterHead = mkOption {
      type = types.str;
    };

    token = mkOption {
      type = types.str;
    };


  };
  config = lib.mkIf cfg.enable {
    environment.systemPackages = with pkgs; [
      k9s
      kubevirt
      calicoctl
      iptables
    ];

    environment.etc."rancher/k3s/registries.yaml".source = registrySetup;

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
            "--node-ip=${simpleSecrets.cluster.${config.device}.internal}"
            "--node-external-ip=${simpleSecrets.cluster.${config.device}.internal},${
              simpleSecrets.cluster.${config.device}.wg
            }"
            "--kube-proxy-arg='--proxy-mode=ipvs'"
          ]
          ++ (
            if cfg.role == "server" then
              [
                "--cluster-cidr=10.42.0.0/16"
                "--service-cidr=10.43.0.0/16"
                "--flannel-backend=none"
                "--disable-network-policy"
                "--disable=traefik"
              ]
            else
              [ ]
          )
        );

        manifests = {
          # kubevirt-operator.source = kubevirt-src.operator;
          # kubevirt-cr.source = kubevirt-src.cr;

          # calico-operator.source = calico-src.operator;
          # calico-tigera-operator.source = calico-src.tigera-operator;
          # calico-cr.source = calico-src.cr;
        };
      }
      (lib.mkIf (cfg.role == "server") {
        clusterInit = true;
      })
      (lib.mkIf (cfg.role == "agent") {
        serverAddr = "https://${cfg.clusterHead}:6443";
      })
    ];

    services.minio = lib.mkIf (cfg.role == "server") {
      enable = true;
      listenAddress = ":${toString cfg.minio.port}";

      inherit (cfg.minio) secretKey accessKey;
    };

    services.dockerRegistry = lib.mkIf (cfg.role == "server") {
      enable = true;

      extraConfig = { };

      listenAddress = "0.0.0.0";
      port = 5000;
      openFirewall = true;
    };

    networking.firewall.enable = lib.mkForce false;

    networking.firewall.allowedTCPPorts = [
      6443
    ];

    networking.firewall.interfaces.${cfg.iface} = {
      allowedTCPPorts = [
        179 # calico BGP
        443 # k3s: idk
        6443 # k3s: required so that pods can reach the API server (running on port 6443 by default)
        2379 # k3s, etcd clients: required if using a "High Availability Embedded etcd" configuration
        2380 # k3s, etcd peers: required if using a "High Availability Embedded etcd" configuration
        5473 # calico, typha
        10250 # k3s metrics
        #
        5000 # docker registry
        9000 # minio
        9001 # minio ui
      ];

      allowedUDPPorts = [
        4789 # calico, VXLan
        8472 # k3s, flannel: required if using multi-node for inter-node networking
      ];
    };

    # allowedUDPPortRanges = [
    #   {
    #     from = 11337;
    #     to = 12337;
    #   }
    # ];

    # allowedTCPPortRanges = [
    #   {
    #     from = 30000;
    #     to = 32767;
    #   }
    # ];
  };
}
