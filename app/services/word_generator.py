"""
Orchestrates loading the master .docx template and rendering a proposal document.
Template is layout-only; all content comes from the database (ProposalSection, ProposalFeature, ProposalVariable).
"""
import os
from datetime import datetime

from docxtpl import DocxTemplate
from flask import current_app

from ..models import GeneratedFile, Proposal, ProposalFeature, ProposalSection, ProposalVariable
from ..models import ENGAGEMENT_DIRECT, ENGAGEMENT_PARTNER_LED
from .file_storage import LocalFileStorage


class ProposalWordGenerator:
    def __init__(self) -> None:
        configured = current_app.config.get("PROPOSAL_TEMPLATE_PATH")
        if configured and os.path.isabs(configured):
            template_path = configured
        else:
            rel = configured or os.path.join("templates", "master_proposal_template.docx")
            template_path = os.path.join(current_app.root_path, "..", rel)

        self.template_path = template_path

    def render_proposal(
        self,
        proposal: Proposal,
        version_number: int,
        version_description: str | None = None,
    ) -> tuple[str, str]:
        storage = LocalFileStorage()
        output_path = storage.build_output_path(proposal.customer_name, version_number)

        doc = DocxTemplate(self.template_path)

        # Sections: only enabled, sorted by order_index (layout-only; content from DB)
        sections = (
            ProposalSection.query.filter_by(proposal_id=proposal.id, is_enabled=True)
            .order_by(ProposalSection.order_index)
            .all()
        )
        sections_ctx = [
            {
                "title": s.title,
                "content": s.content or "",
                "section_key": s.section_key,
                "order_index": s.order_index,
            }
            for s in sections
        ]

        # Features: sorted by order_index (for appendix)
        features = (
            ProposalFeature.query.filter_by(proposal_id=proposal.id)
            .order_by(ProposalFeature.order_index)
            .all()
        )
        features_ctx = [
            {
                "module_tag": f.module_tag or "",
                "feature_name": f.feature_name or "",
                "description": f.description or "",
                "order_index": f.order_index,
            }
            for f in features
        ]

        # Version timeline (all past generated versions for Change Log)
        version_timeline = [
            {
                "version_number": g.version_number,
                "generated_date": g.generated_at.strftime("%d %B %Y") if g.generated_at else "",
                "description": g.version_description or "",
            }
            for g in GeneratedFile.query.filter_by(proposal_id=proposal.id)
            .order_by(GeneratedFile.version_number.asc())
            .all()
        ]
        # Append current version being generated
        version_timeline.append({
            "version_number": version_number,
            "generated_date": datetime.utcnow().strftime("%d %B %Y"),
            "description": version_description or "",
        })

        # Proposal variables (consulting-style) – flattened so template can use {{ txn_volume }}
        variables = {
            pv.variable_key: pv.variable_value or ""
            for pv in ProposalVariable.query.filter_by(proposal_id=proposal.id).all()
        }

        # Engagement line for title block
        if proposal.engagement_type == ENGAGEMENT_PARTNER_LED and proposal.partner_name:
            proposal_to_line = f"Proposal to {proposal.partner_name} for {proposal.customer_name}"
        else:
            proposal_to_line = f"Proposal to {proposal.customer_name}"

        context = {
            "proposal_title": proposal.title or "",
            "customer_name": proposal.customer_name or "",
            "partner_name": proposal.partner_name or "",
            "industry": proposal.industry or "",
            "engagement_type": getattr(proposal, "engagement_type", None) or ENGAGEMENT_DIRECT,
            "proposal_to_line": proposal_to_line,
            "generated_date": datetime.utcnow().strftime("%d %B %Y"),
            "version_number": version_number,
            "sections": sections_ctx,
            "features": features_ctx,
            "version_timeline": version_timeline,
        }
        # Flatten proposal variables into context for {{ txn_volume }} etc. (backward compatible if missing)
        context.update(variables)

        doc.render(context)
        doc.save(output_path)

        filename = os.path.basename(output_path)
        return filename, output_path
