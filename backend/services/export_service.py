import csv
import io
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from models.report import Report


def to_json(report: Report) -> bytes:
    payload = {
        "report_id": report.report_number,
        "case_id": report.case_id,
        "status": report.status.value,
        "readiness_score": report.readiness_score,
        "readiness_level": report.readiness_level.value,
        "missing_items": report.missing_items,
        "body": report.body,
    }
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def to_csv(report: Report) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["field", "value"])
    writer.writerow(["report_id", report.report_number])
    writer.writerow(["case_id", report.case_id])
    writer.writerow(["status", report.status.value])
    writer.writerow(["readiness_score", report.readiness_score])
    writer.writerow(["readiness_level", report.readiness_level.value])
    writer.writerow(["platform", report.body.get("platform")])
    writer.writerow(["target_username", (report.body.get("target") or {}).get("username")])
    writer.writerow(["violation_category", report.body.get("violation_category")])
    for ev in report.body.get("evidence", []):
        writer.writerow([f"evidence:{ev['evidence_id']}", f"{ev['source_url']} | sha256={ev['sha256']}"])
    return buf.getvalue().encode("utf-8")


def to_pdf(report: Report) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    body = report.body
    flow = [
        Paragraph(f"REPORT ID: {report.report_number}", styles["Title"]),
        Paragraph(f"CASE: {body.get('case_number')}", styles["Normal"]),
        Paragraph(f"PLATFORM: {body.get('platform')}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"TARGET: {(body.get('target') or {}).get('username')}", styles["Heading2"]),
        Paragraph(f"Profile URL: {(body.get('target') or {}).get('profile_url')}", styles["Normal"]),
        Spacer(1, 8),
        Paragraph("CONTENT URL(S)", styles["Heading3"]),
        Paragraph(", ".join(body.get("content_urls", [])) or "N/A", styles["Normal"]),
        Spacer(1, 8),
        Paragraph("VIOLATION CATEGORY", styles["Heading3"]),
        Paragraph(str(body.get("violation_category")), styles["Normal"]),
        Spacer(1, 8),
        Paragraph("RELEVANT POLICY", styles["Heading3"]),
        Paragraph(str((body.get("relevant_policy") or {}).get("reason")), styles["Normal"]),
        Spacer(1, 8),
        Paragraph("DESCRIPTION", styles["Heading3"]),
        Paragraph(body.get("description", ""), styles["Normal"]),
        Spacer(1, 8),
        Paragraph("EVIDENCE", styles["Heading3"]),
    ]
    for ev in body.get("evidence", []):
        flow.append(Paragraph(f"{ev['evidence_id']} — {ev['type']} — {ev['source_url']} — SHA-256: {ev['sha256']} — {ev['verification_status']}", styles["Normal"]))
    flow += [
        Spacer(1, 8),
        Paragraph("WHY THE CONTENT MAY VIOLATE THE POLICY", styles["Heading3"]),
        Paragraph(str(body.get("why_may_violate")), styles["Normal"]),
        Spacer(1, 8),
        Paragraph("REQUEST FOR REVIEW", styles["Heading3"]),
        Paragraph(body.get("request_for_review", ""), styles["Normal"]),
        Spacer(1, 8),
        Paragraph(f"REVIEWER: {body.get('reviewer')}", styles["Normal"]),
        Paragraph(f"GENERATED AT: {body.get('generated_at')}", styles["Normal"]),
        Paragraph(f"READINESS: {report.readiness_level.value} ({report.readiness_score}%)", styles["Normal"]),
        Spacer(1, 16),
        Paragraph(body.get("disclaimer", ""), styles["Italic"]),
    ]
    doc.build(flow)
    return buf.getvalue()
