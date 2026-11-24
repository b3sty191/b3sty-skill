---
name: no-trigger-python-csv
description: skill must not load
tags: [trigger, negative]
runs: 3
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
---

Write a Python function that reads sales.csv and returns the sum of the third column, skipping the header row.
