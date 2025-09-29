from sqlalchemy import Column, String, DateTime, ForeignKey, Text, BigInteger, CheckConstraint,Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    status = Column(String, nullable=False)
    description = Column(String)

    owner_id  = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    owner = relationship('User', back_populates='projects')
    artifacts = relationship("DiscoveryArtifact", back_populates="project", passive_deletes=True)

    project_outcome = Column(String, nullable=True)

class User(Base):
    __tablename__='users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    created = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    projects = relationship("Project", back_populates='owner', cascade='all, delete-orphan')
    artifacts = relationship("DiscoveryArtifact", back_populates="user", passive_deletes=True)

class DiscoveryArtifact(Base):
    __tablename__ = "discovery_artifacts"

    # Use the S3 key as the primary key (you already generate a UUID in it)
    s3_key = Column(Text, primary_key=True)

    # Keep types aligned with your other models (UUID) + FKs
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id",    ondelete="SET NULL"), nullable=True, index=True)

    original_filename = Column(Text, nullable=False)
    content_type      = Column(Text, nullable=False)

    s3_bucket = Column(Text, nullable=False)
    public_url = Column(Text, nullable=True)

    status = Column(String, nullable=False, server_default="pending")  # pending|uploaded|verified|failed
    size_bytes = Column(BigInteger, nullable=True)
    etag = Column(Text, nullable=True)

    # Match your naming (you used `created` on Project/User)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending','uploaded','verified','failed')", name="chk_da_status"),
        Index("ix_da_project_created", "project_id", "created_at"),
        Index("ix_da_user_created",    "user_id",    "created_at"),
        Index("ix_da_status",          "status"),
    )

    project = relationship("Project", back_populates="artifacts")
    user    = relationship("User",    back_populates="artifacts")