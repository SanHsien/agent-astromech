# agent-astromech 🤖

> A Windows-first maintenance release derived from [`tingyulu/MyR2D2`](https://github.com/tingyulu/MyR2D2). See [FORK.md](FORK.md) for attribution and synchronization, and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the development entrypoints.

### Your everyday astromech droid — a Claude skillset (zh-TW body, bilingual triggers)

**[繁體中文 (primary)](README.md) | English (this page)**

---

An astromech droid was never the protagonist, but every mission runs on it: securing mission plans, quietly fixing the ship from the socket, fighting memory loss, and managing workflow power.

That's agent-astromech's job description — 14 skills covering things that "won't kill you if skipped, but keep the whole workflow alive when done":

| Skill | One-liner | Astromech parallel |
|---|---|---|
| **save-all** | Before wrap-up/reboot: land everything that lives only in the conversation, and **verify** it hit disk | Plans stored in core, escape pod away |
| **dropoff** | Write a task + full context into a handoff card for another session; rings the doorbell if the target session is live | Recording the distress call and handoff card |
| **pickup** | New session fetches the cards (or gets doorbell-woken), reads in full, claims, starts, reports back when done | Finds the recipient, plays the hologram |
| **recap** | When too many parallel sessions blur together: refresh whatever may have gone stale, then report goal / evidence / blocker / next steps | The hologram isn't a memory — it's the current coordinates, read live off the system |
| **mission-log** | Zero-token harvest of any day's session activity (the transcripts were always recording — you just need a reader) | The flight recorder never sleeps |
| **daily-debrief** | Daily wrap-up: what happened + reflection, landed before transcripts evaporate (30-day retention) | The post-mission debrief |
| **weekly-debrief** | Weekly wrap-up: 7 dailies condensed into storylines and trends | Campaigns reveal supply-line problems; single sorties don't |
| **new-mission** | Kickoff brief: look first, ask at most five questions, draft the plan, review it, wait for an explicit "go" — mint a reusable task prompt on the way, and close with a wrap-up report against the plan | Projects the mission plans; the squadron flies the trench only after the briefing |
| **damage-report** | Five wrap-up questions run against the original ask before you report; the suggestions field says "none" when there's nothing real | Ship repaired, astromech runs diagnostics and reports damage — without waiting to be asked |
| **blind-review** | Hand the change to a subagent that **never saw the conversation** to attack it; the main agent adds the assumptions and design decisions, and out comes a briefing for a human | Plugged into the port with no mission briefing — reading the light that is actually lit |
| **ai-review** | Send the work to **another model** for a second opinion, digest it, then write the report; says "self-review only" when no backend is there | Bickering with a different model — each covering the other's blind half |
| **ai-search** | Ask once, get a **cited, checkable** live answer; says "not found" instead of filling from stale training data | Jacks into an external terminal — reading live station data, not stale intel from memory |
| **token-optimizer** | Iron rules before multi-agent dispatch: model tiering, compressed reporting, stop after 3 failures | Power allocation — don't let shields drain the engines |
| **flight-to-calendar** | Booked flights → Google Calendar: timezone-correct, one leg per event, sunset seats | Navigation — the astromech's actual day job |

## How this pack gets built

Claude sessions are **amnesiac**: close the conversation and everything not written to disk evaporates. The common theme here is fighting that amnesia — every skill in the table covers one link of the amnesia chain. All of it was iterated out of real daily-driver usage, not theory.

The development process eats the same rules: **before every release, the work goes to a different model family for review** (asking the same model to "check again" mostly re-confirms what it already believed). `ai-review` itself was built this way — three rounds of cross-model review caught 21 defects, 13 of which were introduced by the previous round's own fixes, and 46 regression tests ship in the box. All of it is checkable: method and evidence in [docs/TEST_PLAN.md](docs/TEST_PLAN.md), maintained-fork fixes in [Releases](https://github.com/SanHsien/agent-astromech/releases).

## Compatibility matrix

Start here — check which skills your tool can run:

| Skill | Claude Code CLI | Cowork / claude.ai | Gemini CLI | Codex CLI | ChatGPT (manual paste only) |
|---|---|---|---|---|---|
| save-all | ✅ | ✅ (token-count step auto-skips) | ✅\* (same) | ✅\* (drop the token-count step) | ⚠️ checklist only |
| dropoff / pickup³ | ✅ | ✅ | ✅\* | ✅\* | ❌ (no shared disk) |
| recap⁶ | ✅ | ✅ (rules-only; which items refresh depends on your tools) | ✅ (same) | ✅ (same) | ⚠️ report format only, nothing to refresh |
| mission-log / daily-debrief / weekly-debrief | ✅ | ❌ (no local transcripts) | ❌² | ❌² | ❌² |
| new-mission⁷ | ✅ | ✅ (rules-only, zero tool deps) | ✅ (rules-only) | ✅ (rules-only) | ⚠️ paste as a kickoff protocol |
| damage-report | ⚠️⁵ | ✅ (rules-only, zero tool deps) | ✅ (rules-only) | ✅ (Windows CLI runtime tested) | ⚠️ paste as a wrap-up checklist |
| blind-review⁶ | ✅ (needs subagent dispatch) | ⚠️ no subagents → open a clean chat by hand | ⚠️ same | ⚠️ same | ⚠️ use a blank chat as the attacker |
| ai-review | ✅ (needs a review backend⁴) | ⚠️ rules work; the script needs a shell | ⚠️ same | ⚠️ same | ⚠️ use prompts/ in another AI |
| ai-search⁷ | ✅ (needs a search backend) | ⚠️ rules work; the script needs a shell | ⚠️ same | ⚠️ same | ⚠️ use prompts/ with built-in browsing |
| token-optimizer | ✅ | ✅ (rules-only, no tool deps) | ⚠️ principles port¹ | ⚠️ principles port¹ | ⚠️ principles port¹ |
| flight-to-calendar | ✅ (needs Calendar connector) | ✅ (needs Calendar connector) | ⚠️ bring your own Calendar MCP (untested) | ❌ no Calendar tool | ⚠️ needs an Action |

\* = install/discovery layers verified; execution layer is rules-based inference (see [docs/TEST_PLAN.md](docs/TEST_PLAN.md) CROSS-05).
¹ The five iron rules port; swap model names for your vendor's tiers. §1's "advanced backstop" (settings.json / env) only works in Claude Code — skip it elsewhere.
² The journal trio reads **Claude Code's own transcripts** (`~/.claude/projects/`) — the skill format installs elsewhere, but the data isn't there, hence ❌.
³ The "instant doorbell" (messaging the target session right after a dropoff) is an optional enhancement that needs Claude Code v2.1.224+ cross-session messaging (officially macOS/Linux; messages to bypass-permissions sessions are held for manual approval); other tools skip it automatically — file-based handoff is unaffected.
⁴ `ai-review` needs a review backend (Codex CLI by default, swappable via `AI_REVIEW_CMD`) plus a POSIX shell. No backend or not signed in → `skipped_*` and it still **exits 0**, so it never breaks your flow; quota/network failures exit 2 by default, and `--soft-fail` makes those exit 0 too. It deliberately pins no model. macOS and Linux verify full POSIX permissions; Windows 11 Git Bash verifies the remaining behavior and explicitly skips the mode bit that NTFS cannot prove. **Free-tier accounts remain untested**. ⁵ Claude Code 2.1.231 on Windows did not produce the complete five-question contract **for `damage-report`** in non-interactive `-p` mode, so that cell is not backed by package success alone; interactive TUI needs a separate test. ⚠️ This is a **skill-specific** limit, not "skills don't run in `-p`" — the same `-p` mode ran `dropoff` end-to-end and wrote the card (see TEST_PLAN CROSS-05). ⁶ `recap` and `blind-review` were added in v0.7.0 and are **untested on every tool**: the ratings above are inferred from "rules-only" / "needs subagents", not measured.
⁷ `new-mission` and `ai-search` were adopted in v0.8.0 from upstream `tingyulu/MyR2D2` v0.7.3; v0.8.1–v0.8.4 added the Windows fixes and the measurements. Every rating above is now **measured**: the **install layer** on `codex`, `claude-code`, `gemini-cli`, `cursor` and `github-copilot` at **14/14, 0 Skipped** each; the **discovery layer** on Gemini (0 skills listed while untrusted, all **14 `[Enabled]`** once trusted — 0.58.0; the trusted-folder gate is silent); the **execution layer**, with `dropoff` run end-to-end on **Codex CLI, Claude Code CLI and Gemini CLI**, each produced card checked field-by-field against the spec, and all three independently degrading to "no doorbell capability → don't notify" (CROSS-05 — the first time this repo has ever measured it); `ai-search`'s 44-item behavior matrix on every push, its **`ok` path on both the default Codex backend and a pluggable one**, and failure classification against a real backend. **Still unmeasured**: the execution-layer spot check covers `dropoff` only, so it does not extend to skills needing an external connector (`flight-to-calendar`) or subagents (`blind-review`); `cursor`/`github-copilot` are install-layer only (neither tool is installed here); free-tier accounts are **deliberately not tested** (it would need a separate account, and borrowing someone else's proves nothing about yours — that is a decision, not a backlog item). `ai-search` needs a backend that **actually searches the web** (Codex CLI's built-in search by default, swappable via `AI_SEARCH_CMD` — the replacement must also search). No backend or not signed in → `skipped_*` and exit 0, so automation that only checks exit codes reads "skipped" as success; parse the final `AI_SEARCH_STATUS:` line on stdout to tell them apart. Per-item evidence: [docs/TEST_PLAN.md](docs/TEST_PLAN.md) section F, CROSS-02 and CROSS-05.

- **Gemini CLI / Codex CLI**: all three layers verified — Gemini measured on 0.58.0 in both discovery states (0/14 while untrusted, all 14 `[Enabled]` once trusted); the **trusted-folder gate is silent, so if skills don't show up, trust the project folder first**. Both passed the execution layer with `dropoff` (see TEST_PLAN CROSS-05).
- **ChatGPT**: no CLI / no filesystem — manual paste is the only path (see adapters).
- Cursor / Copilot: **install layer verified** (14/14, 0 Skipped each, 2026-09-06); discovery and execution layers untested (neither tool is installed here).

Porting guide for ChatGPT / Codex (preferred `npx skills` path, AGENTS.md fallback, three gotchas): **[adapters/openai/](adapters/openai/README.md)**.

## Install

**Pick your lane**: CLI user → npx or Plugin | want manual control → manual copy | chat-only → no-install lite prompts | claude.ai Cowork → last section.

### skills.sh (`npx skills`) — recommended, one command

[![skills.sh](https://skills.sh/b/SanHsien/agent-astromech)](https://skills.sh/SanHsien/agent-astromech) [![CI](https://github.com/SanHsien/agent-astromech/actions/workflows/ci.yml/badge.svg)](https://github.com/SanHsien/agent-astromech/actions/workflows/ci.yml)
(The skills.sh badge counts cumulative installs, not the number of skills.)

```bash
npx skills add SanHsien/agent-astromech
```

[`npx skills`](https://github.com/vercel-labs/skills) supports Claude Code and many other agents (`gemini-cli`, `codex`, `cursor`, … — full list in the upstream README). This repo has verified the **install layer on five targets** — `codex`, `claude-code`, `gemini-cli`, `cursor`, `github-copilot` — at 14/14 with 0 Skipped each (method & evidence in [docs/TEST_PLAN.md](docs/TEST_PLAN.md) CROSS-01). It installs to the **project scope** `./.claude/skills/` by default; add `-g` for a global install. Use `--skill` to pick individual skills.

### Claude Code CLI — Plugin (deep integration)

```
/plugin marketplace add SanHsien/agent-astromech
/plugin install agent-astromech@agent-astromech
```

Skills land under the `agent-astromech:` namespace (`/agent-astromech:dropoff`, …) — structurally conflict-free with any same-name skills you already have, and centrally updatable via the marketplace.

### Claude Code CLI — manual copy

```bash
git clone https://github.com/SanHsien/agent-astromech.git
cp -rn agent-astromech/skills/* ~/.claude/skills/
```

⚠️ Note the `-n` (no-clobber): if `~/.claude/skills/` already has folders with these names, plain `cp -r` **overwrites them silently**. Diff first if you're updating an existing install.

### Chat-only? No-install lite prompts

No CLI, nothing to install: [prompts/](prompts/) has paste-ready lite versions for rules-type skills — `new-mission` ([zh-TW](prompts/new-mission.md) | [EN](prompts/new-mission.en.md) — paste into persistent instructions so it **asks, plans, waits for your go — then closes with a wrap-up report**), `damage-report` ([zh-TW](prompts/damage-report.md) | [EN](prompts/damage-report.en.md); a 1,260-char [minimal version](prompts/damage-report.lite.en.md) fits narrow fields like ChatGPT Free), `ai-review` ([zh-TW](prompts/ai-review.md) | [EN](prompts/ai-review.en.md) — paste it into **another** AI and that is your cross-model review) `ai-search` ([zh-TW](prompts/ai-search.md) | [EN](prompts/ai-search.en.md) — paste into an AI **with browsing** for cited, real-time verification), `recap` ([zh-TW](prompts/recap.md) | [EN](prompts/recap.en.md) — re-checks before reporting status in four columns; anything it cannot check is marked "unverified") and `token-optimizer` ([zh-TW](prompts/token-optimizer.md) | [EN](prompts/token-optimizer.en.md) — thrift rules for work split into stages or across chats).

### Cowork / claude.ai

First get the repo via the manual-copy `git clone` (or **Code → Download ZIP** on the GitHub page), then add the skill folders you want (`skills/<name>/`) to your Cowork project skills (or the project's `.claude/skills/`).

Then trigger with `/save-all`, `/dropoff`, `/pickup`, `/recap`, `/daily-debrief`, `/new-mission`, `/damage-report`, `/blind-review`, `/ai-review`, `/ai-search`, etc., or natural language in either language.

## Updating

Installed skills are point-in-time snapshots — **new releases won't notify you**. To update:

```bash
npx skills update
```

One command updates every installed skill (sources are recorded in the install-time lock file; `-g`/`-p` scopes to global/project). For plugin installs, update the marketplace via the `/plugin` UI. To get notified on new releases: **Watch → Custom → Releases** on this repo.

## One skill set, two language habits

The skill bodies are written in Traditional Chinese (single source of truth — no parallel translations to maintain). **Trigger phrases come in matched zh/en pairs** in each skill's description:

- 中文習慣:「要重開機了」「交接給 X」「有沒有交接給我的」
- English habit: "about to reboot", "hand this off to X", "anything handed off to me?"

Claude follows the zh-TW instructions and replies in whatever language you speak — English users lose nothing, and there's only ever one copy of each skill to maintain.

## Per-skill dependencies

| Skill | Dependencies |
|---|---|
| save-all | None (the token-count step is Claude Code CLI-only and optional) |
| dropoff / pickup | None — cards are Markdown files under the project's `.claude/handoffs/`; the instant doorbell is an optional enhancement (Claude Code v2.1.224+), auto-skipped where unavailable |
| recap | None (pure rules) — but **the refresh step uses tools**: version control, PR, CI and background jobs each get re-queried; whatever your environment lacks is labelled "unverified" instead of reusing the stale value from the conversation |
| mission-log | None — the harvester is a stdlib-only python3 script, zero tokens. Ships tests (`tests/harvest_test.py`, synthetic fixtures — never reads your real data) |
| daily-debrief | **Requires mission-log** (the harvester lives there) |
| weekly-debrief | **Requires daily-debrief and mission-log** (missing dailies are auto-backfilled) |
| new-mission | None (pure rules; the `ai-review` hookup in step 3's advanced section is an optional cross-reference) |
| damage-report | None (pure rules; the `/dropoff` mention in Q5 and the `ai-review` upgrade section are optional cross-references) |
| blind-review | **An environment that can dispatch a read-only subagent** (the attacker not having the conversation is the whole premise; with no subagents, open a clean chat by hand instead). Complementary to `ai-review`, not overlapping: this one swaps context, that one swaps model family |
| ai-review | **A review backend** (Codex CLI by default; `AI_REVIEW_CMD` swaps in any command that reads stdin and writes stdout) plus a POSIX shell. A built-in 600-second wall-clock timeout is adjustable with `--timeout`. No extra packages: no npm module, no brew formula, no API key of your own. Ships 46 regression tests (`tests/matrix.sh`, no quota burned) |
| ai-search | **A web-searching backend** (Codex CLI's built-in `web_search` by default; `AI_SEARCH_CMD` swaps it, but the replacement must also search) plus a POSIX shell. No extra packages. Ships 44 regression tests (`tests/matrix.sh`, no quota burned, no network) |
| token-optimizer | None (rules-only; Workflow-specific items need the Workflow tool — Workflow is Claude Code's multi-agent orchestration feature; §1's advanced backstop is Claude Code CLI-only) |
| flight-to-calendar | **Google Calendar MCP connector** (hard dependency) |

dropoff/pickup default to the zero-dependency file-based version; if you run your own task system (CLI todo, Notion, Linear…), each SKILL.md includes a "plug in your own task system" section.

## Design principles

1. **Verification over declaration** — writes get read back, completion needs evidence, literal success messages are not trusted.
2. **Self-contained context** — handoff cards assume the reader knows nothing.
3. **Zero-dependency lowest common denominator** — file-based by default, external systems are the upgrade path.
4. **Quota is a shared resource** — thrift is the default for multi-agent dispatch; full power is an explicit switch.
5. **Single source of truth** — one copy per skill (zh-TW); language habits are handled by paired bilingual triggers, not parallel translations.

## Repo layout

```
agent-astromech/
├── .claude-plugin/                    ← plugin.json + marketplace.json (single plugin)
├── .github/workflows/                 ← CI (YAML validation, content gate, behavior matrix, harvest tests)
├── skills/                            ← 14 skills (zh-TW body, bilingual triggers)
│   ├── save-all/  ├── dropoff/  ├── pickup/  ├── recap/
│   ├── mission-log/  ├── daily-debrief/  ├── weekly-debrief/
│   ├── new-mission/  ├── damage-report/  ├── blind-review/
│   ├── ai-review/  ├── ai-search/
│   └── token-optimizer/  └── flight-to-calendar/
├── prompts/                           ← no-install lite prompts (paste into any chat)
├── docs/                              ← test plan + verification notes for external claims
│   └── cheatsheet.md                  ← 14-skill cheat sheet
├── adapters/openai/                   ← ChatGPT / Codex porting kit (other tools install directly via npx skills — no kit needed)
├── README.md                          ← zh-TW (primary)
└── README.en.md                       ← this page
```

## Attribution

- `token-optimizer` is adapted from [kieiken/ultracode-token-optimization](https://github.com/kieiken/ultracode-token-optimization) (MIT), generalized for all-Claude environments.

## License

MIT — see [LICENSE](LICENSE).

*agent-astromech is an astromech workflow skills pack designed for AI Coding Agents.*
