#!/usr/bin/env python3
"""Compare two OAKF publication baseline XML files."""

from __future__ import annotations

import argparse
import os
import platform
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PGUID_RE = re.compile(r"\bPGUID-[A-Za-z0-9-]+\b", re.IGNORECASE)
DOCUMENT_GUID_RE = re.compile(r"\b(?:P?GUID)-[A-Za-z0-9-]+\b", re.IGNORECASE)
VERSION_ATTRS = ("version", "Version", "rev", "revision", "Revision")
GUID_ATTRS = ("guid", "GUID", "documentGuid", "documentGUID", "id", "ID")
TITLE_ATTRS = ("title", "Title", "name", "Name", "href", "HREF")


@dataclass(frozen=True)
class BaselineEntry:
    title: str
    guid: str
    version: str


def default_oakdir() -> Path:
    if platform.system().lower().startswith("win"):
        profile = os.environ.get("USERPROFILE", str(Path.home()))
        return Path(profile) / "AppData" / "Local" / "OAKF" / "oakf_local_storage_prod"

    user = os.environ.get("USER") or Path.home().name
    return Path.home() / ".wine" / "drive_c" / "users" / user / "AppData" / "Local" / "OAKF" / "oakf_local_storage_prod"


def candidate_roots() -> list[Path]:
    roots = [Path.home()]
    if platform.system().lower().startswith("win"):
        for key in ("USERPROFILE", "LOCALAPPDATA", "APPDATA"):
            value = os.environ.get(key)
            if value:
                roots.append(Path(value))
    else:
        roots.extend([Path.home() / ".wine", Path("/tmp")])
    return list(dict.fromkeys(roots))


def find_oakdir() -> Path | None:
    for root in candidate_roots():
        if not root.exists():
            continue
        try:
            for dirpath, dirnames, _ in os.walk(root):
                path = Path(dirpath)
                if path.name == "oakf_local_storage_prod":
                    return path
                if len(path.parts) - len(root.parts) > 8:
                    dirnames[:] = []
        except OSError:
            continue
    return None


def resolve_oakdir(provided: str | None) -> Path:
    if provided:
        path = Path(provided).expanduser()
        if path.exists():
            os.environ["OAKDIR"] = str(path)
            return path
        raise SystemExit(f"OAK directory does not exist: {path}")

    path = default_oakdir()
    if path.exists():
        os.environ["OAKDIR"] = str(path)
        return path

    found = find_oakdir()
    if found:
        answer = input(f"Is your OAK directory {found}? [y|n] ").strip()
        if answer in {"y", "Y", "yes", "Yes"}:
            os.environ["OAKDIR"] = str(found)
            return found
        if answer not in {"n", "N", "no", "No"}:
            raise SystemExit("Expected y or n.")

    entered = input("Enter the OAKDIR path: ").strip().strip('"')
    if not entered:
        raise SystemExit("OAKDIR path is required.")
    path = Path(entered).expanduser()
    if not path.exists():
        raise SystemExit(f"OAK directory does not exist: {path}")
    os.environ["OAKDIR"] = str(path)
    return path


def parse_guid_version(value: str, label: str) -> tuple[str, str]:
    match = PGUID_RE.search(value)
    if not match:
        raise SystemExit(f"{label} must include a GUID beginning with PGUID.")
    guid = match.group(0)
    remainder = (value[: match.start()] + " " + value[match.end() :]).strip()
    parts = remainder.split()
    if not parts:
        raise SystemExit(f"{label} must include a version.")
    return guid, parts[-1]


def prompt_guid_version(label: str) -> tuple[str, str]:
    return parse_guid_version(input(f"Enter the {label} GUID and version: "), label)


def baseline_sort_key(path: Path) -> tuple[int, str]:
    try:
        return (-path.stat().st_mtime_ns, path.name.lower())
    except OSError:
        return (0, path.name.lower())


