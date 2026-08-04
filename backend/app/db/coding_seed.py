"""Coding problem seed catalog."""

from __future__ import annotations

from app.models import CodingProblem
from app.models.enums import DifficultyLevel

PROBLEMS: list[dict] = [
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "statement_md": (
            "Given an array of integers `nums` and an integer `target`, return the "
            "**indices** of the two numbers such that they add up to `target`.\n\n"
            "You may assume each input has exactly one solution, and you may not use "
            "the same element twice. Return the answer in any order.\n\n"
            "Implement `two_sum(nums: list[int], target: int) -> list[int]`."
        ),
        "difficulty": DifficultyLevel.EASY,
        "tags": ["array", "hashmap"],
        "company_tags": ["google", "amazon"],
        "starter_code": {
            "python": (
                "def two_sum(nums, target):\n"
                "    \"\"\"Return indices of the two numbers that add up to target.\"\"\"\n"
                "    pass\n"
            ),
            "javascript": (
                "function two_sum(nums, target) {\n"
                "  // Return indices of the two numbers that add up to target.\n"
                "  return [];\n"
                "}\n"
            ),
            "entry": "two_sum",
        },
        "public_tests": [
            {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
            {"args": [[3, 2, 4], 6], "expected": [1, 2]},
        ],
        "hidden_tests": [
            {"args": [[3, 3], 6], "expected": [0, 1]},
            {"args": [[10, 15, 1, 8], 9], "expected": [2, 3]},
        ],
    },
    {
        "slug": "valid-parentheses",
        "title": "Valid Parentheses",
        "statement_md": (
            "Given a string `s` containing just the characters `'('`, `')'`, `'{'`, "
            "`'}'`, `'['` and `']'`, determine if the input string is valid.\n\n"
            "An input string is valid if:\n"
            "1. Open brackets are closed by the same type of brackets.\n"
            "2. Open brackets are closed in the correct order.\n\n"
            "Implement `is_valid(s: str) -> bool`."
        ),
        "difficulty": DifficultyLevel.EASY,
        "tags": ["stack", "string"],
        "company_tags": ["meta", "microsoft"],
        "starter_code": {
            "python": (
                "def is_valid(s):\n"
                "    \"\"\"Return True if parentheses are valid.\"\"\"\n"
                "    pass\n"
            ),
            "javascript": (
                "function is_valid(s) {\n"
                "  // Return true if parentheses are valid.\n"
                "  return false;\n"
                "}\n"
            ),
            "entry": "is_valid",
        },
        "public_tests": [
            {"args": ["()"], "expected": True},
            {"args": ["()[]{}"], "expected": True},
            {"args": ["(]"], "expected": False},
        ],
        "hidden_tests": [
            {"args": ["([)]"], "expected": False},
            {"args": ["{[]}"], "expected": True},
        ],
    },
    {
        "slug": "max-profit",
        "title": "Best Time to Buy and Sell Stock",
        "statement_md": (
            "You are given an array `prices` where `prices[i]` is the price of a given "
            "stock on the `i`th day.\n\n"
            "You want to maximize your profit by choosing a single day to buy one stock "
            "and choosing a different day in the future to sell that stock.\n\n"
            "Return the maximum profit you can achieve. If you cannot achieve any profit, return `0`.\n\n"
            "Implement `max_profit(prices: list[int]) -> int`."
        ),
        "difficulty": DifficultyLevel.EASY,
        "tags": ["array", "greedy"],
        "company_tags": ["amazon", "bloomberg"],
        "starter_code": {
            "python": (
                "def max_profit(prices):\n"
                "    \"\"\"Return the maximum profit from one buy/sell.\"\"\"\n"
                "    pass\n"
            ),
            "javascript": (
                "function max_profit(prices) {\n"
                "  // Return the maximum profit from one buy/sell.\n"
                "  return 0;\n"
                "}\n"
            ),
            "entry": "max_profit",
        },
        "public_tests": [
            {"args": [[7, 1, 5, 3, 6, 4]], "expected": 5},
            {"args": [[7, 6, 4, 3, 1]], "expected": 0},
        ],
        "hidden_tests": [
            {"args": [[2, 4, 1]], "expected": 2},
            {"args": [[1]], "expected": 0},
        ],
    },
    {
        "slug": "merge-intervals",
        "title": "Merge Intervals",
        "statement_md": (
            "Given an array of `intervals` where `intervals[i] = [start_i, end_i]`, "
            "merge all overlapping intervals and return an array of the non-overlapping "
            "intervals that cover all the intervals in the input.\n\n"
            "Implement `merge(intervals: list[list[int]]) -> list[list[int]]`."
        ),
        "difficulty": DifficultyLevel.MEDIUM,
        "tags": ["array", "sorting"],
        "company_tags": ["google", "facebook"],
        "starter_code": {
            "python": (
                "def merge(intervals):\n"
                "    \"\"\"Merge overlapping intervals.\"\"\"\n"
                "    pass\n"
            ),
            "javascript": (
                "function merge(intervals) {\n"
                "  // Merge overlapping intervals.\n"
                "  return intervals;\n"
                "}\n"
            ),
            "entry": "merge",
        },
        "public_tests": [
            {"args": [[[1, 3], [2, 6], [8, 10], [15, 18]]], "expected": [[1, 6], [8, 10], [15, 18]]},
            {"args": [[[1, 4], [4, 5]]], "expected": [[1, 5]]},
        ],
        "hidden_tests": [
            {"args": [[[1, 4], [0, 4]]], "expected": [[0, 4]]},
            {"args": [[[1, 4], [2, 3]]], "expected": [[1, 4]]},
        ],
    },
]


def upsert_coding_problems(db) -> int:
    from sqlalchemy import select

    count = 0
    for spec in PROBLEMS:
        existing = db.scalar(select(CodingProblem).where(CodingProblem.slug == spec["slug"]))
        if existing:
            for key, value in spec.items():
                if key != "slug":
                    setattr(existing, key, value)
            db.add(existing)
        else:
            db.add(CodingProblem(**spec, is_published=True))
            count += 1
    db.flush()
    return count
