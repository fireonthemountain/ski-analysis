"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    skill_level: Optional[str] = "intermediate"


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Video Schemas
class VideoBase(BaseModel):
    filename: str
    original_filename: str


class VideoCreate(VideoBase):
    storage_url: str
    file_size: int


class VideoResponse(VideoBase):
    id: UUID
    user_id: UUID
    file_size: Optional[int]
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    storage_url: str
    thumbnail_url: Optional[str]
    processing_status: str
    processing_error: Optional[str]
    upload_date: datetime
    processed_date: Optional[datetime]

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int
    page: int
    page_size: int


# Analysis Schemas
class AnalysisBase(BaseModel):
    video_id: UUID


class AnalysisResponse(AnalysisBase):
    id: UUID
    created_at: datetime
    pose_data: Optional[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    recommendations: Optional[List[Dict[str, Any]]]
    overall_score: Optional[float]
    stance_score: Optional[float]
    balance_score: Optional[float]
    edge_control_score: Optional[float]
    turn_dynamics_score: Optional[float]
    upper_body_score: Optional[float]
    lower_body_score: Optional[float]

    class Config:
        from_attributes = True


# Progress Schemas
class ProgressResponse(BaseModel):
    id: UUID
    user_id: UUID
    analysis_id: UUID
    date: datetime
    metric_name: str
    value: float

    class Config:
        from_attributes = True


# Upload Response
class UploadResponse(BaseModel):
    video_id: UUID
    filename: str
    status: str
    message: str
    upload_url: Optional[str]


# Error Response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str]
    status_code: int
