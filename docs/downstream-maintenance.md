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

## GHCR release publication (authorized 2026-11-08)

After source review, dispatch `downstream.yml` on the reviewed downstream branch
with `release_tag` set to the exact upstream stable tag (for example `v0.23.0`).
An empty input or ordinary branch/PR CI is tests-only and has no publication job.
The workflow validates version and upstream ancestry, runs regressions and Docker
integration tests, archives the exact tested linux/amd64 image, then loads it in a
separate publication job. No publication rebuild occurs. The archive is retained
for seven days; GHCR is the durable release artifact.

Images: `ghcr.io/kate-toc/hermes-agent:<upstream-tag>`, the same version without
`v`, and `sha-<full-downstream-commit>`. Version tags are immutable: a differing
existing image fails closed. No moving latest/stable aliases are published.
The GitHub release `downstream/<upstream-tag>` points to our patched commit and
attaches `release.json` with the registry digest, image ID, source and CI run.
Inherited upstream Git tags remain untouched (they identify upstream source,
not the patched downstream image). Only the downstream workflow is enabled;
upstream publication and paid runners remain disabled.

Verify GHCR visibility and an anonymous pull by immutable digest before accepting
a release. Never substitute a local Docker image ID for the registry digest.
Image publication is not production promotion; all production gates above remain.
