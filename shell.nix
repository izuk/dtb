let
  pkgs = import <nixos-unstable> {};
  shell = pkgs.mkShell {
    buildInputs = with pkgs; [
      imagemagick
      typst
      python3Packages.discordpy
      ];
  };  
in shell
