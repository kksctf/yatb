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
  };

  config = {
    rubikoid.ctf = {
      
    };
  };
}
