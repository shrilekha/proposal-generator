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


class Proposal(db.Model):
    __tablename__ = "proposals"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    partner_name = db.Column(db.String(255))
    industry = db.Column(db.String(255))
    status = db.Column(db.String(32), default="draft")  # draft / locked
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

    proposal = db.relationship("Proposal", back_populates="generated_files")

