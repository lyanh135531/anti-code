"""Source-grounded writing and fail-closed verification for Spiritus long-form."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from modules.ai_text import chat_complete, extract_json
from config import (
    CLOUDFLARE_VERIFIER_MODEL,
    LONG_MAX_IMAGES,
    LONG_MIN_IMAGES,
    LONG_TARGET_IMAGES,
)


MIN_VISUALS = LONG_MIN_IMAGES
MAX_VISUALS = LONG_MAX_IMAGES
TARGET_VISUALS = LONG_TARGET_IMAGES
REQUIRED_SECTION_KINDS = (
    "cold_open",
    "context",
    "rising_conflict",
    "turning_point",
    "catholic_meaning",
    "application",
    "cta",
)
SECTION_WORD_TARGETS = {
    "cold_open": 40,
    "context": 125,
    "rising_conflict": 190,
    "turning_point": 165,
    "catholic_meaning": 190,
    "application": 155,
    "cta": 35,
}


def _source_text(source_pack: dict) -> str:
    blocks = []
    for source in source_pack["sources"]:
        blocks.append(f"SOURCE_ID: {source['id']}\nURL: {source['url']}\nTEXT:\n{source['text']}")
    return "\n\n---\n\n".join(blocks)


def _json_completion(prompt: str, system: str, provider: str, max_tokens: int) -> dict:
    last_error: Exception | None = None
    current_prompt = prompt
    for attempt in range(2):
        try:
            raw = chat_complete(
                current_prompt,
                system=system,
                temperature=0.25 if attempt else 0.5,
                json_mode=True,
                provider=provider,
                max_output_tokens=max_tokens,
            )
            return extract_json(raw)
        except (ValueError, json.JSONDecodeError) as error:
            last_error = error
            current_prompt = (
                prompt
                + "\n\nYour previous response was malformed. Return one complete, strictly valid JSON "
                "object with no markdown and no unescaped quotation marks inside strings."
            )
    raise ValueError(f"AI did not return valid JSON after two attempts: {last_error}")


def generate_research_brief(topic: dict, source_pack: dict) -> dict:
    prompt = f"""Build a factual research brief for a Catholic YouTube narrative.

TOPIC: {topic['title_seed']}
PASSAGE: {topic['bible_passage']}

Use ONLY the supplied official sources. Do not add facts from memory. Distinguish what the
Biblical text states from Catholic interpretation. Return JSON with keys: narrative_facts
(array of objects with claim and source_refs), catholic_interpretation (same shape),
uncertainties (array), prohibited_overclaims (array).

SOURCES:
{_source_text(source_pack)}
"""
    raw = chat_complete(
        prompt,
        system="You are a meticulous Catholic research editor. Evidence outranks eloquence.",
        temperature=0.15,
        json_mode=True,
        provider="gemini",
        max_output_tokens=4096,
    )
    brief = extract_json(raw)
    if not isinstance(brief.get("narrative_facts"), list):
        raise ValueError("Research brief is missing narrative_facts")
    return brief


def generate_long_script(topic: dict, source_pack: dict, research_brief: dict) -> dict:
    prompt = f"""Write an original English long-form YouTube script for Spiritus.

TITLE SEED: {topic['title_seed']}
BIBLE PASSAGE: {topic['bible_passage']}
TARGET: create a concise structural draft. The application expands each section separately.
AUDIENCE: United States, interested in Catholic Christianity.

RETENTION STRUCTURE:
- cold_open: 10-20 seconds; immediately deliver the title/thumbnail promise.
- context, rising_conflict, turning_point, catholic_meaning, application, cta.
- No logo intro, fake testimony, fearbait, repeated moral, invented dialogue, or invented
  historical detail. End with one short reflection question and a restrained subscribe CTA.
- Paraphrase Scripture by default. Any direct quotation must be verbatim, 25 words or fewer,
  and explicitly attributed to its passage.
- Catholic interpretation must remain within the supplied Catechism sources.
- In cold_open, context, rising_conflict, and turning_point, narrate only observable words and
  actions in the Biblical source. Do not infer motives or add sociological background.
