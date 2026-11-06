"""Trusted-host packaging for a bounded Metadata consumption trace.

This explains selected field moves, not independent Word extraction fidelity.
No document values are duplicated in the persisted evidence.
"""

import hashlib
import json
import re

from .content_processing import recognized_metadata_block
from .pdf_metadata import normalize_pdf_metadata_value

FIELDS = {
    "opdiv": "opdiv",
    "agency": "agency",
    "subagency": "subagency",
    "subagency2": "subagency2",
    "opportunityname": "title",
    "opportunitynumber": "number",
    "applicationdeadline": "application_deadline",
    "metadataauthor": "author",
    "metadatasubject": "subject",
    "metadatakeywords": "keywords",
}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _ordinal(value):
    return type(value) is int and value >= 0


def _check_consumption(trace):
    """Validate recorded evidence, without replaying or broadening recognition."""
    if (
        trace.get("rule") != "IMPORT-063"
        or trace.get("stage") != "processed-html-to-content-copy"
        or not all(_hash(trace.get(key)) for key in ("before_sha256", "after_sha256"))
        or type(trace.get("flattened_links")) is not list
    ):
        raise ValueError("Metadata consumption schema changed")
    blocks = trace["blocks"]
    if trace.get("selected_block") != (len(blocks) - 1 if blocks else None) or (
        blocks and type(trace["selected_block"]) is not int
    ):
        raise ValueError("Metadata block selection changed")
    previous_heading = -1
    selected_fields = {}
    for ordinal, block in enumerate(blocks):
        if (
            type(block) is not dict
            or type(block.get("ordinal")) is not int
            or block["ordinal"] != ordinal
            or not _ordinal(block.get("heading_ordinal"))
            or block["heading_ordinal"] <= previous_heading
            or not _hash(block.get("source_sha256"))
            or type(block.get("fields")) is not list
        ):
            raise ValueError("Metadata block schema changed")
        previous_heading = previous_element = block["heading_ordinal"]
        seen = {}
        for event in block["fields"]:
            if (
                type(event) is not dict
                or not _ordinal(event.get("element_ordinal"))
                or event["element_ordinal"] <= previous_element
                or not _hash(event.get("source_sha256"))
                or event.get("kind") not in {"blank", "field"}
            ):
                raise ValueError("Metadata event schema changed")
            previous_element = event["element_ordinal"]
            if event["kind"] == "field":
                key = event.get("key")
                if (
                    key not in FIELDS
                    or type(event.get("first")) is not bool
                    or event["first"] != (key not in seen)
                    or not _hash(event.get("value_sha256"))
                ):
                    raise ValueError("Metadata field selection changed")
                seen.setdefault(key, event)
        if not seen:
            raise ValueError("Metadata block lacks recognition evidence")
        selected_fields = seen
    previous_link = -1
    for link in trace["flattened_links"]:
        if (
            type(link) is not dict
            or not _ordinal(link.get("element_ordinal"))
            or link["element_ordinal"] <= previous_link
            or not all(_hash(link.get(key)) for key in ("before_sha256", "text_sha256"))
            or not blocks
        ):
            raise ValueError("Metadata link schema changed")
        previous_link = link["element_ordinal"]
    return selected_fields


def package_trace(source_sha256, conversion_html, processed_soup, trace, nofo):
    fields = recognized_metadata_block(processed_soup)
    destinations = []
    if fields is not None:
        selected = trace[0]["blocks"][trace[0]["selected_block"]]
        for key, field in FIELDS.items():
            actual = getattr(nofo, field)
            value = fields.get(key)
            origin = next(
                (
                    event
                    for event in selected["fields"]
                    if event.get("key") == key and event["first"]
                ),
                None,
            )
            if value is not None and (
                origin is None or origin["value_sha256"] != digest(value)
            ):
                raise ValueError("Metadata trace does not match its extraction source")
            if field in {"author", "subject", "keywords"} and value is not None:
                value = normalize_pdf_metadata_value(value)
            # Nonempty source values, plus PDF-field blanks, have direct
            # documented expected values. Missing/defaulted other fields do not.
            assessable = value is not None and (
                bool(value)
                or field
                in {
                    "author",
                    "subject",
                    "keywords",
                    "agency",
                    "subagency",
                    "subagency2",
                }
            )
            destinations.append(
                {
                    "source_key": key,
                    "source_block": selected["ordinal"],
                    "source_element": origin["element_ordinal"] if origin else None,
                    "destination": field,
                    "expected_sha256": digest(value) if assessable else None,
                    "saved_sha256": digest(actual),
                    "status": (
                        ("pass" if value == actual else "fail")
                        if assessable
                        else "not_assessed"
                    ),
                    "rules": ["IMPORT-041", "IMPORT-010"]
                    + (
                        ["IMPORT-048"]
                        if field in {"author", "subject", "keywords"}
                        else []
                    ),
                }
            )
    return json.dumps(
        {
            "schema": 1,
            "coverage": "recognized-metadata-only",
            "source_sha256": source_sha256,
            "conversion_sha256": digest(conversion_html),
            "trace": trace,
            "destinations": destinations,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def check_trace(run):
    if not run.metadata_trace_json:
        return None
    data = json.loads(run.metadata_trace_json)
    if (
        type(data) is not dict
        or data.get("schema") != 1
        or data.get("coverage") != "recognized-metadata-only"
        or type(data.get("trace")) is not list
        or len(data["trace"]) != 1
        or type(data["trace"][0]) is not dict
        or type(data["trace"][0].get("blocks")) is not list
        or type(data.get("destinations")) is not list
        or data["source_sha256"] != run.source_sha256
        or data["conversion_sha256"] != digest(run.conversion_html)
    ):
        raise ValueError("Metadata trace binding changed")
    origins = _check_consumption(data["trace"][0])
    expected_fields = set(FIELDS.values()) if data["trace"][0]["blocks"] else set()
    seen = set()
    for row in data["destinations"]:
        if (
            type(row) is not dict
            or row.get("source_key") not in FIELDS
            or row.get("destination") != FIELDS[row["source_key"]]
            or row["destination"] in seen
        ):
            raise ValueError("Metadata destination schema changed")
        seen.add(row["destination"])
        expected = row.get("expected_sha256")
        origin = origins.get(row["source_key"])
        if (
            (expected is not None and not _hash(expected))
            or row.get("source_block") != data["trace"][0]["selected_block"]
            or row.get("source_element")
            != (origin["element_ordinal"] if origin else None)
            or (origin is None and expected is not None)
            or (
                origin is not None
                and expected is not None
                and row["destination"] not in {"author", "subject", "keywords"}
                and expected != origin["value_sha256"]
            )
            or row.get("rules")
            != ["IMPORT-041", "IMPORT-010"]
            + (
                ["IMPORT-048"]
                if row["destination"] in {"author", "subject", "keywords"}
                else []
            )
        ):
            raise ValueError("Metadata destination provenance changed")
        saved = digest(getattr(run.nofo, row["destination"]))
        status = (
            "not_assessed"
            if expected is None
            else "pass" if expected == saved else "fail"
        )
        if row["saved_sha256"] != saved or row.get("status") != status:
            raise ValueError("Metadata destination binding changed")
    if seen != expected_fields:
        raise ValueError("Metadata destination coverage changed")
    return data
