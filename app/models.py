from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
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
    created_by = Column(String, nullable=False)
    status = Column(String, nullable=False)
    description = Column(String)