- Never use interpretive shortcuts such as legalism, boundary, narrow-minded, ritual impurity,
  fundamental duty, radical, universal, or transcends barriers unless those exact ideas are
  explicitly present in a cited source.

Return one JSON object exactly shaped like:
{{
  "title": "under 100 characters",
  "thumbnail_text": "2-4 words",
  "bible_passage": "...",
  "summary": "...",
  "sections": [
    {{"kind":"cold_open", "heading":"...", "narration":"...", "source_refs":["BIBLE"],
      "on_screen_text":"..."}}
  ],
  "description": "2-3 short paragraphs without sources",
  "tags": ["..."]
}}

Every section needs source_refs. on_screen_text is optional and at most 6 words. Use only the
SOURCE_ID values supplied below. The seven section kinds must occur exactly once and in order.

RESEARCH BRIEF:
{json.dumps(research_brief, ensure_ascii=False)}

OFFICIAL SOURCES:
{_source_text(source_pack)}
"""
    narrative = _json_completion(
        prompt,
        system=(
            "You are an original Catholic narrative writer. Treat the supplied source pack as "
            "the complete universe of factual claims. Output valid JSON only."
        ),
        provider="gemini",
        max_tokens=8192,
    )
    expanded_sections = []
    for section in narrative.get("sections", []):
        kind = section.get("kind")
        target = SECTION_WORD_TARGETS.get(kind)
        if target is None:
            raise ValueError(f"Unexpected section kind in narrative draft: {kind}")
        lower, upper = max(25, target - 25), target + 30
        expansion_prompt = f"""Expand exactly one section of a source-grounded Catholic YouTube script.

SECTION KIND: {kind}
WORD RANGE: {lower}-{upper} spoken words. Stay inside this range.
HEADING: {section.get('heading', '')}
DRAFT: {section.get('narration', '')}
CURRENT SOURCE REFS: {json.dumps(section.get('source_refs', []))}
FULL RESEARCH BRIEF: {json.dumps(research_brief, ensure_ascii=False)}

Write natural American English. Preserve the section's role in the retention structure. Add no
facts, dialogue, motives, historical color, or doctrine beyond the official sources. Paraphrase
Scripture; do not pad or repeat. For Biblical narrative sections, state observable words and acts,
not inferred motives. Do not use legalism, boundary, ritual impurity, fundamental duty, radical,
universal, or transcends barriers unless explicit in a cited source. Return JSON with heading,
narration, source_refs, on_screen_text.
The source_refs must use only exact SOURCE_ID values.

OFFICIAL SOURCES:
{_source_text(source_pack)}
"""
        expanded = {}
        count = 0
        for expansion_attempt in range(2):
            expanded = _json_completion(
                expansion_prompt
                + (
                    f"\nThe previous attempt contained {count} words. Rewrite it inside the exact range."
                    if expansion_attempt
                    else ""
                ),
                system="You expand one Catholic narrative section from evidence only. Output JSON only.",
                provider="gemini",
                max_tokens=2048,
            )
            count = len(re.findall(r"\b[\w’'-]+\b", str(expanded.get("narration", ""))))
            if lower <= count <= upper:
                break
        if not lower <= count <= upper:
            raise ValueError(f"Expanded section {kind} must contain {lower}-{upper} words, got {count}")
        expanded["kind"] = kind
        expanded_sections.append(expanded)
    narrative["sections"] = expanded_sections
    visual_prompt = f"""Create the visual plan for this finished Catholic Bible narration.

Return JSON with one key, sections. It must contain seven objects in the same order as the script:
{{"sections":[{{"kind":"cold_open","visual_prompts":["..."]}}]}}

Produce exactly 24 distinct prompts total, distributed as follows:
- cold_open, context, rising_conflict: exactly 4 prompts each.
- turning_point, catholic_meaning, application, cta: exactly 3 prompts each.
Every prompt must describe a historically restrained, reverent, landscape 16:9 fine-art scene
with safe margins for camera motion. Keep recurring figures consistent through stable robe colors.
Do not depict an invented visual detail as if Scripture stated it. Do not put written text in images.

