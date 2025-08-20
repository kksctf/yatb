{ lib, config, pkgs, ... }:

let
  rCfg = config.rubikoid.ctf;
  cfg = rCfg.etcd;
in
{
  options.rubikoid.ctf.etcd = with lib; {
    enable = mkEnableOption "etcd";

    clientPort = mkOption {
      type = types.int;
      default = 8379;
    };

    peerPort = mkOption {
      type = types.int;
      default = 8379;
    };

    peers = mkOption {
      type = types.listOf str;
    };
  };

  config = lib.mkIf cfg.enable {
    rubikoid.ctf.etcd.peers = [ config.device ];

    services.etcd = {
      enable = true;
      openFirewall = false;

      initialClusterState = "new";
      initialClusterToken = "yatb-prod";

      listenClientUrls = [
        "http://127.0.0.1:${toString cfg.clientPort}"
        "http://${rCfg.cluster.${config.device}.internal}:${toString cfg.clientPort}"
      ];

      listenPeerUrls = [
        "http://127.0.0.1:${toString cfg.peerPort}"
        "http://${rCfg.cluster.${config.device}.internal}:${toString cfg.peerPort}"
      ];

      initialCluster = lib.mkForce (
        lib.map (host: "${host.name}=http://${host.internal}:${toString host.peerPort}") (
          lib.attrValues cfg.cluster
        )
      );

      extraConf = { };
    };

    networking.firewall.interfaces.${rCfg.internalIface} = {
      allowedTCPPorts = [
        cfg.port
        cfg.peerPort
      ];
    };
  };
}
