from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from .. import db
from ..models import GeneratedFile, Proposal, ProposalFeature, ProposalSection
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


@proposals_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        partner_name = request.form.get("partner_name", "").strip() or None
        industry = request.form.get("industry", "").strip()

        if not title or not customer_name:
            flash("Title and customer name are required.", "danger")
            return render_template("proposals/create.html")

        proposal = Proposal(
            title=title,
            customer_name=customer_name,
            partner_name=partner_name,
            industry=industry,
            created_by=current_user.id,
        )
        db.session.add(proposal)
        db.session.flush()

        # Initialize default sections snapshot per proposal
        default_sections = [
            ("intro", "Introduction"),
            ("platform", "Platform Overview"),
            ("scope", "Scope of Work"),
            ("appendix", "Appendix"),
        ]
        for idx, (key, title) in enumerate(default_sections):
            section = ProposalSection(
                proposal_id=proposal.id,
                section_key=key,
                title=title,
                content="",
                order_index=idx,
                is_enabled=True,
            )
            db.session.add(section)

        db.session.commit()
        flash("Proposal created.", "success")
        return redirect(url_for("proposals.edit", proposal_id=proposal.id))

    return render_template("proposals/create.html")


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
        proposal.updated_at = datetime.utcnow()

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
    return render_template(
        "proposals/edit.html",
        proposal=proposal,
        sections=sections,
        features=features,
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

    enabled_sections = [
        s for s in proposal.sections if s.is_enabled
    ]

    generator = ProposalWordGenerator()
    storage = LocalFileStorage()

    latest = (
        GeneratedFile.query.filter_by(proposal_id=proposal.id)
        .order_by(GeneratedFile.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else 1

    filename, abs_path = generator.render_proposal(proposal, enabled_sections, proposal.features, next_version)
    rel_path = storage.save(abs_path)

    record = GeneratedFile(
        proposal_id=proposal.id,
        filename=filename,
        file_path=rel_path,
        version_number=next_version,
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

