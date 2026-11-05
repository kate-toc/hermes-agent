"""Run an operator-configured provisioner before a profile becomes discoverable."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess


def provision_profile(name: str, staging: Path, destination: Path,
                      default_home: Path, source: Path | None) -> None:
    """Read policy from the default home, not the new profile or a clone.

    This is trusted operator code, not a model tool. JSON context travels on stdin;
    output is discarded because provisioning can handle credentials. Failure leaves
    only an unpublished staging tree, which create_profile's existing cleanup owns.
    """
    from hermes_cli.config_effective import load_user_config_effective

    config = load_user_config_effective(default_home / "config.yaml", fail_closed=True)
    policy = config.get("profiles", {})
    if not isinstance(policy, dict):
        raise ValueError("profiles must be a mapping")
    command = policy.get("provision_command", [])
    if command == []:
        return
    if (not isinstance(command, list) or not command
            or any(not isinstance(arg, str) or not arg or "\0" in arg for arg in command)
            or not Path(command[0]).is_absolute()):
        raise ValueError("profiles.provision_command must be an argv list with an absolute executable")
    timeout = policy.get("provision_timeout", 60)
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or not 0 < timeout <= 300):
        raise ValueError("profiles.provision_timeout must be greater than 0 and at most 300 seconds")
    context = {"schema": 1, "name": name, "staging_home": str(staging),
               "destination_home": str(destination), "default_home": str(default_home),
               "source_home": str(source) if source else None}
    try:
        result = subprocess.run(
            command, input=json.dumps(context), text=True, cwd=staging,
            env={**os.environ, "HERMES_HOME": str(staging)},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Profile provisioning could not complete; profile was not published") from None
    if result.returncode:
        raise RuntimeError("Profile provisioning failed; profile was not published")