SCRIPT:
{json.dumps(narrative, ensure_ascii=False)}
"""
    visual_plan = _json_completion(
        visual_prompt,
        system="You are a restrained Biblical art director. Output valid JSON only.",
        provider="gemini",
        max_tokens=6144,
    )
    visual_sections = visual_plan.get("sections")
    if not isinstance(visual_sections, list) or len(visual_sections) != len(REQUIRED_SECTION_KINDS):
        raise ValueError("Visual plan must contain seven sections")
    by_kind = {item.get("kind"): item.get("visual_prompts") for item in visual_sections if isinstance(item, dict)}
    for section in narrative.get("sections", []):
        section["visual_prompts"] = by_kind.get(section.get("kind"), [])
    total_visuals = sum(len(section.get("visual_prompts", [])) for section in narrative.get("sections", []))
    # Keep a near-valid model response usable without duplicating an image. Each supplement
    # requests a materially different framing of an existing source-grounded scene.
    supplement_index = 0
    while total_visuals < TARGET_VISUALS:
        section = narrative["sections"][supplement_index % len(narrative["sections"])]
        visuals = section.get("visual_prompts", [])
        if not visuals:
            raise ValueError(f"Visual plan omitted section {section.get('kind')}")
        base = visuals[supplement_index % len(visuals)]
        visuals.append(
            f"Alternate wider composition from a different camera distance, preserving the same "
            f"source-grounded moment and character colors: {base}"
        )
        supplement_index += 1
        total_visuals += 1
    while total_visuals > TARGET_VISUALS:
        section = max(narrative["sections"], key=lambda item: len(item.get("visual_prompts", [])))
        if len(section.get("visual_prompts", [])) <= 1:
            raise ValueError("Visual plan cannot be reduced safely")
        section["visual_prompts"].pop()
        total_visuals -= 1
    return normalize_and_validate(narrative, source_pack)


def normalize_and_validate(script: dict, source_pack: dict) -> dict:
    value = deepcopy(script)
    sections = value.get("sections")
    if not isinstance(sections, list) or len(sections) != len(REQUIRED_SECTION_KINDS):
        raise ValueError("Long-form script must contain exactly seven sections")
    kinds = tuple(section.get("kind") for section in sections)
    if kinds != REQUIRED_SECTION_KINDS:
        raise ValueError(f"Invalid long-form section order: {kinds}")

    allowed_refs = {source["id"] for source in source_pack["sources"]}
    narration_parts: list[str] = []
    visual_prompts: list[str] = []
    all_refs: set[str] = set()
    for section in sections:
        narration = section.get("narration")
        refs = section.get("source_refs")
        visuals = section.get("visual_prompts")
        if not isinstance(narration, str) or not narration.strip():
            raise ValueError(f"Section {section.get('kind')} has no narration")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"Section {section.get('kind')} has no source_refs")
        canonical_refs = []
        for ref in refs:
            if not isinstance(ref, str):
                raise ValueError(f"Section {section.get('kind')} has a non-string source reference")
            canonical_refs.append(ref.split(":", 1)[0].strip())
        unknown = set(canonical_refs) - allowed_refs
        if unknown:
            raise ValueError(f"Section {section.get('kind')} cites unknown sources: {sorted(unknown)}")
        section["source_refs"] = canonical_refs
        if not isinstance(visuals, list) or not all(isinstance(item, str) and item.strip() for item in visuals):
            raise ValueError(f"Section {section.get('kind')} has invalid visual prompts")
        on_screen = section.get("on_screen_text", "")
        if on_screen:
            section["on_screen_text"] = " ".join(str(on_screen).split()[:6])
        narration_parts.append(narration.strip())
        visual_prompts.extend(item.strip() for item in visuals)
        all_refs.update(canonical_refs)

    if not MIN_VISUALS <= len(visual_prompts) <= MAX_VISUALS:
        raise ValueError(f"Expected {MIN_VISUALS}-{MAX_VISUALS} visuals, got {len(visual_prompts)}")
    if "BIBLE" not in all_refs or not any(ref.startswith("CCC_") for ref in all_refs):
        raise ValueError("Script must cite both Biblical and Catechism sources")

    narration = "\n\n".join(narration_parts)
    word_count = len(re.findall(r"\b[\w’'-]+\b", narration))
    if not 700 <= word_count <= 1100:
        raise ValueError(f"Long-form narration has implausible word count: {word_count}")
    thumbnail_words = str(value.get("thumbnail_text", "")).split()
    if len(thumbnail_words) < 2:
        thumbnail_words = str(value.get("title", "Spiritus Bible Story")).split()[:3]
    value["thumbnail_text"] = " ".join(thumbnail_words[:4]).strip(".,:;!?-")
    if len(value["thumbnail_text"].split()) < 2:
        raise ValueError("thumbnail_text must contain 2-4 words")
    value["title"] = str(value.get("title", "")).strip()[:100]
    if not value["title"]:
        raise ValueError("Long-form title is required")
    if value.get("bible_passage") != source_pack["bible_passage"]:
        raise ValueError("Script Bible passage does not match source pack")

    value["narration"] = narration
    value["visual_prompts"] = visual_prompts
    value["source_refs"] = sorted(all_refs)
    value["word_count"] = word_count
    value["verification_status"] = "PENDING"
    return value


def verify_script(script: dict, source_pack: dict) -> dict:
    allowed_refs = {source["id"] for source in source_pack["sources"]}
    sources_by_id = {source["id"]: source for source in source_pack["sources"]}
    combined_claims: list[dict] = []
    required_changes: list[str] = []
    model_statuses: dict[str, str] = {}
    section_results: dict[str, bool] = {}

    for section in script.get("sections", []):
        kind = section["kind"]
        cited_sources = [sources_by_id[ref] for ref in section["source_refs"] if ref in sources_by_id]
        audit_prompt = f"""Audit exactly one section of a Catholic YouTube script.

