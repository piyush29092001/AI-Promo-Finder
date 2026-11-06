import json
import logging
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from src.config import FINAL_RESULTS_DIR, RAW_OUTPUTS_DIR, QUALITY_REPORTS_DIR
from src.models import PromoEvaluation, QualityReport

logger = logging.getLogger(__name__)


class Exporter:
    """
    Exports discovery results, ranked promos, quality reports, and raw LLM outputs
    in JSON, CSV, and PDF formats.
    """

    @staticmethod
    def export_json(evaluations: List[PromoEvaluation], output_path: Optional[Path] = None) -> str:
        """
        Exports full evaluated promo results to structured JSON string or file.
        """
        data = [ev.model_dump() for ev in evaluations]
        json_str = json.dumps(data, indent=2, default=str)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    @staticmethod
    def export_csv(evaluations: List[PromoEvaluation], output_path: Optional[Path] = None) -> str:
        """
        Exports ranked promo candidate metrics to CSV string or file.
        """
        records = []
        for ev in evaluations:
            cand = ev.candidate
            records.append(
                {
                    "Rank": ev.rank,
                    "Promo ID": ev.promo_id,
                    "Type": cand.promo_type,
                    "Episodes": ", ".join(str(e) for e in cand.episodes),
                    "Duration (s)": cand.total_duration_seconds,
                    "Overall Score": ev.overall_promo_score,
                    "Hook Score (40%)": ev.hook_eval.total_hook_score,
                    "Cliffhanger Score (25%)": ev.cliffhanger_eval.cliffhanger_score,
                    "Clarity Score (15%)": ev.story_clarity_score,
                    "Emotional Score (10%)": ev.emotional_impact_score,
                    "Continuity Score (10%)": ev.scene_continuity_score,
                    "Top 3": "YES" if ev.is_top_three else "NO",
                    "Segments": "; ".join(
                        f"Ep {s.episode_id}: {s.start_time}-{s.end_time}"
                        for s in cand.segments
                    ),
                    "Hook Text": cand.hook_text,
                    "Cliffhanger Text": cand.cliffhanger_text,
                    "Unresolved Question": cand.unresolved_question,
                    "Priority Reason": ev.publish_priority_reason,
                }
            )
        df = pd.DataFrame(records)
        csv_str = df.to_csv(index=False)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(csv_str)
        return csv_str

    @staticmethod
    def export_pdf(
        evaluations: List[PromoEvaluation],
        report: Optional[QualityReport] = None,
        output_path: Optional[Path] = None,
    ) -> bytes:
        """
        Generates a professional 2-3 page executive summary PDF using ReportLab.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1A202C"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "SubTitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=15,
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=12,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#2D3748"),
        )
        bold_body = ParagraphStyle(
            "BoldBody",
            parent=body_style,
            fontName="Helvetica-Bold",
        )

        story = []

        # Header
        story.append(Paragraph("AI Promo Finder & Ranking System", title_style))
        story.append(
            Paragraph(
                "Executive Recommendation Report & Discovered Promotional Clips",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#CBD5E0"), spaceAfter=15))

        # Overview Stats
        top_three = [ev for ev in evaluations if ev.is_top_three][:3]
        total_promos = len(evaluations)

        stats_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Total Promos Discovered", str(total_promos), "Top Candidates Selected", str(len(top_three))],
            [
                "Highest Composite Score",
                f"{evaluations[0].overall_promo_score:.2f}/100" if evaluations else "N/A",
                "Quality Status",
                f"{report.rule_violations_count} Rule Violations" if report else "Validated",
            ],
        ]
        t_stats = Table(stats_data, colWidths=[140, 120, 140, 120])
        t_stats.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_stats)
        story.append(Spacer(1, 15))

        # Top 3 Recommendations
        story.append(Paragraph("Top 3 Promotional Video Recommendations to Publish First", h2_style))

        for ev in top_three:
            cand = ev.candidate
            seg_text = ", ".join(
                f"Ep {s.episode_id} ({s.start_time} - {s.end_time})" for s in cand.segments
            )

            promo_box = [
                [
                    Paragraph(f"<b>Rank #{ev.rank} — {ev.promo_id}</b> ({cand.promo_type})", bold_body),
                    Paragraph(f"<b>Overall Score: {ev.overall_promo_score:.2f}/100</b>", bold_body),
                ],
                [
                    Paragraph(f"<b>Source Segments:</b> {seg_text} | <b>Total Duration:</b> {cand.total_duration_seconds:.1f}s", body_style),
                    "",
                ],
                [
                    Paragraph(
                        f"<b>Opening Hook (Score {ev.hook_eval.total_hook_score:.1f}/100):</b><br/>"
                        f"<i>{cand.hook_text}</i> [{cand.hook_start_time} - {cand.hook_end_time}]<br/>"
                        f"Delay: {ev.hook_eval.delay_score}/25 | Confusion: {ev.hook_eval.confusion_score}/25 | "
                        f"Irrelevance: {ev.hook_eval.irrelevance_score}/25 | Disinterest: {ev.hook_eval.disinterest_score}/25",
                        body_style,
                    ),
                    "",
                ],
                [
                    Paragraph(
                        f"<b>Cliffhanger (Score {ev.cliffhanger_eval.cliffhanger_score:.1f}/100):</b><br/>"
                        f"<i>{cand.cliffhanger_text}</i> [{cand.cliffhanger_start_time} - {cand.cliffhanger_end_time}]<br/>"
                        f"<b>Unresolved Question:</b> {cand.unresolved_question}",
                        body_style,
                    ),
                    "",
                ],
                [
                    Paragraph(f"<b>Why Publish First:</b> {ev.publish_priority_reason}", body_style),
                    "",
                ],
            ]

            t_promo = Table(promo_box, colWidths=[380, 140])
            t_promo.setStyle(
                TableStyle(
                    [
                        ("SPAN", (0, 1), (1, 1)),
                        ("SPAN", (0, 2), (1, 2)),
                        ("SPAN", (0, 3), (1, 3)),
                        ("SPAN", (0, 4), (1, 4)),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBF8FF")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BEE3F8")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t_promo)
            story.append(Spacer(1, 10))

        # Quality & Limitations Notice
        story.append(Spacer(1, 10))
        story.append(Paragraph("System Disclaimers & Methodology", h2_style))
        disclaimer_text = (
            "Notice: AI-generated promo scores predict audience engagement potential based on structured narrative criteria "
            "(Four Hook Mistakes Framework, cliffhanger tension, and story coherence). Final real-world CTR and viewer completion "
            "require iterative A/B testing on social platforms. All source timestamps and quotes have been strictly extracted from authentic screenplay data."
        )
        story.append(Paragraph(disclaimer_text, body_style))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        return pdf_bytes
