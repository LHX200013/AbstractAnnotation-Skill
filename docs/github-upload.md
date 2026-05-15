# GitHub Upload Guide

## Recommended Repository Settings

For this project type:

- Visibility: `Private` while raw abstracts or database exports are present.
- License: `MIT License` for original skill code, prompts, workflow documentation, and scripts.
- README: do not auto-generate if a local README already exists.
- `.gitignore`: use a custom project `.gitignore`.

## Connector-Based Path

1. Create the GitHub repository manually.
2. Connect the GitHub plugin or connector in Codex.
3. Provide the repository full name, for example:

```text
LHX200013/AbstractAnnotation-Skill
```

4. Codex can then create or update repository files through the connector.

## Local Git Path

If using local Git and GitHub CLI:

```powershell
git init
git branch -M main
git add .
git commit -m "Add abstract annotation workflow"
gh repo create AbstractAnnotation-Skill --private --source . --remote origin --push
```

Use `--public` only after checking whether raw abstracts or vendor metadata can be redistributed.

## Publication Caution

The local workflow may include bibliographic exports and article abstracts. Public upload may require checking database export terms, publisher terms, and project privacy expectations.

For a public repository, consider excluding raw input files and full abstract text, then publish documentation, sanitized examples, the dimension mapping, aggregate charts, and reproducible workflow notes.
