"""Real create_profile calls and child processes, against isolated profile homes."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from hermes_cli import profile_provisioning, profiles
from hermes_cli.config import atomic_config_write


@pytest.fixture
def operator_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


@pytest.mark.parametrize("clone", [False, True])
def test_provisioner_finishes_before_profile_publication(operator_home, tmp_path, clone):
    script = tmp_path / "provision.py"
    script.write_text(
        "import json, os, sys\nfrom pathlib import Path\n"
        "c = json.load(sys.stdin)\n"
        "stage = Path(c['staging_home'])\n"
        "assert c['schema'] == 1 and c['name'] == 'research'\n"
        "assert stage.name.startswith('.') and stage.is_dir()\n"
        "assert not Path(c['destination_home']).exists()\n"
        "assert os.environ['HERMES_HOME'] == str(stage)\n"
        "(stage / 'provisioned.json').write_text(json.dumps(c))\n"
    )
    atomic_config_write(operator_home / "config.yaml", {
        "profiles": {"provision_command": [sys.executable, str(script)]},
    })
    result = profiles.create_profile("research", clone_from="default" if clone else None,
                                     no_alias=True)
    context = json.loads((result / "provisioned.json").read_text())
    assert context["default_home"] == str(operator_home)
    assert context["source_home"] == (str(operator_home) if clone else None)
    assert result == profiles.get_profile_dir("research")
    assert not Path(context["staging_home"]).exists()


def test_failure_does_not_publish_or_leak_child_output(operator_home, tmp_path, capsys):
    script = tmp_path / "fail.py"
    script.write_text("import sys\nprint('synthetic-private-output', file=sys.stderr)\nsys.exit(1)\n")
    atomic_config_write(operator_home / "config.yaml", {
        "profiles": {"provision_command": [sys.executable, str(script)]},
    })
    with pytest.raises(RuntimeError, match="not published") as exc:
        profiles.create_profile("research", no_alias=True)
    assert not profiles.get_profile_dir("research").exists()
    assert not list((operator_home / "profiles").glob(".research.staging-*"))
    assert "synthetic-private-output" not in str(exc.value) + str(capsys.readouterr())


def test_unconfigured_creation_stays_unchanged(operator_home):
    assert profiles.create_profile("research", no_alias=True).is_dir()


@pytest.mark.parametrize("policy", [
    {"provision_command": "echo unsafe"},
    {"provision_command": ["relative-executable"]},
    {"provision_command": [sys.executable], "provision_timeout": 0},
])
def test_invalid_policy_fails_before_publication(operator_home, policy):
    atomic_config_write(operator_home / "config.yaml", {"profiles": policy})
    with pytest.raises(ValueError):
        profiles.create_profile("research", no_alias=True)
    assert not profiles.get_profile_dir("research").exists()


def test_timeout_fails_closed(operator_home, tmp_path, monkeypatch):
    atomic_config_write(operator_home / "config.yaml", {
        "profiles": {"provision_command": [sys.executable], "provision_timeout": 1},
    })
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(profile_provisioning.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="not published"):
        profile_provisioning.provision_profile("research", tmp_path, tmp_path / "dest",
                                               operator_home, None)
