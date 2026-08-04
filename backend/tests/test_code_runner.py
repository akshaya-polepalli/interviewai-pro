"""Unit tests for Python + JavaScript code runners."""

from __future__ import annotations

import shutil

import pytest

from app.models.enums import SubmissionStatus
from app.services.code_runner import (
    CodeSafetyError,
    run_javascript_function_tests,
    run_python_function_tests,
    validate_javascript_code,
    validate_user_code,
)


def test_two_sum_accepted() -> None:
    source = """
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        need = target - n
        if need in seen:
            return [seen[need], i]
        seen[n] = i
    return []
"""
    result = run_python_function_tests(
        source_code=source,
        entry="two_sum",
        public_tests=[{"args": [[2, 7, 11, 15], 9], "expected": [0, 1]}],
        hidden_tests=[{"args": [[3, 3], 6], "expected": [0, 1]}],
    )
    assert result.status == SubmissionStatus.ACCEPTED
    assert result.passed_tests == 2


def test_wrong_answer() -> None:
    source = "def two_sum(nums, target):\n    return [0, 0]\n"
    result = run_python_function_tests(
        source_code=source,
        entry="two_sum",
        public_tests=[{"args": [[2, 7], 9], "expected": [0, 1]}],
    )
    assert result.status == SubmissionStatus.WRONG_ANSWER


def test_blocks_os_import() -> None:
    try:
        validate_user_code("import os\ndef f():\n    return 1\n")
        assert False, "expected CodeSafetyError"
    except CodeSafetyError as exc:
        assert "os" in str(exc)


def test_blocks_eval() -> None:
    try:
        validate_user_code("def f(x):\n    return eval(x)\n")
        assert False, "expected CodeSafetyError"
    except CodeSafetyError:
        pass


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_javascript_two_sum_accepted() -> None:
    source = """
function two_sum(nums, target) {
  const seen = {};
  for (let i = 0; i < nums.length; i++) {
    const need = target - nums[i];
    if (need in seen) return [seen[need], i];
    seen[nums[i]] = i;
  }
  return [];
}
"""
    result = run_javascript_function_tests(
        source_code=source,
        entry="two_sum",
        public_tests=[{"args": [[2, 7, 11, 15], 9], "expected": [0, 1]}],
        hidden_tests=[{"args": [[3, 3], 6], "expected": [0, 1]}],
    )
    assert result.status == SubmissionStatus.ACCEPTED
    assert result.passed_tests == 2


def test_javascript_blocks_fs() -> None:
    try:
        validate_javascript_code("const fs = require('fs');\nfunction f(){ return 1 }\n")
        assert False, "expected CodeSafetyError"
    except CodeSafetyError:
        pass
