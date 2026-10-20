---
name: milestone
description: Execute one milestone of the fork roadmap end to end (plan, implement, verify, review, PR). Invoke as /milestone M1.
disable-model-invocation: true
---

Execute milestone **$ARGUMENTS** of `docs/fork/ROADMAP.md`, autonomously, up to an open pull request.

## 1. Prepare
- Read `CLAUDE.md`, `docs/fork/SPEC.md`, `docs/fork/DESIGN.md`, the milestone section in `docs/fork/ROADMAP.md`,
  and the end of `docs/fork/PROGRESS.md` and `docs/fork/DECISIONS.md`.
- If a previous milestone's PR is still open and this milestone depends on it, branch from that PR's branch and say so in the PR.
  Otherwise: `git fetch origin && git switch -c fork/<m-id>-<slug> origin/main`.
- Check the environment: last line of `scripts/fork/verify.sh --quick` must be `VERIFY: OK` before you change anything.
  If it is not, fix the environment first and note it in PROGRESS.md.

## 2. Plan (write it down before coding)
- Use a subagent to map the code involved (components, stores, API endpoints) so your own context stays clean.
- Append to `docs/fork/PROGRESS.md` a section `## <m-id> — plan` with numbered sub-tasks, each small enough for one commit,
  each with how you will verify it. Commit the plan.

## 3. Implement, one sub-task at a time
- Implement, run `scripts/fork/verify.sh --quick`, fix until `VERIFY: OK`, commit (English message), tick the sub-task in PROGRESS.md.
- UI work: run `scripts/fork/verify.sh --quick --ui wip` and open the relevant screenshots yourself before moving on.
- Reversible product or design choice not covered by SPEC/DESIGN: decide, log it in `docs/fork/DECISIONS.md`, continue.
- Irreversible or out-of-scope choice: stop that sub-task, write the question at the top of PROGRESS.md, continue with
  the other sub-tasks, and list the question in the PR.
- Pages you redesigned: set `"strict": true` for them in `scripts/fork/ui/routes.json`.

## 4. Verify for real
- Full gate: `scripts/fork/verify.sh --ui <m-id> --publish` → must end with `VERIFY: OK`.
- Run the `reviewer` subagent on the diff for this milestone, then the `ui-auditor` subagent on label `<m-id>`
  (compare with `m0-baseline`). Fix every BLOCKER and every UI issue that is cheap to fix; list the rest in the PR.
  Do not chase every minor remark: correctness and the acceptance criteria come first.
- Re-run the full gate after fixes.

## 5. Deliver
- Tick the milestone's criteria in ROADMAP.md, add a short `## <m-id> — summary` to PROGRESS.md, commit, push the branch.
- Open a PR against `main` of the fork (never upstream). PR body, in French:
  - What changed (5 lines max) and what to test on the phone
  - Acceptance criteria with ✅ / ❌
  - Screenshots: embed `docs/fork/screens/<m-id>/<route>-mobile.jpg` for each touched page with
    `![route](https://github.com/<owner>/<repo>/blob/<branch>/docs/fork/screens/<m-id>/<file>?raw=true)`
    (owner/repo from `git remote get-url origin`), next to the `m0-baseline` version of the same page
  - Evidence: the final `verify.sh` summary lines
  - Decisions to validate (from DECISIONS.md) and open questions
- Stop after the PR is open. Do not start the next milestone unless the prompt explicitly asked for it.
