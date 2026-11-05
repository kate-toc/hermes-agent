# Thin downstream maintenance

The `kate/stable-v0.22.2` branch starts at upstream release commit
`d923a5eb487a17c0a68801bba9ef0f56c81040a8`. Upstream `main` remains an unmodified
tracking branch; do not merge it into stable just to move workflow files.

## Local patches

1. Trailing ASCII `:` requests continuation at any length. Existing caller gates
   and the shared two-nudge limit are unchanged. Punctuation is deliberately a
   heuristic: literal answers and requests for input ending in `:` also match.
2. An optional operator provisioner runs before atomic publication of a new profile.
   Third-party provisioning policy lives outside Hermes core.

The default home's `config.yaml` can opt in:

```yaml
profiles:
  provision_command: ["/absolute/path/to/python", "/absolute/path/to/provision.py"]
  provision_timeout: 60
```

The executable path must be absolute. No shell interpolation occurs. The command
receives schema-1 JSON on stdin with `name`, `staging_home`, `destination_home`,
`default_home` and nullable `source_home`. Its cwd and `HERMES_HOME` point to the
hidden staging directory. It must finish before the timeout (maximum 300 seconds).
Exit zero means provisioned; failure/timeout aborts creation and removes staging.
Output is discarded because provider setup may handle credentials. Do not put
credentials in argv. Existing profiles, imports and renames are not provisioned.

Provisioners must be idempotent. They may leave an external resource after an
interruption; retry should reconcile it, never delete someone else's resource.
Do not start profile services or publish staging inside the command. Use supported
plugin admission for dependencies, not runtime pip installs.

## Release gate

Routine CI uses standard GitHub-hosted runners and synthetic fixtures, without
model API keys, production state, LAN access or deployment credentials. Image
creation uses the upstream Dockerfile and canonical install-stamp writer. Only
downstream workflows are enabled; upstream publication and paid runners stay off.

New upstream releases prepare candidates, never replace production automatically.
Fetch tags, select an exact release commit, rebase the small commits, resolve
conflicts, and rerun regression and Docker integration tests. Review the source
SHA and resulting image digest. A clean rebase is not acceptance.

Promotion stays outside public CI: verify architecture and source identity; run
isolated smoke checks; quiesce writers; fully verify a consistent protected state
backup; preserve runtime config and secrets; deploy by immutable digest; verify
authentication, tools, supervision and state integrity. Keep the previous image
and compatible backup. Retire startup patching only after verifying the built-in
behavior. Never restore state over live writers.
