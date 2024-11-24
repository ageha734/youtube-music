{ pkgs, ... }: {
  channel = "stable-24.05";

  packages = [
    pkgs.mise
  ];

  env = {};
  idx = {
    extensions = [
      "ms-python.python"
      "ms-python.debugpy"
      "ms-python.mypy-type-checker"
      "charliermarsh.ruff"
    ];

    workspace = {
      onCreate = {
        mise-install = "mise install";
        pdm-install = "pdm install";
      };
      onStart = {
        # watch-backend = "pdm run watch-backend";
      };
    };
  };
}
