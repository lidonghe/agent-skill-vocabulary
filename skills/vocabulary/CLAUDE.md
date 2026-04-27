# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an OpenClaw skill for managing an English vocabulary notebook. It's a **pure Agent implementation** - all logic is defined in SKILL.md and executed by the AI, not by Python scripts.

## Key Files

- **SKILL.md** — The skill specification. Contains trigger keywords, operation flows, data structure definitions, and API specifications. This is the primary file that defines how the skill behaves.
- **README.md** — User-facing documentation for installation and basic usage.

## Architecture

The skill is triggered by keywords and operates via:
1. **Add word**: Query Free Dictionary API → translate first definition via MyMemory API → append to `data/words.json`
2. **Quiz**: One-by-one mode where Agent uses LLM to judge semantic equivalence between user answer and correct definition
3. **Stats**: Calculate accuracy from `quiz_history` array within each word entry

## Data Storage

User data persists at `data/words.json` in the agent's working directory (independent of skill updates).

Structure:
```json
{
  "words": [{ "id": 1, "word": "...", "quiz_history": [...] }],
  "next_id": 2,
  "settings": {}
}
```

## External APIs

- **None** — fully autonomous by Agent
