import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "workflow_metrics.py"
_spec = importlib.util.spec_from_file_location("workflow_metrics", SCRIPT)
workflow_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(workflow_metrics)


# SPEC 011, AC8: a cent is a fixed unit only while the table is never repriced, so the rows
# are pinned literally. Cents per million tokens: input, cache write 5 min, cache write 1 h,
# cache read, output.
def test_the_rate_table_is_dated_and_frozen():
    assert workflow_metrics.RATES_DATE == "2026-09-24"
    assert workflow_metrics.RATES == {
        "claude-opus-5-5": (400, 500, 800, 20, 2000),
        "claude-opus-5": (500, 625, 1000, 50, 2500),
        "claude-sonnet-5": (200, 250, 400, 20, 1000),
        "claude-haiku-4-5": (100, 125, 200, 10, 500),
        "claude-fable-5-1": (1000, 1250, 2000, 25, 5000),
    }
    source = SCRIPT.read_text()
    assert "never changed" in source
    assert "launch rates" in source


# SPEC 011, AC1: only the stage total is rounded.
def test_stage_cost_is_tokens_times_rates_rounded_once():
    # 200 output tokens on Opus 5.5 = 200 × 2000 = 400 000 → 0.4 cent; 400 output tokens on
    # Sonnet 5 = 400 × 1000 = 400 000 → 0.4 cent. Together 0.8 → 1, where rounding each
    # would give 0.
    assert (
        workflow_metrics.stage_cents(
            {"claude-opus-5-5": [0, 0, 0, 0, 200], "claude-sonnet-5": [0, 0, 0, 0, 400]}
        )
        == 1
    )
    # Sonnet 5, every type: 1000 × 200 + 2000 × 250 + 3000 × 400 + 100 000 × 20 + 5000 × 1000
    # = 200 000 + 500 000 + 1 200 000 + 2 000 000 + 5 000 000 = 8 900 000 → 8.9 → 9.
    assert workflow_metrics.stage_cents({"claude-sonnet-5": [1000, 2000, 3000, 100_000, 5000]}) == 9
    # Half up: 5000 × 100 = 500 000 → 0.5 → 1.
    assert workflow_metrics.stage_cents({"claude-haiku-4-5": [5000, 0, 0, 0, 0]}) == 1


def test_a_dated_model_id_finds_its_rate():
    assert workflow_metrics.rate_for("claude-haiku-4-5-20251001") == (100, 125, 200, 10, 500)
    assert workflow_metrics.rate_for("claude-opus-5-5") == (400, 500, 800, 20, 2000)
    assert workflow_metrics.rate_for("claude-nope-1") is None
    assert workflow_metrics.stage_cents({"claude-nope-1": [1, 0, 0, 0, 0]}) is None


def test_usage_without_the_ttl_split_counts_as_5m():
    older = {
        "input_tokens": 1,
        "cache_creation_input_tokens": 7,
        "cache_read_input_tokens": 3,
        "output_tokens": 4,
    }
    assert workflow_metrics.usage_tokens(older) == (1, 7, 0, 3, 4)
    split = dict(
        older, cache_creation={"ephemeral_5m_input_tokens": 2, "ephemeral_1h_input_tokens": 5}
    )
    assert workflow_metrics.usage_tokens(split) == (1, 2, 5, 3, 4)
