---
name: compare-baseline
description: Compare two OAKF publication baseline XML files by publication GUID and version. Use when a user needs to find baseline files named with title, PGUID, and version separated by equals signs in oakf_local_storage_prod and produce a mismatch-first table of document titles, GUIDs, versions, and match status across two baselines on Oracle Linux or Windows.
---

# Compare Baseline

Use this skill to compare two OAKF publication baselines. Prefer the bundled script because it handles cross-platform OAK directory detection, interactive prompts, baseline file discovery, XML parsing, sorting mismatches first, and Markdown table formatting.

## Quick Start

Run:

```bash
python scripts/compare_baseline.py
```

The script prompts for:

- `Enter the first GUID and version:`
- `Enter the second GUID and version:`

Each response must contain a publication GUID beginning with `PGUID` and a version value, for example:

```text
PGUID-70F40A08-5515-441E-AB22-013DC79ADCFE 15
```

## OAK Directory Rules

The script sets `OAKDIR` from the operating system:

- Linux: `~/.wine/drive_c/users/$USER/AppData/Local/OAKF/oakf_local_storage_prod`
- Windows: `%USERPROFILE%\AppData\Local\OAKF\oakf_local_storage_prod`

If that directory does not exist, the script searches common home-directory locations for `oakf_local_storage_prod`. When it finds a candidate, it asks:

```text
Is your OAK directory <path/to/folder>? [y|n]
```

Answering `y`, `Y`, `yes`, or `Yes` uses that directory. Answering `n`, `N`, `no`, or `No` prompts for the OAKDIR path.

## Baseline Lookup

Baseline files must match:

```text
<title>=<GUID>=<Version>.XML
```

The GUID comparison is case-insensitive. The version comparison is exact after trimming whitespace.

## Output

The comparison table columns are:

- Title
- Document GUID
- Version in First Baseline
- Version in Second Baseline
- Match

Rows with mismatches appear first. The Match column uses a green checkmark for matching versions and a red X for mismatches.

## Notes for Agents

- If the user gives all four values in the prompt, run the script with arguments instead of interactive input:

```bash
python scripts/compare_baseline.py --first PGUID-... 15 --second PGUID-... 16
```

- If OAKDIR is already known, pass it explicitly:

```bash
python scripts/compare_baseline.py --oakdir /path/to/oakf_local_storage_prod --first PGUID-... 15 --second PGUID-... 16
```

- If XML schema details differ from the parser's heuristics, inspect the baseline XML and patch `scripts/compare_baseline.py` rather than rewriting the workflow by hand.
