# Trigger evals

Checks that the skill loads for RedM/FiveM work and stays out of everything
else - the failure `claude plugin eval` most often finds is a description that
never gets picked. Four `trigger-*` cases must load the skill; three
`no-trigger-*` cases must not (including Roblox Lua, which is Lua but not CFX).
Each case has one `tool_used: Skill` grader scored in both arms, so the
with/without-plugin delta measures triggering directly.

This directory is separate from `evals/` (the planted-bug review benchmark), so
always pass `--eval-dir`:

```bash
claude plugin eval . --eval-dir trigger-evals                      # 7 cases x 3 runs x 2 arms
claude plugin eval . --eval-dir trigger-evals --case 'trigger-*' --runs 1   # quick check
```

Needs Claude Code 2.1.269 or later and your normal model credentials: every run
is a real model call billed to you, so the full suite is 42 runs. In CI add
`--trust-plugin --no-publish --json results.json --threshold 1.0` and pin
`--model`. Results land in `trigger-evals/results/` (git-ignored).