SECTION KIND: {kind}
HEADING: {section.get('heading', '')}
NARRATION: {section.get('narration', '')}
DECLARED SOURCE REFS: {json.dumps(section.get('source_refs', []))}

Using ONLY the supplied official sources, enumerate every material factual, Biblical, historical,
or doctrinal claim. Check invented motives, invented dialogue/detail, inaccurate quotation,
unsupported interpretation, fearbait, and deceptive promises. A rhetorical question or personal
invitation is not a factual claim.

Return JSON: {{"status":"PASS or FAIL","reason":"...","claims":[{{"section":"{kind}",
"claim":"...","source_refs":["..."],"status":"PASS or FAIL","reason":"..."}}],
"required_changes":["..."]}}. Return at least one claim record. If there is no material claim,
use claim "No material claim", the section's declared refs, and PASS. The section field must be
exactly "{kind}". Status PASS requires every listed claim to be supported.

OFFICIAL SOURCES:
{_source_text({'sources': cited_sources})}
"""
        section_report: dict[str, Any] = {}
        for attempt in range(2):
            raw = chat_complete(
                audit_prompt
                + ("\nPrevious response was incomplete. Return complete valid JSON." if attempt else ""),
                system="You are an adversarial Catholic fact checker. Fail closed. Output JSON only.",
                temperature=0.0,
                json_mode=True,
                provider="cloudflare",
                provider_model=CLOUDFLARE_VERIFIER_MODEL,
                max_output_tokens=1536,
            )
            section_report = extract_json(raw)
            claims = section_report.get("claims")
            if isinstance(claims, list) and claims:
                break

        claims = section_report.get("claims")
        section_valid = isinstance(claims, list) and bool(claims)
        model_statuses[kind] = str(section_report.get("status", "UNKNOWN"))
        if section_valid:
            for claim in claims:
                if not isinstance(claim, dict) or claim.get("section") != kind:
                    section_valid = False
                    continue
                refs = claim.get("source_refs")
                canonical = (
                    [ref.split(":", 1)[0].strip() for ref in refs if isinstance(ref, str)]
                    if isinstance(refs, list)
                    else []
                )
                if (
                    claim.get("status") != "PASS"
                    or not canonical
                    or len(canonical) != len(refs)
                    or set(canonical) - allowed_refs
                    or not set(canonical).issubset(set(section["source_refs"]))
                ):
                    section_valid = False
                claim["source_refs"] = canonical
                combined_claims.append(claim)
        if not section_valid and not any(
            isinstance(claim, dict) and claim.get("section") == kind and claim.get("status") != "PASS"
            for claim in (claims or [])
        ):
            combined_claims.append(
                {
                    "section": kind,
                    "claim": "Verifier returned an incomplete or invalid section audit",
                    "source_refs": section["source_refs"],
                    "status": "FAIL",
                    "reason": "The accuracy audit could not establish complete coverage",
                }
            )
        section_results[kind] = section_valid
        required_changes.extend(str(item) for item in section_report.get("required_changes", []))

    passed = set(section_results) == set(REQUIRED_SECTION_KINDS) and all(section_results.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "reason": "All seven sections passed source audit" if passed else "One or more sections failed source audit",
        "claims": combined_claims,
        "required_changes": required_changes,
        "model_statuses": model_statuses,
    }


def repair_script(script: dict, report: dict, source_pack: dict) -> dict:
    repaired = deepcopy(script)
    repaired_sections = []
    failed_labels = {
        str(claim.get("section", "")).strip().lower()
        for claim in report.get("claims", [])
        if isinstance(claim, dict) and claim.get("status") != "PASS"
    }
    for section in script["sections"]:
        kind = section["kind"]
        heading = str(section.get("heading", "")).strip().lower()
        if failed_labels and kind.lower() not in failed_labels and heading not in failed_labels:
            repaired_sections.append(deepcopy(section))
            continue
        target = SECTION_WORD_TARGETS[kind]
        lower, upper = max(25, target - 25), target + 30
        prompt = f"""Repair exactly one section of a Catholic YouTube script using the verifier report.

