import json

import pytest
from test_guard import (
    ALLOWED_ANYWHERE,
    BLOCKED_ANYWHERE,
    WORKFLOW,
    evaluate,
    git,
    make_repo,
    run_hook,
)

CHANNELS = {**WORKFLOW, "protectedBranches": ["stable"]}


@pytest.fixture(scope="module")
def channel_repo(tmp_path_factory):
    repo = make_repo(tmp_path_factory.mktemp("channels") / "repo", CHANNELS)
    git(repo, "branch", "stable")
    git(repo, "branch", "stable-next")
    return repo


@pytest.fixture
def on_feature(channel_repo):
    git(channel_repo, "switch", "-C", "feat/001-x")
    return channel_repo


@pytest.fixture
def on_stable(channel_repo):
    git(channel_repo, "switch", "stable")
    return channel_repo


REFUSED_ON_A_FEATURE_BRANCH = [
    "git push origin HEAD:stable",
    "git push origin feat/x:refs/heads/stable",
    "git push -u origin stable",
    "B=stable; git push origin $B",
    "git branch -D stable",
    "git update-ref refs/heads/stable HEAD",
    "gh api -X PATCH repos/o/r/git/refs/heads/stable -f sha=x",
    "gh api repos/o/r/git/refs/heads/stable -f sha=x",
    "gh api -X POST repos/o/r/git/refs -f ref=refs/heads/stable -f sha=x",
    "gh api -X POST repos/o/r/branches/stable/rename -f new_name=x",
    "gh api -X PUT repos/o/r/branches/stable/protection",
    "gh api -X PUT repos/o/r/contents/x -f branch=stable -f message=m -f content=Yg==",
    "gh api -X DELETE repos/o/r/contents/x -f branch=stable -f message=m -f sha=x",
    "gh api repos/o/r/merge-upstream -fbranch=stable",
]

REFUSED_ON_STABLE = [
    "git push",
    "git commit -m x",
    "git merge feat/001-x",
    "git rebase feat/001-x",
    "git pull",
]


@pytest.mark.parametrize("command", REFUSED_ON_A_FEATURE_BRANCH)
def test_a_configured_branch_is_guarded_like_main(on_feature, command):
    reason = evaluate(command, on_feature)
    assert reason is not None, command
    assert "stable" in reason, reason


@pytest.mark.parametrize("command", REFUSED_ON_STABLE)
def test_a_configured_branch_is_guarded_like_main_while_on_it(on_stable, command):
    reason = evaluate(command, on_stable)
    assert reason is not None, command
    assert "stable" in reason, reason


def test_work_around_a_configured_branch_passes(channel_repo):
    git(channel_repo, "switch", "-C", "feat/001-x")
    assert evaluate("git push origin feat/x", channel_repo) is None
    git(channel_repo, "switch", "stable")
    assert evaluate("git pull --ff-only", channel_repo) is None
    assert evaluate("git switch -c feat/y", channel_repo) is None


def test_main_stays_protected(on_feature):
    reason = evaluate("git push origin HEAD:main", on_feature)
    assert reason is not None
    assert "pushing to main" in reason, reason


def test_the_refusal_names_the_configured_branch(channel_repo):
    git(channel_repo, "switch", "-C", "feat/001-x")
    reasons = [
        evaluate("git push origin HEAD:stable", channel_repo),
        evaluate("git branch -D stable", channel_repo),
        evaluate("git update-ref refs/heads/stable HEAD", channel_repo),
        evaluate("gh api -X PATCH repos/o/r/git/refs/heads/stable -f sha=x", channel_repo),
    ]
    git(channel_repo, "switch", "stable")
    reasons += [
        evaluate("git pull", channel_repo),
        evaluate("git commit -m x", channel_repo),
        evaluate("git push", channel_repo),
    ]
    joined = "\n".join(reason or "" for reason in reasons)
    assert all(reasons), reasons
    for fragment in [
        "pushing to stable",
        "on stable only",
        "resetting stable",
        "`git commit` on stable",
        "protectedBranches",
    ]:
        assert fragment in joined, joined
    assert "main" not in joined, joined


@pytest.mark.parametrize(
    "command",
    [
        "git push origin stable-next",
        "git push origin feat/stable",
        "git branch -D stable-next",
        "gh api -X PATCH repos/o/r/git/refs/heads/stable-next -f sha=x",
        "gh api -X POST repos/o/r/branches/stable-next/rename -f new_name=x",
        "gh api -X PUT repos/o/r/contents/x -f branch=stable-next -f message=m",
        "gh api -X PUT repos/o/r/contents/stable -f branch=feat/x -f message=m",
        "gh api repos/o/r/git/refs/heads/stable",
        "gh api repos/o/r/branches/stable",
        "gh api -X GET repos/o/r/contents/x -f ref=stable",
    ],
)
def test_names_match_exactly(on_feature, command):
    assert evaluate(command, on_feature) is None


def test_a_commit_on_a_similarly_named_branch_passes(channel_repo):
    git(channel_repo, "switch", "stable-next")
    assert evaluate("git commit -m x", channel_repo) is None


@pytest.fixture(scope="module")
def empty_list_repo(tmp_path_factory):
    repo = make_repo(
        tmp_path_factory.mktemp("empty") / "repo", {**WORKFLOW, "protectedBranches": []}
    )
    git(repo, "switch", "-C", "feat/001-x")
    return repo


@pytest.mark.parametrize("command, fragment", BLOCKED_ANYWHERE)
def test_an_empty_list_decides_like_0_3_4_on_refusals(empty_list_repo, command, fragment):
    reason = evaluate(command, empty_list_repo)
    assert reason is not None, command
    assert fragment in reason, reason


@pytest.mark.parametrize("command", ALLOWED_ANYWHERE)
def test_an_empty_list_decides_like_0_3_4_on_passes(empty_list_repo, command):
    assert evaluate(command, empty_list_repo) is None


def test_an_empty_name_does_not_protect_a_detached_head(tmp_path):
    repo = make_repo(tmp_path / "detached", {"protectedBranches": [""]})
    git(repo, "switch", "--detach", "HEAD")
    assert evaluate("git commit --allow-empty -m x", repo) is None
    assert evaluate("git push origin HEAD:feat/x", repo) is None


def test_an_invalid_value_falls_back_for_that_key_only(tmp_path):
    repo = make_repo(tmp_path / "invalid", {**WORKFLOW, "protectedBranches": "stable"})
    git(repo, "switch", "-C", "feat/001-x")
    assert evaluate("git push origin HEAD:stable", repo) is None
    assert "pushing to main" in (evaluate("git push origin HEAD:main", repo) or "")
    assert evaluate("curl https://api.example.com", repo) is not None
    payload = json.dumps({"tool_input": {"command": "git status"}, "cwd": str(repo)})
    result = run_hook(payload, repo)
    assert result.returncode == 0
    assert "`protectedBranches` has to be list" in result.stderr
