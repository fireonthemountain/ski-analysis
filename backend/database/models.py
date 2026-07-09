"""
Database models for ski analysis application.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .connection import Base


class SkillLevel(str, enum.Enum):
    """Enum for user skill levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ProcessingStatus(str, enum.Enum):
    """Enum for video processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User model for authentication and profiles."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    skill_level = Column(Enum(SkillLevel), default=SkillLevel.INTERMEDIATE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")


class Video(Base):
    """Video model for uploaded skiing videos."""
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    duration = Column(Float)  # Duration in seconds
    width = Column(Integer)  # Video width
    height = Column(Integer)  # Video height
    fps = Column(Float)  # Frames per second
    storage_url = Column(Text, nullable=False)  # S3/MinIO URL
    thumbnail_url = Column(Text)
    processing_status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        index=True
    )
    processing_error = Column(Text)  # Error message if failed
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="videos")
    analyses = relationship("Analysis", back_populates="video", cascade="all, delete-orphan")


class Analysis(Base):
    """Analysis model for technique analysis results."""
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Pose data - array of frames with landmarks
    pose_data = Column(JSONB)  # Flexible JSON structure for pose landmarks

    # Calculated metrics
    metrics = Column(JSONB)  # Dictionary of calculated metrics

    # AI recommendations
    recommendations = Column(JSONB)  # Array of recommendation objects

    # Overall score (0-100)
    overall_score = Column(Float)

    # Technique scores (each 0-100)
    stance_score = Column(Float)
    balance_score = Column(Float)
    edge_control_score = Column(Float)
    turn_dynamics_score = Column(Float)
    upper_body_score = Column(Float)
    lower_body_score = Column(Float)

    # Relationships
    video = relationship("Video", back_populates="analyses")
    progress_entries = relationship(
        "Progress",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )


class Progress(Base):
    """Progress tracking model for user improvement over time."""
    __tablename__ = "progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    metric_name = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)

    # Relationships
    analysis = relationship("Analysis", back_populates="progress_entries")