def find_baseline(oakdir: Path, guid: str, version: str) -> Path:
    suffix = f"={guid}={version}.xml".lower()
    matches = [
        path
        for path in oakdir.rglob("*.XML")
        if path.name.lower().endswith(suffix)
    ]
    matches.extend(
        path
        for path in oakdir.rglob("*.xml")
        if path.name.lower().endswith(suffix) and path not in matches
    )
    if not matches:
        raise SystemExit(f"No baseline file found for {guid} version {version} in {oakdir}")
    matches.sort(key=baseline_sort_key)
    return matches[0]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def attr_value(element: ET.Element, names: Iterable[str]) -> str | None:
    lower = {key.lower(): value for key, value in element.attrib.items()}
    for name in names:
        value = lower.get(name.lower())
        if value:
            return value.strip()
    return None


def text_child(element: ET.Element, names: Iterable[str]) -> str | None:
    wanted = {name.lower() for name in names}
    for child in list(element):
        if local_name(child.tag) == "meta":
            meta_name = child.attrib.get("name", "").lower()
            if meta_name in wanted:
                content = child.attrib.get("content")
                if content and content.strip():
                    return content.strip()
        if local_name(child.tag) in wanted and child.text and child.text.strip():
            return child.text.strip()
    return None


def derive_title(element: ET.Element, guid: str) -> str:
    title = attr_value(element, TITLE_ATTRS) or text_child(element, TITLE_ATTRS)
    if title:
        return title
    return local_name(element.tag) or guid


def collect_entries(path: Path) -> dict[str, BaselineEntry]:
    tree = ET.parse(path)
    entries: dict[str, BaselineEntry] = {}
    for element in tree.iter():
        guid = attr_value(element, GUID_ATTRS) or text_child(element, GUID_ATTRS)
        if not guid:
            text = " ".join(part for part in (element.text, element.tail) if part)
            match = DOCUMENT_GUID_RE.search(text)
            guid = match.group(0) if match else None
        if not guid or not DOCUMENT_GUID_RE.fullmatch(guid):
            continue

        version = attr_value(element, VERSION_ATTRS) or text_child(element, VERSION_ATTRS)
        if not version:
            continue

        normalized = guid.upper()
        entry = BaselineEntry(derive_title(element, normalized), normalized, version.strip())
        entries[normalized] = entry
    return entries


def esc(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def markdown_table(first: dict[str, BaselineEntry], second: dict[str, BaselineEntry]) -> str:
    rows = []
    for guid in sorted(set(first) | set(second)):
        left = first.get(guid)
        right = second.get(guid)
        title = (left.title if left else None) or (right.title if right else "")
        first_version = left.version if left else ""
        second_version = right.version if right else ""
        match = bool(left and right and first_version == second_version)
        rows.append((match, title, guid, first_version, second_version))

    rows.sort(key=lambda row: (row[0], row[1].lower(), row[2]))

    lines = [
        "| Title | Document GUID | Version in First Baseline | Version in Second Baseline | Match |",
        "|---|---|---:|---:|:---:|",
    ]
    for match, title, guid, first_version, second_version in rows:
        symbol = "✅" if match else "❌"
        lines.append(
            f"| {esc(title)} | {esc(guid)} | {esc(first_version)} | {esc(second_version)} | {symbol} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oakdir", help="Path to oakf_local_storage_prod")
    parser.add_argument("--first", nargs=2, metavar=("GUID", "VERSION"), help="First publication GUID and version")
    parser.add_argument("--second", nargs=2, metavar=("GUID", "VERSION"), help="Second publication GUID and version")
    args = parser.parse_args()

    oakdir = resolve_oakdir(args.oakdir)
    first_guid, first_version = tuple(args.first) if args.first else prompt_guid_version("first")
    second_guid, second_version = tuple(args.second) if args.second else prompt_guid_version("second")

    first_path = find_baseline(oakdir, first_guid, first_version)
    second_path = find_baseline(oakdir, second_guid, second_version)

    first_entries = collect_entries(first_path)
    second_entries = collect_entries(second_path)

    print(f"First baseline: {first_path}")
    print(f"Second baseline: {second_path}")
    print()
    print(markdown_table(first_entries, second_entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
