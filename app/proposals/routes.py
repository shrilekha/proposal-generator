from datetime import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from .. import db
from ..models import (
    GeneratedFile,
    ModuleSectionMap,
    Proposal,
    ProposalFeature,
    ProposalSection,
    ProposalVariable,
    SectionTemplate,
)
from ..constants import SUPPORTED_MODULES
from ..services.file_storage import LocalFileStorage
from ..services.word_generator import ProposalWordGenerator

proposals_bp = Blueprint("proposals", __name__, url_prefix="/proposals")


def require_admin():
    if not current_user.is_admin():
        abort(403)


@proposals_bp.route("/")
@login_required
def dashboard():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    query = Proposal.query
    if search:
        ilike = f"%{search}%"
        query = query.filter(
            db.or_(
                Proposal.title.ilike(ilike),
                Proposal.customer_name.ilike(ilike),
                Proposal.partner_name.ilike(ilike),
            )
        )
    if status:
        query = query.filter_by(status=status)

    proposals = query.order_by(Proposal.updated_at.desc()).all()
    return render_template("proposals/dashboard.html", proposals=proposals, search=search, status=status)


def _section_keys_for_modules(module_tags: list[str]) -> set[str]:
    """Return section_keys that should be enabled for the given module_tags (from ModuleSectionMap)."""
    if not module_tags:
        return set()
    rows = ModuleSectionMap.query.filter(ModuleSectionMap.module_tag.in_(module_tags)).all()
    return {r.section_key for r in rows}


@proposals_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        partner_name = request.form.get("partner_name", "").strip() or None
        industry = request.form.get("industry", "").strip()
        engagement_type = request.form.get("engagement_type", "DIRECT").strip() or "DIRECT"
        module_tags = request.form.getlist("module_tags")

        if not title or not customer_name:
            flash("Title and customer name are required.", "danger")
            return render_template("proposals/create.html", supported_modules=SUPPORTED_MODULES)

        proposal = Proposal(
            title=title,
            customer_name=customer_name,
            partner_name=partner_name,
            industry=industry,
            engagement_type=engagement_type,
            created_by=current_user.id,
        )
        db.session.add(proposal)
        db.session.flush()

        allowed_section_keys = _section_keys_for_modules(module_tags) if module_tags else None

        templates = SectionTemplate.query.order_by(SectionTemplate.order_index).all()
        if templates:
            for tmpl in templates:
                if allowed_section_keys is not None:
                    is_enabled = tmpl.section_key in allowed_section_keys
                else:
                    is_enabled = tmpl.is_default_enabled
                section = ProposalSection(
                    proposal_id=proposal.id,
                    section_key=tmpl.section_key,
                    title=tmpl.title,
                    content=tmpl.default_content or "",
                    order_index=tmpl.order_index,
                    is_enabled=is_enabled,
                )
                db.session.add(section)
        else:
            default_sections = [
                ("intro", "Introduction"),
                ("platform", "Platform Overview"),
                ("scope", "Scope of Work"),
                ("appendix", "Appendix"),
            ]
            for idx, (key, sec_title) in enumerate(default_sections):
                is_enabled = (key in allowed_section_keys) if allowed_section_keys else True
                section = ProposalSection(
                    proposal_id=proposal.id,
                    section_key=key,
                    title=sec_title,
                    content="",
                    order_index=idx,
                    is_enabled=is_enabled,
                )
                db.session.add(section)

        db.session.commit()
        flash("Proposal created.", "success")
        return redirect(url_for("proposals.edit", proposal_id=proposal.id))

    return render_template("proposals/create.html", supported_modules=SUPPORTED_MODULES)


def _get_proposal_or_404(proposal_id: int) -> Proposal:
    proposal = Proposal.query.get_or_404(proposal_id)
    return proposal


@proposals_bp.route("/<int:proposal_id>/edit", methods=["GET", "POST"])
@login_required
def edit(proposal_id):
    proposal = _get_proposal_or_404(proposal_id)

    if proposal.status == "locked" and not current_user.is_admin():
        flash("This proposal is locked and cannot be edited.", "warning")
        return redirect(url_for("proposals.view", proposal_id=proposal.id))

    if request.method == "POST":
        proposal.title = request.form.get("title", "").strip()
        proposal.customer_name = request.form.get("customer_name", "").strip()
        proposal.partner_name = request.form.get("partner_name", "").strip() or None
        proposal.industry = request.form.get("industry", "").strip()
        proposal.engagement_type = request.form.get("engagement_type", "DIRECT").strip() or "DIRECT"
        proposal.updated_at = datetime.utcnow()

        # Proposal variables (consulting-style)
        var_keys = request.form.getlist("variable_key")
        var_values = request.form.getlist("variable_value")
        existing_vars = {pv.variable_key: pv for pv in proposal.variables}
        for key, value in zip(var_keys, var_values):
            key = key.strip()
            if not key:
                continue
            if key in existing_vars:
                existing_vars[key].variable_value = value.strip()
            else:
                db.session.add(ProposalVariable(proposal_id=proposal.id, variable_key=key, variable_value=value.strip()))
        for pv in proposal.variables:
            if pv.variable_key not in [k.strip() for k in var_keys if k.strip()]:
                db.session.delete(pv)

        # Sections update (enable/disable, order, content)
        section_ids = request.form.getlist("section_id")
        for idx, section_id in enumerate(section_ids):
            section = ProposalSection.query.get(int(section_id))
            if not section or section.proposal_id != proposal.id:
                continue

            section.title = request.form.get(f"section_title_{section_id}", section.title)
            section.content = request.form.get(f"section_content_{section_id}", section.content)
            section.is_enabled = request.form.get(f"section_enabled_{section_id}") == "on"
            section.order_index = idx

        db.session.commit()
        flash("Proposal updated.", "success")
        return redirect(url_for("proposals.edit", proposal_id=proposal.id))

    sections = ProposalSection.query.filter_by(proposal_id=proposal.id).order_by(
        ProposalSection.order_index
    )
    features = ProposalFeature.query.filter_by(proposal_id=proposal.id).order_by(
        ProposalFeature.order_index
    )
    from ..constants import STANDARD_PROPOSAL_VARIABLE_KEYS
    variables_dict = {pv.variable_key: pv.variable_value for pv in proposal.variables}
    all_variable_keys = list(STANDARD_PROPOSAL_VARIABLE_KEYS) + [
        k for k in variables_dict if k not in STANDARD_PROPOSAL_VARIABLE_KEYS
    ]
    return render_template(
        "proposals/edit.html",
        proposal=proposal,
        sections=sections,
        features=features,
        variable_keys=all_variable_keys,
        variables_dict=variables_dict,
        standard_variable_keys=STANDARD_PROPOSAL_VARIABLE_KEYS,
    )


