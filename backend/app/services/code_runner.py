"""
Restricted Python code runner for coding problems.

Safety model (MVP / Docker demo):
- AST pre-scan blocks dangerous imports and calls
- User code is written to a temp file and imported by a fixed harness
- Only a declared entry function is invoked with JSON-serialized args
- Hidden test expected/actual values are redacted by the service layer
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.models.enums import SubmissionStatus

logger = get_logger(__name__)

ALLOWED_IMPORT_ROOTS = {
    "math",
    "typing",
    "collections",
    "heapq",
    "functools",
    "itertools",
    "bisect",
    "re",
    "string",
    "dataclasses",
    "enum",
    "json",
    "copy",
    "decimal",
    "fractions",
    "statistics",
    "operator",
    "array",
}

BANNED_NAMES = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "breakpoint",
    "input",
    "memoryview",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
}

HARNESS = textwrap.dedent(
    """
    import importlib.util
    import json
    import sys
    from pathlib import Path

    entry = sys.argv[1]
    args = json.loads(sys.argv[2])
    user_path = Path(__file__).with_name("user_solution.py")

    spec = importlib.util.spec_from_file_location("user_solution", user_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(1)

    fn = getattr(mod, entry, None)
    if fn is None or not callable(fn):
        print(json.dumps({"ok": False, "error": f"Entry function '{entry}' not found"}))
        sys.exit(2)

    try:
        result = fn(*args)
        print(json.dumps({"ok": True, "result": result}))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        sys.exit(1)
    """
)

JS_HARNESS = textwrap.dedent(
    """
    const fs = require('fs');
    const path = require('path');
    const entry = process.argv[2];
    const args = JSON.parse(process.argv[3]);
    const userPath = path.join(__dirname, 'user_solution.js');
    let mod;
    try {
      mod = require(userPath);
    } catch (err) {
      console.log(JSON.stringify({ ok: false, error: String(err && err.message || err) }));
      process.exit(1);
    }
    const fn = mod[entry] || (typeof mod === 'function' ? mod : null);
    if (typeof fn !== 'function') {
      console.log(JSON.stringify({ ok: false, error: `Entry function '${entry}' not found` }));
      process.exit(2);
    }
    try {
      const result = fn(...args);
      console.log(JSON.stringify({ ok: true, result }));
    } catch (err) {
      console.log(JSON.stringify({ ok: false, error: String(err && err.message || err) }));
      process.exit(1);
    }
    """
)

JS_BANNED = (
    "require('child_process')",
    'require("child_process")',
    "require('fs')",
    'require("fs")',
    "require('net')",
    'require("net")',
    "require('http')",
    'require("http")',
    "require('https')",
    'require("https")',
    "process.exit",
    "eval(",
    "Function(",
    "WebAssembly",
)


def validate_javascript_code(source: str) -> None:
    lowered = source.replace(" ", "")
    for banned in JS_BANNED:
        token = banned.replace(" ", "")
        if token in lowered or banned in source:
            raise CodeSafetyError(f"JavaScript pattern not allowed: {banned}")


@dataclass
class CaseResult:
    test_index: int
    is_hidden: bool
    status: SubmissionStatus
    stdin: str | None = None
    expected_stdout: str | None = None
    actual_stdout: str | None = None
    stderr: str | None = None
    runtime_ms: int | None = None
    detail: dict[str, Any] | None = None


@dataclass
class RunSummary:
    status: SubmissionStatus
    verdict: str
    passed_tests: int
    total_tests: int
    score: float
    runtime_ms: int | None
    cases: list[CaseResult] = field(default_factory=list)
    compile_stderr: str | None = None


class CodeSafetyError(ValueError):
    pass


def validate_user_code(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise CodeSafetyError(f"Syntax error: {exc.msg} (line {exc.lineno})") from exc

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif node.module:
                names = [node.module.split(".")[0]]
            for root in names:
                if root not in ALLOWED_IMPORT_ROOTS:
                    raise CodeSafetyError(f"Import not allowed: {root}")
        if isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise CodeSafetyError(f"Use of '{node.id}' is not allowed")
        if isinstance(node, ast.Attribute) and node.attr in {
            "__class__",
            "__bases__",
            "__subclasses__",
            "__globals__",
            "__code__",
        }:
            raise CodeSafetyError(f"Access to '{node.attr}' is not allowed")


def _normalize(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, float):
        return round(value, 6)
    return value


def _values_equal(actual: Any, expected: Any) -> bool:
    return _normalize(actual) == _normalize(expected)


def run_python_function_tests(
    *,
    source_code: str,
    entry: str,
    public_tests: list[dict[str, Any]],
    hidden_tests: list[dict[str, Any]] | None = None,
    time_limit_ms: int = 2000,
) -> RunSummary:
    try:
        validate_user_code(source_code)
    except CodeSafetyError as exc:
        return RunSummary(
            status=SubmissionStatus.COMPILATION_ERROR,
            verdict="unsafe_or_syntax",
            passed_tests=0,
            total_tests=len(public_tests or []) + len(hidden_tests or []),
            score=0.0,
            runtime_ms=None,
            compile_stderr=str(exc),
        )

    cases_spec: list[tuple[int, bool, dict[str, Any]]] = []
    for i, case in enumerate(public_tests or []):
        cases_spec.append((i, False, case))
    offset = len(public_tests or [])
    for i, case in enumerate(hidden_tests or []):
        cases_spec.append((offset + i, True, case))

    if not cases_spec:
        return RunSummary(
            status=SubmissionStatus.SYSTEM_ERROR,
            verdict="no_tests",
            passed_tests=0,
            total_tests=0,
            score=0.0,
            runtime_ms=None,
            compile_stderr="Problem has no test cases",
        )

    results: list[CaseResult] = []
    passed = 0
    total_runtime = 0
    overall = SubmissionStatus.ACCEPTED

    for index, is_hidden, case in cases_spec:
        case_result = _run_single_case(
            source_code=source_code,
            entry=entry,
            args=case.get("args", []),
            expected=case.get("expected"),
            time_limit_ms=time_limit_ms,
            test_index=index,
            is_hidden=is_hidden,
        )
        results.append(case_result)
        if case_result.runtime_ms:
            total_runtime += case_result.runtime_ms
        if case_result.status == SubmissionStatus.ACCEPTED:
            passed += 1
        elif overall == SubmissionStatus.ACCEPTED:
            overall = case_result.status

    score = round((passed / len(cases_spec)) * 100, 2) if cases_spec else 0.0
    return RunSummary(
        status=overall,
        verdict=overall.value,
        passed_tests=passed,
        total_tests=len(cases_spec),
        score=score,
        runtime_ms=total_runtime or None,
        cases=results,
    )


def run_javascript_function_tests(
    *,
    source_code: str,
    entry: str,
    public_tests: list[dict[str, Any]],
    hidden_tests: list[dict[str, Any]] | None = None,
    time_limit_ms: int = 2000,
) -> RunSummary:
    try:
        validate_javascript_code(source_code)
    except CodeSafetyError as exc:
        return RunSummary(
            status=SubmissionStatus.COMPILATION_ERROR,
            verdict="unsafe_or_syntax",
            passed_tests=0,
            total_tests=len(public_tests or []) + len(hidden_tests or []),
            score=0.0,
            runtime_ms=None,
            compile_stderr=str(exc),
        )

    cases_spec: list[tuple[int, bool, dict[str, Any]]] = []
    for i, case in enumerate(public_tests or []):
        cases_spec.append((i, False, case))
    offset = len(public_tests or [])
    for i, case in enumerate(hidden_tests or []):
        cases_spec.append((offset + i, True, case))

    if not cases_spec:
        return RunSummary(
            status=SubmissionStatus.SYSTEM_ERROR,
            verdict="no_tests",
            passed_tests=0,
            total_tests=0,
            score=0.0,
            runtime_ms=None,
            compile_stderr="Problem has no test cases",
        )

    results: list[CaseResult] = []
    passed = 0
    total_runtime = 0
    overall = SubmissionStatus.ACCEPTED

    for index, is_hidden, case in cases_spec:
        case_result = _run_single_js_case(
            source_code=source_code,
            entry=entry,
            args=case.get("args", []),
            expected=case.get("expected"),
            time_limit_ms=time_limit_ms,
            test_index=index,
            is_hidden=is_hidden,
        )
        results.append(case_result)
        if case_result.runtime_ms:
            total_runtime += case_result.runtime_ms
        if case_result.status == SubmissionStatus.ACCEPTED:
            passed += 1
        elif overall == SubmissionStatus.ACCEPTED:
            overall = case_result.status

    score = round((passed / len(cases_spec)) * 100, 2) if cases_spec else 0.0
    return RunSummary(
        status=overall,
        verdict=overall.value,
        passed_tests=passed,
        total_tests=len(cases_spec),
        score=score,
        runtime_ms=total_runtime or None,
        cases=results,
    )


def _run_single_js_case(
    *,
    source_code: str,
    entry: str,
    args: list[Any],
    expected: Any,
    time_limit_ms: int,
    test_index: int,
    is_hidden: bool,
) -> CaseResult:
    timeout_s = max(0.2, time_limit_ms / 1000.0)
    with tempfile.TemporaryDirectory(prefix="ivcodejs_") as tmp:
        tmp_path = Path(tmp)
        # Export CommonJS style so harness can require the file.
        wrapped = source_code
        if "module.exports" not in source_code and "exports." not in source_code:
            wrapped = (
                source_code.rstrip()
                + f"\nmodule.exports = {{ {entry}: typeof {entry} !== 'undefined' ? {entry} : undefined }};\n"
            )
        (tmp_path / "user_solution.js").write_text(wrapped, encoding="utf-8")
        (tmp_path / "harness.js").write_text(JS_HARNESS, encoding="utf-8")
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                ["node", "--no-warnings", str(tmp_path / "harness.js"), entry, json.dumps(args)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=tmp,
                check=False,
            )
        except FileNotFoundError:
            return CaseResult(
                test_index=test_index,
                is_hidden=is_hidden,
                status=SubmissionStatus.SYSTEM_ERROR,
                stderr="Node.js is not installed in this environment",
                runtime_ms=None,
            )
        except subprocess.TimeoutExpired:
            return CaseResult(
                test_index=test_index,
                is_hidden=is_hidden,
                status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
                expected_stdout=None if is_hidden else json.dumps(expected),
                stderr="Time limit exceeded",
                runtime_ms=time_limit_ms,
            )
        runtime_ms = max(1, int((time.perf_counter() - started) * 1000))

    stderr = (proc.stderr or "").strip() or None
    raw_out = (proc.stdout or "").strip()
    if not raw_out:
        return CaseResult(
            test_index=test_index,
            is_hidden=is_hidden,
            status=SubmissionStatus.RUNTIME_ERROR,
            expected_stdout=None if is_hidden else json.dumps(expected),
            stderr=stderr or "No output from runner",
            runtime_ms=runtime_ms,
        )
    try:
        payload = json.loads(raw_out.splitlines()[-1])
    except json.JSONDecodeError:
        return CaseResult(
            test_index=test_index,
            is_hidden=is_hidden,
            status=SubmissionStatus.RUNTIME_ERROR,
            expected_stdout=None if is_hidden else json.dumps(expected),
            actual_stdout=raw_out,
            stderr=stderr or "Invalid runner output",
            runtime_ms=runtime_ms,
        )
    if not payload.get("ok"):
        status = (
            SubmissionStatus.COMPILATION_ERROR
            if proc.returncode == 2
            else SubmissionStatus.RUNTIME_ERROR
        )
        return CaseResult(
            test_index=test_index,
            is_hidden=is_hidden,
            status=status,
            expected_stdout=None if is_hidden else json.dumps(expected),
            stderr=str(payload.get("error") or stderr or "Runtime error"),
            runtime_ms=runtime_ms,
        )
    actual = payload.get("result")
    ok = _values_equal(actual, expected)
    return CaseResult(
        test_index=test_index,
        is_hidden=is_hidden,
        status=SubmissionStatus.ACCEPTED if ok else SubmissionStatus.WRONG_ANSWER,
        expected_stdout=None if is_hidden else json.dumps(expected),
        actual_stdout=None if is_hidden else json.dumps(actual),
        stderr=None if (ok or is_hidden) else "Wrong answer",
        runtime_ms=runtime_ms,
    )


def _run_single_case(
    *,
    source_code: str,
    entry: str,
    args: list[Any],
    expected: Any,
    time_limit_ms: int,
    test_index: int,
    is_hidden: bool,
) -> CaseResult:
    timeout_s = max(0.2, time_limit_ms / 1000.0)
    with tempfile.TemporaryDirectory(prefix="ivcode_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "user_solution.py").write_text(source_code, encoding="utf-8")
        (tmp_path / "harness.py").write_text(HARNESS, encoding="utf-8")
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(tmp_path / "harness.py"), entry, json.dumps(args)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=tmp,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CaseResult(
                test_index=test_index,
                is_hidden=is_hidden,
                status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
                expected_stdout=None if is_hidden else json.dumps(expected),
                stderr="Time limit exceeded",
                runtime_ms=time_limit_ms,
            )
        runtime_ms = max(1, int((time.perf_counter() - started) * 1000))

    stderr = (proc.stderr or "").strip() or None
    raw_out = (proc.stdout or "").strip()

    if not raw_out:
        return CaseResult(
            test_index=test_index,
            is_hidden=is_hidden,
            status=SubmissionStatus.RUNTIME_ERROR,
            expected_stdout=None if is_hidden else json.dumps(expected),
            stderr=stderr or "No output from runner",
            runtime_ms=runtime_ms,
        )

    try:
        payload = json.loads(raw_out.splitlines()[-1])
    except json.JSONDecodeError:
        return CaseResult(
            test_index=test_index,
            is_hidden=is_hidden,
            status=SubmissionStatus.RUNTIME_ERROR,
            expected_stdout=None if is_hidden else json.dumps(expected),
            actual_stdout=raw_out,
            stderr=stderr or "Invalid runner output",
            runtime_ms=runtime_ms,
        )

    if not payload.get("ok"):
        status = (
            SubmissionStatus.COMPILATION_ERROR
            if proc.returncode == 2
            else SubmissionStatus.RUNTIME_ERROR
        )
        return CaseResult(
            test_index=test_index,
            is_hidden=is_hidden,
            status=status,
            expected_stdout=None if is_hidden else json.dumps(expected),
            stderr=str(payload.get("error") or stderr or "Runtime error"),
            runtime_ms=runtime_ms,
        )

    actual = payload.get("result")
    ok = _values_equal(actual, expected)
    return CaseResult(
        test_index=test_index,
        is_hidden=is_hidden,
        status=SubmissionStatus.ACCEPTED if ok else SubmissionStatus.WRONG_ANSWER,
        expected_stdout=None if is_hidden else json.dumps(expected),
        actual_stdout=None if is_hidden else json.dumps(actual),
        stderr=None if (ok or is_hidden) else "Wrong answer",
        runtime_ms=runtime_ms,
    )
