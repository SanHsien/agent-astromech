# token-optimizer — lite prompt (no install, just paste)

> Adapted from [kieiken/ultracode-token-optimization](https://github.com/kieiken/ultracode-token-optimization) (MIT), generalized in this repo's [skills/token-optimizer/](../skills/token-optimizer/SKILL.md) and condensed here.
>
> For chat-only users: paste everything below the `---` into the **start of a conversation** or your platform's persistent-instructions field. It applies whenever you have the AI **split work into stages, spread it across several chats, or dispatch its own sub-tasks** — the goal is to stop rework loops and pasted-back walls of output from burning your quota. Full version (Workflow-script syntax, the pre-dispatch checklist): [skills/token-optimizer/](../skills/token-optimizer/SKILL.md). For where each platform's persistent field lives and its size limit, see the table at the top of the [damage-report lite prompt](damage-report.en.md).
>
> ⚠️ These are **behavior rules, not a hard quota cap**. If your platform cannot pick a model per sub-task, rule 1 falls to you when you open each new chat. After pasting, verify with one real multi-part task that it actually follows this.

---

When a task has to be split into stages, sub-tasks, or several chats, do the following:

1. **Tier the models.** Keep judgment and final calls on the strongest tier; writing, editing, and ordinary review go to a mid tier; mechanical work that needs no judgment (summarizing, formatting, gathering search results) goes to the cheapest tier. Whenever a model can be chosen, **choose it explicitly for every stage** — do not let everything inherit the most expensive default.
2. **Compress results before reporting.** Each sub-task returns three lines only: done / not done + what changed + verification result. 🚫 Never paste full raw output, long logs, or whole diffs back into the main thread. If details are needed, run a separate stage to read them and return a summary.
3. **Separate the roles.** Whoever does the work does not review it. The reviewer only lists problems (trigger + how to reproduce + where), gives no fixes, and does not rule pass/fail. Problems without evidence are dropped, not forwarded to the doer.
4. **Completion needs evidence, not self-declaration.** Agree up front how "done" will be checked (the file exists, the result reproduces); "Done!" does not count. The final output is **a proposal awaiting the user's approval** — nothing is sent or published automatically.
5. **Stop after the same error three times in a row.** Report the current state and the blocker, then change the angle (another model tier, another way to split, or ask a human) — no fourth identical retry.
