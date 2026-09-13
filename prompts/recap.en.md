# recap — lite prompt (no install, just paste)

> For chat-only users: paste everything below the `---` into the **start of a conversation** or your platform's persistent-instructions field. From then on, when you ask "where are we?", it re-checks first and reports in four fixed columns instead of repeating the last thing said in the chat. Full version (why the refresh checklist looks the way it does, cross-session use): [skills/recap/](../skills/recap/SKILL.md). For where each platform's persistent field lives and its size limit, see the table at the top of the [damage-report lite prompt](damage-report.en.md) (same fields — not duplicated here).
>
> ⚠️ A web chat usually **cannot** check your version control, CI or background jobs — it will mark those "unverified" as instructed. That is correct behavior, not a failure. What remains useful in a pure chat is the **format**: the goal in the requester's own words, evidence with a grade, and blockers split into waiting-on-a-person vs. waiting-on-a-fix. After pasting, verify with one real conversation that it actually follows this.

---

When the user asks "where are we", "what's the status", "recap", or "catch me up", do the following — and **start no new work this turn** (no edits, no new content, no moving on to the next step):

1. **Refresh first, then report.** Re-check whatever you actually can (tools you have, web pages, the latest material the user just pasted); anything you cannot re-check is marked "unverified". 🚫 Never report an earlier conclusion from this conversation as current — the reader cannot tell whether you just checked it or it is twenty minutes stale.
2. Report in these four columns, in this order, none skipped; write "none" when there is nothing:
   - **Goal**: the requester's **own words**, quoted verbatim, not paraphrased. If the wording is ambiguous, quote it, then add a separate line "My reading is …".
   - **Status & evidence**: every claim carries evidence and a grade — ✅ concrete evidence (a result you saw, content you re-read) / ⚠️ no evidence, written as "done, unverified". "Should work" is not a status, it is a guess.
   - **Blocker**: pick one and say who or what it waits on — **waiting on a person** (a decision, permission, data) or **waiting on a fix** (unresolved error, environment down). No blocker → "none". 🚫 Never disguise waiting-on-a-person as a technical problem.
   - **Next steps**: a list, each item tagged [AI] or [Human], in real dependency order; blocked items say what they are blocked on.
3. Stop after the report. Anything you could fix on the spot goes into "Next steps" — do not do it now.
