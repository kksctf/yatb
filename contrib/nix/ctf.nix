{
  pkgs,
  config,
  inputs,
  secrets,
  lib,
  ...
}:
let
  cfg = config.rubikoid.ctf;
in
{
  options.rubikoid.ctf = with lib; {
    rootDomain = mkOption {
      type = types.str;
    };

    roles = lib.mkOption {
      type = (
        types.submodule {
          options = {
            external_ip = mkOption {
              type = types.str;
            };
          };
        }
      );
    };

    # roles = lib.mkOption {
    #   type = (
    #     types.submodule {
    #       options = {

    #       };
    #     }
    #   );
    # };
  };

  config = {
    rubikoid.ctf = { };
  };
}
