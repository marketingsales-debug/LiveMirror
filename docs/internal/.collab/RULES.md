# LiveMirror Collaboration Rules

## Both AIs MUST read this file at the start of every session.

### RULE 1: READ BEFORE WRITE
Before doing ANY work, read:
- `.collab/STATUS.md` (current project state)
- `.collab/HANDOFF.md` (what was last done + what to do next)
- `.collab/DECISIONS.md` (all architecture decisions)
- `.ownership/CODEOWNERS.md` (who owns what)

### RULE 2: NEVER EDIT FILES YOU DON'T OWN
Check CODEOWNERS.md. If it's not yours:
- Write a review in `.collab/REVIEWS/`
- Or write a request in `.collab/HANDOFF.md`
- NEVER directly modify another AI's files

### RULE 3: SHARED FILES NEED A LOCK
To edit `src/shared/` or `src/api/`:
1. Write `LOCKED BY: [claude/gemini] — [reason] — [timestamp]` in STATUS.md
2. Make your changes
3. Remove the lock from STATUS.md
4. Document what you changed in HANDOFF.md

### RULE 4: LOG EVERY DECISION
Any choice that affects the other AI → append to `DECISIONS.md`
Format:
```
### [DATE] — [DECISION TITLE]
- **Decision:** What was decided
- **Reasoning:** Why
- **Alternatives:** What else was considered
- **Decided by:** claude / gemini / human
```

### RULE 5: ADVERSARIAL TESTING
- You write code → the OTHER AI writes tests to break it
- Claude's adversarial tests go in: `tests/adversarial/claude-tests/`
- Gemini's adversarial tests go in: `tests/adversarial/gemini-tests/`
- Goal: find edge cases, race conditions, logic errors

### RULE 6: HANDOFF COMPLETELY
When you finish a session, HANDOFF.md MUST contain:
- **What you did** (with file paths)
- **What's broken/incomplete**
- **What the other AI should do next**
- **Any blockers**

### RULE 7: GIT WORKFLOW
- Claude commits to: `claude/[feature-name]`
- Gemini commits to: `gemini/[feature-name]`
- NEVER push directly to `main`
- Human merges to main after review

### RULE 8: CONFLICT RESOLUTION
- If you disagree with a decision, write to `.collab/CONFLICTS.md`
- Do NOT override the other AI's decisions
- Human resolves all conflicts
- Resolution goes to `DECISIONS.md`
