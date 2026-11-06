"""Revision-bound synthetic review evidence; no acceptance or content editing."""

import hashlib
import json

from django.db import transaction

from . import design_pilot_host as host
from .design_candidate import DesignRequestError
from .design_fidelity import inspect as inspect_fidelity
from .metadata_provenance import check_trace
from .models import DesignPilotReviewDecision
from .nofo import (
    find_broken_links,
    find_endnote_issues,
    find_incorrectly_nested_heading_levels,
    find_same_or_higher_heading_levels_consecutive,
)
from .pdf_metadata import PDF_METADATA_FIELDS, is_missing_pdf_metadata_value


def _finding(
    key,
    rule,
    status,
    severity,
    target,
    evidence,
    action,
    section=None,
    evidence_digest="",
):
    data = dict(
        id=key,
        rule=rule,
        status=status,
        severity=severity,
        target=target,
        evidence=evidence,
        action=action,
        section_id=str(section.pk) if section else "",
        human_required=severity in {"blocking", "warning"},
        evidence_digest=evidence_digest,
    )
    data["digest"] = hashlib.sha256(
        json.dumps(data, sort_keys=True).encode()
    ).hexdigest()
    return data


def report(run):
    """Recheck current native HTML and reuse offline Builder diagnostics only."""
    revision, html = host.review_artifact(run)
    findings = [
        _finding(
            "baseline",
            "DESIGN-007",
            "pass",
            "info",
            "Imported content",
            "Stored source hash and exact imported record snapshot match. Only declared presentation changes are permitted.",
            "This does not verify source-to-import fidelity.",
        ),
        _finding(
            "source-import",
            "DESIGN-001",
            "not_assessed",
            "blocking",
            "Source and import",
            "Original Word bytes and conversion output are retained. Differences have not been reconciled against import rules.",
            "Source-to-import verification is still needed before acceptance. Acknowledgment cannot replace that check.",
        ),
        _finding(
            "assets-links",
            "DESIGN-006",
            "not_assessed",
            "blocking",
            "Assets and links",
            "The HTML preview filters external navigation and resources. Internal-link diagnostics do not prove complete link or asset fidelity.",
            "Complete technical asset/link verification before acceptance. Do not enable network access to clear this finding.",
        ),
        _finding(
            "pdf",
            "DESIGN-008",
            "unsupported",
            "info",
            "PDF pagination",
            "DocRaptor is disabled in lower environments. Local HTML does not verify PDF pagination.",
            "No local PDF is needed. This capability limit is not a blocker.",
        ),
    ]
    for evidence in inspect_fidelity(run.conversion_html, html):
        findings.append(
            _finding(
                f"fidelity-{evidence['id']}",
                "DESIGN-001",
                evidence["status"],
                (
                    "blocking"
                    if evidence["status"] == "fail" or evidence["id"] == "inventory"
                    else "info"
                ),
                evidence["target"],
                evidence["evidence"],
                evidence["action"],
                evidence_digest=evidence.get("input_digest", ""),
            )
        )
    provenance = check_trace(run)
    findings.append(
        _finding(
            "metadata-trace",
            "IMPORT-063",
            "not_assessed",
            "info",
            "Metadata provenance",
            (
                f"Recognized Metadata blocks recorded: {len(provenance['trace'][0]['blocks'])}. Selected block (zero-based): {provenance['trace'][0]['selected_block']}. Flattened dead-target links: {len(provenance['trace'][0]['flattened_links'])}. Trace SHA-256: {hashlib.sha256(run.metadata_trace_json.encode()).hexdigest()}."
                if provenance
                else "This candidate predates Metadata provenance capture; no trace was reconstructed."
            ),
            "This records executed field consumption only, not independent Word extraction or complete source fidelity.",
        )
    )
    for row in provenance["destinations"] if provenance else []:
        findings.append(
            _finding(
                f"metadata-destination-{row['destination']}",
                "IMPORT-041",
                row["status"],
                "blocking" if row["status"] == "fail" else "info",
                f"Metadata destination: {row['destination']}",
                f"Source key: {row['source_key']}. Processed-source block: {row['source_block']}; element: {row['source_element']}. Saved field bound to this candidate. Result: {row['status']}.",
                "Defaults/missing sources remain not assessed. A matching field is not proof that all Word content was extracted.",
            )
        )
    checks = [
        (
            "headings",
            "DESIGN-006",
            lambda: find_same_or_higher_heading_levels_consecutive(run.nofo)
            + find_incorrectly_nested_heading_levels(run.nofo),
        ),
        ("links", "DESIGN-006", lambda: find_broken_links(run.nofo)),
        ("endnotes", "DESIGN-006", lambda: find_endnote_issues(run.nofo)),
    ]
    for name, rule, check in checks:
        try:
            issues = check()
        except (ValueError, KeyError, IndexError, TypeError):
            findings.append(
                _finding(
                    name,
                    rule,
                    "not_assessed",
                    "blocking",
                    name.capitalize(),
                    "The existing diagnostic could not assess this saved structure.",
                    "Correct the source structure and import a fresh synthetic copy; this is not a pass.",
                )
            )
            continue
        if not issues:
            findings.append(
                _finding(
                    name,
                    rule,
                    "pass",
                    "info",
                    name.capitalize(),
                    "The existing offline diagnostic reported no issues in its supported scope.",
                    "This is not a complete structure or accessibility assessment.",
                )
            )
        for i, issue in enumerate(issues):
            subsection = issue.get("subsection")
            section = issue.get("section") or (
                subsection.section if subsection else None
            )
            evidence = (
                issue.get("error")
                or issue.get("message")
                or f"Unresolved internal destination: {issue.get('link_href', '')}"
            )
            findings.append(
                _finding(
                    f"{name}-{i}",
                    rule,
                    "fail",
                    "blocking",
                    (
                        subsection.name
                        if subsection
                        else section.name if section else name
                    ),
                    evidence,
                    "Review the affected content. Substantive corrections require a corrected source and fresh import in this slice.",
                    section,
                )
            )
    for field, label in PDF_METADATA_FIELDS:
        if is_missing_pdf_metadata_value(getattr(run.nofo, field)):
            findings.append(
                _finding(
                    f"metadata-{field}",
                    "DESIGN-007",
                    "fail",
                    "blocking",
                    label,
                    f"{label} is missing or contains a placeholder.",
                    "Supply the intended value in a corrected source. Do not invent it.",
                )
            )
    for i, warning in enumerate(run.warnings):
        findings.append(
            _finding(
                f"import-warning-{i}",
                "DESIGN-001",
                "not_assessed",
                "warning",
                "Word conversion",
                str(warning),
                "Compare the retained content with the source; record why this nonblocking warning can be acknowledged.",
            )
        )
    decisions = {
        (d.finding_id, d.finding_digest): d
        for d in run.review_decisions.filter(revision=revision).select_related("actor")
    }
    for item in findings:
        item["decision"] = decisions.get((item["id"], item["digest"]))
        item["status_label"] = {
            "pass": "Passed",
            "fail": "Needs correction",
            "not_assessed": "Not assessed",
            "unsupported": "Not available",
        }[item["status"]]
        item["severity_label"] = {
            "info": "Information",
            "blocking": "Blocking",
            "warning": "Warning",
        }[item["severity"]]
    # Changes to finding definitions/diagnostics must also stale a posted form,
    # even if the native HTML revision happens to stay unchanged.
    evidence_revision = hashlib.sha256(
        json.dumps([(f["id"], f["digest"]) for f in findings], sort_keys=True).encode()
    ).hexdigest()
    return dict(
        revision=revision,
        evidence_revision=evidence_revision,
        findings=findings,
        blockers=sum(f["severity"] == "blocking" for f in findings),
        open_warnings=sum(
            f["severity"] == "warning" and not f["decision"] for f in findings
        ),
        status="Ready for review",
        acceptance_available=False,
        changes=host.snapshot(run).read()["changes"],
    )


