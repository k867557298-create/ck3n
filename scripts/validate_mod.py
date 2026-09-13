#!/usr/bin/env python3
"""Dependency-free static validation for the CK3 mod data shipped in this repository."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "OttomanSuleiman"


def fail(message: str) -> None:
    raise SystemExit(f"validation error: {message}")

# Descriptor compatibility and presence of both launcher descriptor files.
for descriptor in (ROOT / "descriptor.mod", MOD / "descriptor.mod"):
    text = descriptor.read_text(encoding="utf-8")
    if 'supported_version="1.19.*"' not in text:
        fail(f"{descriptor}: expected CK3 1.19 support pattern")

# All Paradox script files must have balanced braces and paired double quotes.
for path in [*MOD.rglob("*.txt"), *MOD.rglob("*.mod")]:
    depth = 0
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0]
        if line.count('"') % 2:
            fail(f"{path}:{lineno}: unclosed quote")
        depth += line.count("{") - line.count("}")
        if depth < 0:
            fail(f"{path}:{lineno}: unexpected closing brace")
    if depth:
        fail(f"{path}: unclosed brace")

# Localisation needs Paradox's UTF-8 BOM, correct headers, and no duplicate keys.
for language in ("english", "russian"):
    path = MOD / "localization" / language / f"ottoman_suleiman_l_{language}.yml"
    raw = path.read_bytes()
    if not raw.startswith(b"\xef\xbb\xbf"):
        fail(f"{path}: missing UTF-8 BOM")
    text = raw.decode("utf-8-sig")
    if not text.startswith(f"l_{language}:\n"):
        fail(f"{path}: incorrect language header")
    keys = re.findall(r"^ ([A-Za-z0-9_.]+):", text, re.M)
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        fail(f"{path}: duplicate localisation keys: {', '.join(duplicates)}")

# Events must use CK3's current_date trigger, be registered in the pulse, and have localisation.
events = (MOD / "events" / "ottoman_suleiman_events.txt").read_text(encoding="utf-8")
if re.search(r"^\s*date\s*[<>=]", events, re.M):
    fail("events: use current_date rather than date in triggers")
event_ids = re.findall(r"\bid = (ottoman_suleiman\.\d+)", events)
pulse = (MOD / "common" / "on_action" / "ottoman_suleiman_on_actions.txt").read_text(encoding="utf-8")
for event_id in event_ids[1:]:
    if event_id not in pulse:
        fail(f"on_action: missing event {event_id}")
    for language in ("english", "russian"):
        loc = (MOD / "localization" / language / f"ottoman_suleiman_l_{language}.yml").read_text(encoding="utf-8-sig")
        for suffix in ("t", "desc", "a"):
            if not re.search(rf"^ {re.escape(event_id)}\.{suffix}: \".+\"$", loc, re.M):
                fail(f"{language}: missing localisation for {event_id}.{suffix}")

# County-level Sanjaks must all display the matching historical ruler style and be localised.
sanjaks = re.findall(r"^(c_[a-z0-9_]+) = \{ ruler_title = \"SANCAKBEY\" ruler_title_female = \"SANCAKBEY_FEMALE\" \}$", (MOD / "common" / "landed_titles" / "ottoman_sanjak_titles.txt").read_text(encoding="utf-8"), re.M)
if len(sanjaks) != 38:
    fail(f"expected 38 sanjak county overrides, got {len(sanjaks)}")
for language in ("english", "russian"):
    loc = (MOD / "localization" / language / f"ottoman_suleiman_l_{language}.yml").read_text(encoding="utf-8-sig")
    for title in sanjaks:
        if not re.search(rf"^ {title}: \".+\"$", loc, re.M):
            fail(f"{language}: missing localisation for {title}")

print(f"OK: CK3 1.19 descriptor, {len(event_ids)} events, and {len(sanjaks)} sanjak overrides validated.")
