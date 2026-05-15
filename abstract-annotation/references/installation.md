# Installation and Sharing

This skill is packaged as a generic Agent Skill folder. The portable core is:

```text
abstract-annotation/
  SKILL.md
  scripts/
  references/
```

The optional `agents/openai.yaml` file provides Codex UI metadata. Claude Code and other agents can ignore it.

## Claude Code

Personal skill:

```bash
mkdir -p ~/.claude/skills
unzip abstract-annotation-agent-skill.zip -d ~/.claude/skills
```

Project skill:

```bash
mkdir -p .claude/skills
unzip abstract-annotation-agent-skill.zip -d .claude/skills
```

Restart Claude Code after installing or updating the skill.

## Codex

Personal skill on macOS/Linux:

```bash
mkdir -p ~/.codex/skills
unzip abstract-annotation-agent-skill.zip -d ~/.codex/skills
```

Personal skill on Windows PowerShell:

```powershell
Expand-Archive -Path .\abstract-annotation-agent-skill.zip -DestinationPath "$env:USERPROFILE\.codex\skills" -Force
```

Restart Codex or open a new session after installing or updating the skill.

## Agent-neutral usage

After installation, ask the agent for literature CSV analysis, for example:

```text
Use the abstract-annotation skill to extract variables that influence urban vitality from my literature CSV folder.
```

The agent should load `SKILL.md`, follow `references/workflow.md`, and use the bundled scripts for deterministic CSV filtering and final output generation.
