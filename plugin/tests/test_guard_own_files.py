from pathlib import Path

import pytest
from test_guard import BIN, WORKFLOW, evaluate, git, make_repo

GUARDRAIL = "guardrail files"


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    repo = make_repo(tmp_path_factory.mktemp("own") / "repo", WORKFLOW)
    git(repo, "switch", "-C", "feat/001-x")
    return repo


@pytest.fixture
def plugin(tmp_path):
    root = tmp_path / "cache" / "pipeline"
    (root / "bin").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / "templates" / "docs").mkdir(parents=True)
    (root / "bin" / "guard.py").write_text("# guard\n")
    (root / "hooks" / "hooks.json").write_text("{}\n")
    (root / "templates" / "pre-push").write_text("#!/bin/sh\n")
    (root / "templates" / "x").write_text("x\n")
    (tmp_path / "x").write_text("x\n")
    (tmp_path / "y").write_text("y\n")
    config = tmp_path / "config" / "plugins"
    config.mkdir(parents=True)
    (config / "installed_plugins.json").write_text('{"plugins": {}}')
    (config / "known_marketplaces.json").write_text("{}")
    return root


def env_for(plugin: Path) -> dict[str, str]:
    return {
        "CLAUDE_PLUGIN_ROOT": str(plugin),
        "CLAUDE_CONFIG_DIR": str(plugin.parents[1] / "config"),
    }


WRITES = [
    "sed -i 's/a/b/' {}",
    "perl -i -pe 's/a/b/' {}",
    "tee {}",
    "mv /dev/null {}",
    "cp /dev/null {}",
    "truncate -s 0 {}",
    "chmod -x {}",
    "ln -sf /dev/null {}",
    "echo x > {}",
    "echo x >> {}",
    "git checkout -- {}",
    "git restore {}",
]


@pytest.mark.parametrize("relative", ["bin/guard.py", "hooks/hooks.json"])
@pytest.mark.parametrize("shape", WRITES)
def test_writing_the_plugin_directory_is_refused(repo, plugin, shape, relative):
    reason = evaluate(shape.format(plugin / relative), repo, **env_for(plugin))
    assert reason is not None, shape
    assert GUARDRAIL in reason, reason


@pytest.mark.parametrize(
    "shape",
    [
        "cd {root} && sed -i s/a/b/ bin/guard.py",
        "P={root}; tee $P/bin/guard.py",
        "cp /dev/null {root}/bin/*",
        "mv {root}/.. /tmp/x",
        "cp x {root}/bin/guard.py",
        "cp -t {root}/bin x",
        "install -m 755 x {root}/bin/guard",
        "ln -sf /dev/null {root}/bin/guard.py",
        "dd if=/dev/null of={root}/bin/guard.py",
        "cp x {root}/bin/guard.py 2>/dev/null",
        "echo x > {root}/bin/new-file",
        "cp x {root}/bin/{{a,b}}",
        "sed -i s/a/b/ {root}/../pipeline/bin/guard.py",
    ],
)
def test_other_write_shapes_on_the_plugin_directory_are_refused(repo, plugin, shape):
    reason = evaluate(shape.format(root=plugin), repo, **env_for(plugin))
    assert reason is not None, shape
    assert GUARDRAIL in reason, reason


@pytest.mark.parametrize(
    "shape",
    [
        "cat {root}/bin/guard.py",
        "grep -n x {root}/bin/guard.py",
        "sed -n 1p {root}/bin/guard.py",
        "cp {tmp}/x {tmp}/y",
        "diff {tmp}/x {tmp}/y",
    ],
)
def test_reading_the_plugin_directory_passes(repo, plugin, shape):
    command = shape.format(root=plugin, tmp=plugin.parents[1])
    assert evaluate(command, repo, **env_for(plugin)) is None


@pytest.mark.parametrize(
    "shape",
    [
        "cp {root}/templates/pre-push scripts/git-hooks/pre-commit",
        "cp -r {root}/templates/docs docs",
        "cp $CLAUDE_PLUGIN_ROOT/templates/x y",
        "cp ${{CLAUDE_PLUGIN_ROOT}}/templates/x y",
        "cat {root}/templates/x > y",
        "ln -s {root}/bin/guard.py {tmp}/link",
    ],
)
def test_copying_out_of_the_plugin_passes(repo, plugin, shape):
    command = shape.format(root=plugin, tmp=plugin.parents[1])
    assert evaluate(command, repo, **env_for(plugin)) is None