def acknowledge(user, candidate_id, command):
    fields = {
        "expected_revision",
        "evidence_revision",
        "finding_id",
        "finding_digest",
        "reason",
    }
    if (
        not isinstance(command, dict)
        or set(command) != fields
        or any(not isinstance(v, str) for v in command.values())
    ):
        raise DesignRequestError(
            "Use the current review form to acknowledge a warning."
        )
    if not command["reason"].strip() or len(command["reason"]) > 500:
        raise DesignRequestError("Explain the acknowledgment in 1 to 500 characters.")
    with transaction.atomic():
        run = host.owned_candidate(user, candidate_id)
        current = report(run)
        if (
            command["expected_revision"] != current["revision"]
            or command["evidence_revision"] != current["evidence_revision"]
        ):
            raise DesignRequestError(
                "This candidate or its checks changed. Return to review before acknowledging again."
            )
        finding = next(
            (
                f
                for f in current["findings"]
                if f["id"] == command["finding_id"]
                and f["digest"] == command["finding_digest"]
            ),
            None,
        )
        if finding is None or finding["severity"] != "warning":
            raise DesignRequestError(
                "Only nonblocking warnings can be acknowledged. Blocking findings require correction and rechecking."
            )
        decision, created = DesignPilotReviewDecision.objects.get_or_create(
            candidate=run,
            revision=current["revision"],
            finding_id=finding["id"],
            finding_digest=finding["digest"],
            defaults={
                "actor": host.current_owner(user),
                "reason": command["reason"].strip(),
            },
        )
        # Retries never rewrite the original human's reason/time.
        return decision
