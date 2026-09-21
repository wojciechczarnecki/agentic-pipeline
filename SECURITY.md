# Security policy

## Supported version

Only the current release is supported: the one on the `stable` release channel, which is
the latest `pipeline--v*` tag (see [plugin/CHANGELOG.md](plugin/CHANGELOG.md)). A fix ships
as a new release on that channel; older tags are not patched.

## Reporting a vulnerability

Report it privately through GitHub private vulnerability reporting:
<https://github.com/wojciechczarnecki/agentic-pipeline/security/advisories/new>.
Please do not open a public issue for it. Include the plugin version, the command or the
input that shows the problem, and what you expected the plugin to do.

## The command guard

The command guard is best effort, not a sandbox: it reads the commands the agent runs through
Claude Code's Bash tool, as text, before they run, and some ways around it are known and documented in
[plugin/docs/GUARD.md](plugin/docs/GUARD.md#known-limits). A guard bypass counts as a
security report: a command the guard should refuse but lets through, beyond those known
limits, is a vulnerability — report it the same private way.
