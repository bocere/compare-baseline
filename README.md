# Compare Baseline

A Codex and Claude Code skill that compares two OAKF publication baseline XML
files and reports which documents differ in version between them.

It locates baseline files in `oakf_local_storage_prod` by publication GUID
and version, parses the XML, and prints a Markdown table of document
titles, GUIDs, and per-baseline versions, with mismatches sorted first.

## Contents

```
compare-baseline/
├── SKILL.md                  # Skill definition Claude Code loads
├── agents/
│   └── openai.yaml           # Display name, description, default prompt
└── scripts/
    └── compare_baseline.py   # Standalone comparison script
```

## Usage

### Via Claude Code

Invoke the skill and let Claude drive the script for you:

```
Use $compare-baseline to compare two OAK publication baselines by GUID and version.
```

### Directly

Run the script on its own — it works without Claude Code too.

Interactive:

```bash
python scripts/compare_baseline.py
```

It prompts for a GUID + version pair twice:

```
Enter the first GUID and version: PGUID-70F40A08-5515-441E-AB22-013DC79ADCFE 15
Enter the second GUID and version: PGUID-70F40A08-5515-441E-AB22-013DC79ADCFE 16
```

Non-interactive, with arguments:

```bash
python scripts/compare_baseline.py --first PGUID-... 15 --second PGUID-... 16
```

With an explicit OAK directory:

```bash
python scripts/compare_baseline.py --oakdir /path/to/oakf_local_storage_prod \
  --first PGUID-... 15 --second PGUID-... 16
```

## OAK directory detection

The script resolves `OAKDIR` in this order:

1. `--oakdir`, if given.
2. The platform default:
   - Linux: `~/.wine/drive_c/users/$USER/AppData/Local/OAKF/oakf_local_storage_prod`
   - Windows: `%USERPROFILE%\AppData\Local\OAKF\oakf_local_storage_prod`
3. A search of common home-directory locations for a folder named
   `oakf_local_storage_prod`. If found, it asks for confirmation
   (`Is your OAK directory <path>? [y|n]`) before using it.
4. A manual path prompt, as a last resort.

## Baseline file matching

Baseline files are expected to be named:

```
<title>=<GUID>=<Version>.XML
```

- GUID matching is case-insensitive.
- Version matching is exact after trimming whitespace.
- If multiple files match, the most recently modified one is used.

## Output

A Markdown table with columns:

| Title | Document GUID | Version in First Baseline | Version in Second Baseline | Match |
|---|---|---:|---:|:---:|

Mismatched rows (✅ / ❌) are sorted to the top.

## Requirements

- Python 3.10+ (uses `from __future__ import annotations` and `X | None` syntax)
- No third-party dependencies — only the standard library.

## Notes for maintainers

If the baseline XML schema changes and the parser's GUID/version/title
heuristics stop matching, patch `scripts/compare_baseline.py`'s
`GUID_ATTRS`, `VERSION_ATTRS`, and `TITLE_ATTRS` tuples (or the
`derive_title`/`collect_entries` logic) rather than rewriting the workflow.