@pytest.mark.parametrize(
    "shape",
    ["cd {root} && ls 2>&1", "cd {root} && git status >&2", "cd {root} && cat x 2>/dev/null"],
)
def test_descriptor_redirects_inside_the_plugin_pass(repo, plugin, shape):
    assert evaluate(shape.format(root=plugin), repo, **env_for(plugin)) is None


def test_the_running_guards_own_directory_is_guarded(repo, tmp_path):
    # evaluated, never run
    reason = evaluate(f"sed -i s/a/b/ {BIN / 'guard.py'}", repo, CLAUDE_CONFIG_DIR=str(tmp_path))
    assert reason is not None
    assert GUARDRAIL in reason, reason


def test_a_plugin_dir_clone_inside_the_project_is_guarded(tmp_path):
    project = make_repo(tmp_path / "clone", WORKFLOW)
    git(project, "switch", "-C", "feat/001-x")
    (project / "plugin" / "bin").mkdir(parents=True)
    (project / "plugin" / "bin" / "guard.py").write_text("# guard\n")
    env = {"CLAUDE_PLUGIN_ROOT": str(project / "plugin"), "CLAUDE_CONFIG_DIR": str(tmp_path)}
    reason = evaluate("sed -i s/a/b/ plugin/bin/guard.py", project, **env)
    assert reason is not None
    assert GUARDRAIL in reason, reason
    assert evaluate("sed -i s/a/b/ backend/app.py", project, **env) is None


@pytest.mark.parametrize("name", ["installed_plugins.json", "known_marketplaces.json"])
@pytest.mark.parametrize("shape", WRITES[:10])
def test_writing_the_install_state_is_refused(repo, plugin, shape, name):
    env = env_for(plugin)
    for path in [
        f"{env['CLAUDE_CONFIG_DIR']}/plugins/{name}",
        f"$CLAUDE_CONFIG_DIR/plugins/{name}",
    ]:
        reason = evaluate(shape.format(path), repo, **env)
        assert reason is not None, shape.format(path)
        assert GUARDRAIL in reason, reason


@pytest.mark.parametrize("name", ["installed_plugins.json", "known_marketplaces.json"])
@pytest.mark.parametrize("shape", ["cat {}", "grep -n x {}", "python3 -m json.tool {}"])
def test_reading_the_install_state_passes(repo, plugin, shape, name):
    env = env_for(plugin)
    path = f"{env['CLAUDE_CONFIG_DIR']}/plugins/{name}"
    assert evaluate(shape.format(path), repo, **env) is None


def test_guard_md_covers_the_0_4_0_rules():
    text = (BIN.parent / "docs" / "GUARD.md").read_text()
    for token in ["protectedBranches", "installed_plugins.json", "gh api graphql", "nested"]:
        assert token in text, token
    assert "Only `main` and `master`" not in text


# End-to-end check 6 of PLAN 005: in a --plugin-dir session with the clone inside the
# project, copying a template out of the plugin is a read for the 0.3.4 pattern too.
def test_copying_out_of_a_plugin_dir_clone_inside_the_project_passes(tmp_path):
    project = make_repo(tmp_path / "clone-copy", WORKFLOW)
    git(project, "switch", "-C", "feat/001-x")
    (project / "plugin" / "templates").mkdir(parents=True)
    (project / "plugin" / "templates" / "pre-push").write_text("#!/bin/sh\n")
    env = {"CLAUDE_PLUGIN_ROOT": str(project / "plugin"), "CLAUDE_CONFIG_DIR": str(tmp_path)}
    assert evaluate("cp plugin/templates/pre-push /tmp/pre-push-copy", project, **env) is None
    assert evaluate("cp -r plugin/templates docs/x", project, **env) is None
    for command in [
        "cp /dev/null plugin/templates/pre-push",
        "cp -t plugin/templates x",
        "cp .claude/settings.json /tmp/x",
    ]:
        reason = evaluate(command, project, **env)
        assert reason is not None, command
        assert GUARDRAIL in reason, reason
