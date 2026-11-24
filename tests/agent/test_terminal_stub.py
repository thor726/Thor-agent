"""Terminal stubs keep the decoded output lines and the last non-empty line.

Ported from upstream ``tests/agent/test_tool_result_stub_text.py`` (terminal cases only):
``agent.context_compressor_prune.terminal_stub`` wired through ``_sum_terminal``.
"""

import json

from agent.context_compressor import _PRUNE_MIN_CHARS, _summarize_tool_result


def _summary(name, args, body):
    return _summarize_tool_result(name, json.dumps(args), body)


def test_failing_terminal_uses_decoded_lines_and_last_nonempty_line():
    last = "FAILED tests/test_example.py::test_x - AssertionError"
    output = "\n".join([f"progress {i}" for i in range(37)] + [last]) + "\n"
    body = json.dumps({"output": output, "exit_code": 1})
    assert _summary("terminal", {"command": "pytest tests/test_example.py -q"}, body) == (
        "[terminal] ran `pytest tests/test_example.py -q` -> exit 1, 38 lines output | last: " + last)


def test_terminal_stub_stays_under_the_prune_floor():
    """A stub at or over the floor would be summarised again by a later pass and lose its exit code."""
    body = json.dumps({"output": "ERROR " + "y" * 300, "exit_code": 127})
    stub = _summary("terminal", {"command": "c" * 200}, body)
    assert len(stub) < _PRUNE_MIN_CHARS
    assert "-> exit 127, 1 line output | last: ERROR yyy" in stub