Keep {lower}-{upper} spoken words. Remove or correct every unsupported claim; never compensate by
inventing detail. Preserve supported sentences. For Biblical narrative sections, state observable
words and acts only, not inferred motives. Do not use legalism, boundary, ritual impurity,
fundamental duty, radical, universal, or transcends barriers unless explicit in a cited source. Return
JSON with heading, narration, source_refs, and on_screen_text. Use exact SOURCE_ID values only.

SECTION: {json.dumps({key: value for key, value in section.items() if key != 'visual_prompts'}, ensure_ascii=False)}
FULL VERIFIER REPORT: {json.dumps(report, ensure_ascii=False)}
OFFICIAL SOURCES: {_source_text(source_pack)}
"""
        fixed = {}
        count = 0
        for attempt in range(2):
            fixed = _json_completion(
                prompt
                + (f"\nThe previous repair had {count} words; rewrite within range." if attempt else ""),
                system="You repair Catholic scripts strictly from evidence. Output JSON only.",
                provider="gemini",
                max_tokens=2048,
            )
            count = len(re.findall(r"\b[\w’'-]+\b", str(fixed.get("narration", ""))))
            if lower <= count <= upper:
                break
        if not lower <= count <= upper:
            raise ValueError(f"Repaired section {kind} must contain {lower}-{upper} words, got {count}")
        fixed["kind"] = kind
        fixed["visual_prompts"] = section["visual_prompts"]
        repaired_sections.append(fixed)
    repaired["sections"] = repaired_sections
    return normalize_and_validate(repaired, source_pack)


def verify_with_one_repair(script: dict, source_pack: dict) -> tuple[dict, dict]:
    first = verify_script(script, source_pack)
    if first["status"] == "PASS":
        script["verification_status"] = "PASS"
        first["repairs_applied"] = []
        return script, first
    if not any(
        isinstance(claim, dict) and claim.get("status") != "PASS"
        for claim in first.get("claims", [])
    ):
        script["verification_status"] = "FAIL"
        first["repairs_applied"] = []
        return script, first
    repaired = repair_script(script, first, source_pack)
    second = verify_script(repaired, source_pack)
    second["repairs_applied"] = first.get("required_changes", [])
    second["initial_verification"] = first
    repaired["verification_status"] = second["status"]
    return repaired, second
