from typing import Iterable

from docxtpl import DocxTemplate
from flask import current_app

from ..models import Proposal, ProposalFeature, ProposalSection
from .file_storage import LocalFileStorage


class ProposalWordGenerator:
    """
    Orchestrates loading the master .docx template and rendering a proposal document.
    """

    def __init__(self) -> None:
        self.template_path = current_app.config.get(
            "PROPOSAL_TEMPLATE_PATH",
            "templates/master_proposal_template.docx",
        )

    def render_proposal(
        self,
        proposal: Proposal,
        sections: Iterable[ProposalSection],
        features: Iterable[ProposalFeature],
        version_number: int,
    ) -> tuple[str, str]:
        storage = LocalFileStorage()
        output_path = storage.build_output_path(proposal.customer_name, version_number)

        doc = DocxTemplate(self.template_path)

        context = {
            "customer_name": proposal.customer_name,
            "partner_name": proposal.partner_name or "",
            "industry": proposal.industry or "",
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                }
                for s in sections
                if s.is_enabled
            ],
            "features": [
                {
                    "module_tag": f.module_tag,
                    "feature_name": f.feature_name,
                    "description": f.description,
                }
                for f in features
            ],
        }

        doc.render(context)
        doc.save(output_path)

        filename = output_path.split("/")[-1].split("\\")[-1]
        return filename, output_path

