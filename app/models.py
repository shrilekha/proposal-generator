from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="presales")  # admin / presales
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    proposals = db.relationship("Proposal", back_populates="creator", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role == "admin"


# Engagement type: DIRECT = VuNet to customer; PARTNER_LED = VuNet via partner
ENGAGEMENT_DIRECT = "DIRECT"
ENGAGEMENT_PARTNER_LED = "PARTNER_LED"


class Proposal(db.Model):
    __tablename__ = "proposals"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    partner_name = db.Column(db.String(255))
    industry = db.Column(db.String(255))
    status = db.Column(db.String(32), default="draft")  # draft / locked
    engagement_type = db.Column(db.String(32), default=ENGAGEMENT_DIRECT, nullable=False)  # DIRECT | PARTNER_LED
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    creator = db.relationship("User", back_populates="proposals")
    sections = db.relationship(
        "ProposalSection",
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="ProposalSection.order_index",
    )
    features = db.relationship(
        "ProposalFeature",
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="ProposalFeature.order_index",
    )
    generated_files = db.relationship(
        "GeneratedFile",
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="GeneratedFile.generated_at.desc()",
    )
    variables = db.relationship(
        "ProposalVariable",
        back_populates="proposal",
        cascade="all, delete-orphan",
    )


class ProposalSection(db.Model):
    __tablename__ = "proposal_sections"

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), nullable=False)
    section_key = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)  # rich text HTML
    order_index = db.Column(db.Integer, nullable=False, default=0)
    is_enabled = db.Column(db.Boolean, default=True)

    proposal = db.relationship("Proposal", back_populates="sections")


class ProposalFeature(db.Model):
    __tablename__ = "proposal_features"

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), nullable=False)
    module_tag = db.Column(db.String(128), nullable=False)
    feature_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, nullable=False, default=0)

    proposal = db.relationship("Proposal", back_populates="features")


class GeneratedFile(db.Model):
    __tablename__ = "generated_files"

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), nullable=False)
    filename = db.Column(db.String(512), nullable=False)
    file_path = db.Column(db.String(1024), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    version_number = db.Column(db.Integer, nullable=False, default=1)
    version_description = db.Column(db.String(512))  # e.g. "initial draft", "updated scope"

    proposal = db.relationship("Proposal", back_populates="generated_files")


class ProposalVariable(db.Model):
    """Consulting-style proposal variables (e.g. txn_volume, commitment_tenure). Exposed in docxtpl context."""
    __tablename__ = "proposal_variables"

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey("proposals.id"), nullable=False)
    variable_key = db.Column(db.String(128), nullable=False)
    variable_value = db.Column(db.Text)

    proposal = db.relationship("Proposal", back_populates="variables")

    __table_args__ = (db.UniqueConstraint("proposal_id", "variable_key", name="uq_proposal_variable"),)


class ModuleSectionMap(db.Model):
    """Maps module_tag to section_key. Used to auto-enable sections when modules are selected."""
    __tablename__ = "module_section_map"

    id = db.Column(db.Integer, primary_key=True)
    module_tag = db.Column(db.String(128), nullable=False, index=True)
    section_key = db.Column(db.String(128), nullable=False, index=True)


class SectionTemplate(db.Model):
    """
    Admin-defined default sections that are copied into each new proposal
    as a starting snapshot.
    """

    __tablename__ = "section_templates"

    id = db.Column(db.Integer, primary_key=True)
    section_key = db.Column(db.String(64), nullable=False, unique=True)
    title = db.Column(db.String(255), nullable=False)
    default_content = db.Column(db.Text)  # rich text HTML
    order_index = db.Column(db.Integer, nullable=False, default=0)
    is_default_enabled = db.Column(db.Boolean, default=True)

