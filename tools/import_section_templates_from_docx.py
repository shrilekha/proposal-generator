import os
import sys
from html import escape

from docx import Document

# Ensure the project root (containing the `app` package) is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app, db
from app.models import SectionTemplate
from config import get_config


HEADING_TO_SECTION_KEY = {
    "Introduction": "introduction",
    "Platform Overview": "platform_overview",
    "Platform Differentiation": "platform_differentiation",
    "Scope of Work": "scope_of_engagement",
    "Inventory": "inventory",
    "Applications in Scope": "applications_in_scope",
    "Features": "functional_features",
    "Solution Approach": "solution_approach",
    "Implementation Approach": "implementation_approach",
    "Deliverables": "deliverables",
    "Deployment Architecture": "deployment_architecture",
    "Hardware Requirements": "hardware_requirements",
    "Training": "training",
    "Post Implementation Support": "post_implementation_support",
    "Risk Management": "risk_management",
    "Pricing": "pricing",
    "Terms & Conditions": "terms_conditions",
    "Appendix": "appendix_features",
}


def get_template_path() -> str:
    """
    Resolve the path to template.docx.
    We reuse the app config's PROPOSAL_TEMPLATE_PATH so this script
    follows the same convention as the Word generator.
    """
    cfg = get_config()
    return getattr(cfg, "CONTENT_SEED_TEMPLATE_PATH")


def parse_sections_from_docx(doc_path: str) -> dict[str, list[str]]:
    """
    Parse the Word document and group paragraph texts under each mapped heading.
    Returns a dict: section_key -> list of paragraph strings.
    """
    document = Document(doc_path)
    sections: dict[str, list[str]] = {v: [] for v in HEADING_TO_SECTION_KEY.values()}

    current_key: str | None = None

    heading_text_to_key = {
        h.lower(): key for h, key in HEADING_TO_SECTION_KEY.items()
    }

    for para in document.paragraphs:
        text = (para.text or "").strip()
        if not text:
            # Preserve blank lines inside a section as paragraph breaks.
            if current_key is not None:
                sections[current_key].append("")
            continue

        # First, if the paragraph text itself matches a known heading (case-insensitive),
        # treat it as a heading regardless of style. This is more robust for templates
        # where only the first heading uses a Heading style.
        lowered = text.lower()
        if lowered in heading_text_to_key:
            current_key = heading_text_to_key[lowered]
            continue

        style_name = getattr(para.style, "name", "") or ""
        # Fallback: treat any Heading style whose text matches one of our headings
        # as the start of a new section.
        if style_name.startswith("Heading"):
            mapped_key = HEADING_TO_SECTION_KEY.get(text)
            if mapped_key:
                current_key = mapped_key
                continue

        if current_key is not None:
            sections[current_key].append(text)

    return sections


def paragraphs_to_html(paragraphs: list[str]) -> str:
    """
    Convert plain paragraph texts into simple HTML suitable for Quill's initial content.
    We keep it intentionally minimal: each non-empty paragraph becomes a <p>.
    """
    html_parts: list[str] = []
    for p in paragraphs:
        if not p.strip():
            continue
        html_parts.append(f"<p>{escape(p)}</p>")
    return "\n\n".join(html_parts)


def import_into_section_templates(sections: dict[str, list[str]]) -> None:
    """
    Upsert SectionTemplate rows from the parsed sections.
    For each mapped section_key:
      - if a row exists, update title and default_content
      - otherwise, create a new row with a sequential order_index.
    """
    existing_templates = {
        st.section_key: st for st in SectionTemplate.query.all()
    }
    # Start order_index after the current max.
    max_order = 0
    if existing_templates:
        max_order = max(st.order_index for st in existing_templates.values())

    for heading, section_key in HEADING_TO_SECTION_KEY.items():
        paragraphs = sections.get(section_key, [])
        html_content = paragraphs_to_html(paragraphs)

        tmpl = existing_templates.get(section_key)
        if tmpl is None:
            max_order += 1
            tmpl = SectionTemplate(
                section_key=section_key,
                title=heading,
                default_content=html_content,
                order_index=max_order,
                is_default_enabled=True,
            )
            db.session.add(tmpl)
        else:
            tmpl.title = heading
            tmpl.default_content = html_content

    db.session.commit()


def main() -> None:
    doc_path = get_template_path()
    if not os.path.exists(doc_path):
        raise SystemExit(f"template.docx not found at: {doc_path}")

    print(f"Reading template from: {doc_path}")
    sections = parse_sections_from_docx(doc_path)

    app = create_app()
    with app.app_context():
        import_into_section_templates(sections)

    print("SectionTemplate rows updated from template.docx.")


if __name__ == "__main__":
    main()

