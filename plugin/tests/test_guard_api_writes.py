import pytest
from test_guard import WORKFLOW, evaluate, git, make_repo


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    repo = make_repo(tmp_path_factory.mktemp("api") / "repo", WORKFLOW)
    git(repo, "switch", "-C", "feat/001-x")
    return repo


VERBATIM = [
    ("gh api -X PATCH repos/o/r -f default_branch=x", "repos/o/r"),
    ("gh api -X PATCH repos/o/r -f visibility=public", "repos/o/r"),
    ("gh api -X PUT repos/o/r/topics", "repos/o/r/topics"),
    ("gh api -X POST repos/o/r/transfer", "repos/o/r/transfer"),
    ("gh api -f name=x repos/o/r", "repos/o/r"),
    ("gh api -X PATCH repos/{owner}/{repo} -f visibility=public", "repos/{owner}/{repo}"),
]

OWNER_GROUND = [
    "repos/o/r",
    "repositories/1",
    "orgs/o",
    "repos/o/r/topics",
    "repos/o/r/transfer",
    "repos/o/r/actions/secrets/T",
    "repos/o/r/actions/variables/V",
    "repos/o/r/environments/prod",
    "repos/o/r/hooks",
    "repos/o/r/keys",
    "repos/o/r/collaborators/u",
    "repos/o/r/invitations/1",
    "repos/o/r/pages",
    "repos/o/r/vulnerability-alerts",
    "repos/o/r/private-vulnerability-reporting",
    "repos/o/r/actions/permissions",
    "repos/o/r/rulesets",
    "repos/o/r/branches/main/protection",
    "orgs/o/teams",
    "orgs/o/members/u",
    "orgs/o/actions/secrets/T",
    "repositories/1/actions/secrets/T",
]

METHODS = ["-X POST", "--method PUT", "-XPATCH", "--method=patch"]


@pytest.mark.parametrize("command, endpoint", VERBATIM)
def test_the_acceptance_examples_are_refused(repo, command, endpoint):
    reason = evaluate(command, repo)
    assert reason is not None, command
    assert "owner's call" in reason and endpoint in reason, reason


@pytest.mark.parametrize("endpoint", OWNER_GROUND)
@pytest.mark.parametrize("method", METHODS)
def test_a_write_on_the_owners_ground_is_refused(repo, endpoint, method):
    reason = evaluate(f"gh api {method} {endpoint} -f x=y", repo)
    assert reason is not None, endpoint
    assert "owner's call" in reason and endpoint in reason, reason


@pytest.mark.parametrize("endpoint", OWNER_GROUND)
@pytest.mark.parametrize("method", ["", "-X GET ", "--method get "])
def test_reads_of_the_owners_ground_pass(repo, endpoint, method):
    assert evaluate(f"gh api {method}{endpoint}", repo) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh api -X POST repos/o/r/actions/runs/1/rerun",
        "gh api -X POST repos/o/r/issues/1/comments -f body=x",
        "gh api -X POST repos/o/r/issues/1/comments -f body='see the secrets page'",
        "gh api -X PATCH repos/o/r/pulls/1 -f title=x",
        "gh api -X POST repos/o/r/labels -f name=x",
        "gh api -X POST repos/o/r/issues -f title=x",
        "gh api -X POST repos/o/r/releases -f tag_name=v1",
        "gh api -X POST repos/o/r/deployments -f ref=x",
        "gh api -X POST repos/o/pages/issues/1/comments -f body=x",
        "gh api -X POST repos/hooks/r/labels -f name=x",
        "gh api -X PATCH repos/o/r/git/refs/heads/fix/hooks -f sha=x",
        "gh api -X POST repos/{owner}/{repo}/issues/1/comments -f body=x",
        "gh api repos/o/r/issues/1/comments -f body=x",
        "gh api -H 'Accept: application/json' -X POST repos/o/r/issues/1/comments -f body=x",
    ],
)
def test_ordinary_writes_and_reads_pass(repo, command):
    assert evaluate(command, repo) is None


@pytest.mark.parametrize(
    "command",
    [
        'gh api -X PATCH "$EP" -f x=y',
        "gh api -X POST repos/o/${R}/topics",
        "gh api -f name=x repos/o/$(echo r)",
        "gh api -X $M repos/o/r",
    ],
)
def test_a_write_on_a_variable_endpoint_is_refused(repo, command):
    reason = evaluate(command, repo)
    assert reason is not None, command
    assert "built from variables" in reason, reason