@proposals_bp.route("/<int:proposal_id>")
@login_required
def view(proposal_id):
    proposal = _get_proposal_or_404(proposal_id)
    sections = ProposalSection.query.filter_by(proposal_id=proposal.id).order_by(
        ProposalSection.order_index
    )
    features = ProposalFeature.query.filter_by(proposal_id=proposal.id).order_by(
        ProposalFeature.order_index
    )
    return render_template(
        "proposals/view.html",
        proposal=proposal,
        sections=sections,
        features=features,
    )


@proposals_bp.route("/<int:proposal_id>/clone", methods=["POST"])
@login_required
def clone(proposal_id):
    proposal = _get_proposal_or_404(proposal_id)

    clone = Proposal(
        title=f"{proposal.title} (Copy)",
        customer_name=proposal.customer_name,
        partner_name=proposal.partner_name,
        industry=proposal.industry,
        status="draft",
        engagement_type=getattr(proposal, "engagement_type", "DIRECT"),
        created_by=current_user.id,
    )
    db.session.add(clone)
    db.session.flush()

    for section in proposal.sections:
        new_section = ProposalSection(
            proposal_id=clone.id,
            section_key=section.section_key,
            title=section.title,
            content=section.content,
            order_index=section.order_index,
            is_enabled=section.is_enabled,
        )
        db.session.add(new_section)

    for feature in proposal.features:
        new_feature = ProposalFeature(
            proposal_id=clone.id,
            module_tag=feature.module_tag,
            feature_name=feature.feature_name,
            description=feature.description,
            order_index=feature.order_index,
        )
        db.session.add(new_feature)

    for pv in proposal.variables:
        db.session.add(ProposalVariable(
            proposal_id=clone.id,
            variable_key=pv.variable_key,
            variable_value=pv.variable_value,
        ))

    db.session.commit()
    flash("Proposal cloned.", "success")
    return redirect(url_for("proposals.edit", proposal_id=clone.id))


@proposals_bp.route("/<int:proposal_id>/lock", methods=["POST"])
@login_required
def lock(proposal_id):
    proposal = _get_proposal_or_404(proposal_id)
    if not current_user.is_admin():
        abort(403)
    proposal.status = "locked"
    db.session.commit()
    flash("Proposal locked.", "success")
    return redirect(url_for("proposals.view", proposal_id=proposal.id))


@proposals_bp.route("/<int:proposal_id>/unlock", methods=["POST"])
@login_required
def unlock(proposal_id):
    proposal = _get_proposal_or_404(proposal_id)
    if not current_user.is_admin():
        abort(403)
    proposal.status = "draft"
    db.session.commit()
    flash("Proposal unlocked.", "success")
    return redirect(url_for("proposals.edit", proposal_id=proposal.id))


@proposals_bp.route("/<int:proposal_id>/generate", methods=["POST"])
@login_required
def generate(proposal_id):
    proposal = _get_proposal_or_404(proposal_id)
    version_description = request.form.get("version_description", "").strip() or None

    generator = ProposalWordGenerator()
    storage = LocalFileStorage()

    latest = (
        GeneratedFile.query.filter_by(proposal_id=proposal.id)
        .order_by(GeneratedFile.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else 1

    try:
        filename, abs_path = generator.render_proposal(
            proposal, next_version, version_description=version_description
        )
    except Exception as exc:  # pragma: no cover - defensive UX path
        # Log the underlying error and show a friendly message instead of a 500.
        current_app.logger.exception("Failed to generate Word document for proposal %s", proposal.id)
        flash(
            "Failed to generate the Word document. Please verify the master template and try again.",
            "danger",
        )
        return redirect(url_for("proposals.view", proposal_id=proposal.id))
    rel_path = storage.save(abs_path)

    record = GeneratedFile(
        proposal_id=proposal.id,
        filename=filename,
        file_path=rel_path,
        version_number=next_version,
        version_description=version_description,
    )
    db.session.add(record)
    db.session.commit()

    flash("Word document generated.", "success")
    return redirect(url_for("proposals.view", proposal_id=proposal.id))


@proposals_bp.route("/files/<int:file_id>/download")
@login_required
def download_file(file_id):
    gen_file = GeneratedFile.query.get_or_404(file_id)
    storage = LocalFileStorage()
    abs_path = storage.get_absolute_path(gen_file.file_path)
    return send_file(abs_path, as_attachment=True, download_name=gen_file.filename)

