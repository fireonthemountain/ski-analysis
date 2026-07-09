"""
Main FastAPI application entry point for Ski Analysis API.
"""
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv

# Import database and models
from database import get_db, create_tables, Video, User, Analysis
from database.models import ProcessingStatus
from api.schemas import (
    VideoResponse,
    VideoListResponse,
    AnalysisResponse,
    UploadResponse,
    ErrorResponse
)
from processing import storage_service
from analysis import pose_detector, technique_analyzer

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Ski Analysis API",
    description="API for analyzing ski technique from video footage",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    print("🚀 Starting Ski Analysis API...")
    print("📦 Creating database tables...")
    create_tables()
    print("✅ Database initialized")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "ski-analysis-api",
            "version": "0.1.0"
        }
    )


# API v1 routes
@app.get("/api/v1")
async def api_root():
    """API root endpoint."""
    return JSONResponse(
        content={
            "message": "Ski Analysis API v1",
            "endpoints": {
                "health": "/health",
                "docs": "/api/docs",
                "videos": "/api/v1/videos",
                "upload": "/api/v1/videos/upload",
                "analysis": "/api/v1/analysis/{video_id}",
                "skeleton": "/api/v1/analysis/{video_id}/skeleton",
            }
        }
    )


# Video endpoints
@app.get("/api/v1/videos", response_model=VideoListResponse)
async def list_videos(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all videos with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by processing status
        db: Database session

    Returns:
        List of videos with pagination info
    """
    query = db.query(Video)

    if status_filter:
        query = query.filter(Video.processing_status == status_filter)

    total = query.count()
    videos = query.offset(skip).limit(limit).all()

    return VideoListResponse(
        videos=videos,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )


@app.get("/api/v1/videos/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, db: Session = Depends(get_db)):
    """
    Get video by ID.

    Args:
        video_id: UUID of the video
        db: Database session

    Returns:
        Video details
    """
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format"
        )

    video = db.query(Video).filter(Video.id == video_uuid).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return video


@app.post("/api/v1/videos/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload photo or video for analysis.
    V1: Focused on photo analysis (JPG, PNG)
    Future: Video support (MP4, AVI, MOV, MKV)

    Args:
        file: Image/video file to upload
        db: Database session

    Returns:
        Upload confirmation with video ID
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    # Check file extension - Support photos (V1) and videos (future)
    allowed_image_formats = os.getenv("ALLOWED_IMAGE_FORMATS", "jpg,jpeg,png").split(",")
    allowed_video_formats = os.getenv("ALLOWED_VIDEO_FORMATS", "mp4,avi,mov,mkv").split(",")
    allowed_extensions = allowed_image_formats + allowed_video_formats

    file_extension = file.filename.rsplit(".", 1)[-1].lower()
    is_image = file_extension in allowed_image_formats
    is_video = file_extension in allowed_video_formats

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: Images ({', '.join(allowed_image_formats)}), Videos ({', '.join(allowed_video_formats)})"
        )

    # Check file size (smaller limit for images)
    if is_image:
        max_size_mb = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
    else:
        max_size_mb = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))

    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    if file_size > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_size_mb}MB"
        )

    try:
        # Upload to storage
        object_name, storage_url = storage_service.upload_video(
            file.file,
            file.filename,
            content_type=file.content_type or "video/mp4"
        )

        # Create database entry (temporary user for now)
        # TODO: Add authentication and use actual user_id
        temp_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        # Check if temp user exists, create if not
        temp_user = db.query(User).filter(User.id == temp_user_id).first()
        if not temp_user:
            temp_user = User(
                id=temp_user_id,
                email="temp@example.com",
                username="temp_user",
                hashed_password="temp"  # Not a real password
            )
            db.add(temp_user)
            db.commit()

        video = Video(
            user_id=temp_user_id,
            filename=object_name,
            original_filename=file.filename,
            file_size=file_size,
            storage_url=storage_url,
            processing_status=ProcessingStatus.PENDING if is_video else ProcessingStatus.PROCESSING
        )

        db.add(video)
        db.commit()
        db.refresh(video)

        # For images, process immediately
        if is_image:
            try:
                # Re-read file for processing
                file.file.seek(0)
                file_bytes = file.file.read()

                # Detect pose
                pose_data = pose_detector.detect_from_file(file_bytes)

                if pose_data:
                    # Analyze technique
                    analysis_result = technique_analyzer.analyze(pose_data)

                    # Create analysis record
                    analysis = Analysis(
                        video_id=video.id,
                        pose_data=pose_data,
                        metrics=analysis_result["metrics"],
                        recommendations=analysis_result["recommendations"],
                        overall_score=analysis_result["scores"]["overall_score"],
                        stance_score=analysis_result["scores"].get("stance_score"),
                        balance_score=analysis_result["scores"].get("balance_score"),
                        edge_control_score=None,  # Not calculated for static images
                        turn_dynamics_score=None,  # Not calculated for static images
                        upper_body_score=analysis_result["scores"].get("upper_body_score"),
                        lower_body_score=analysis_result["scores"].get("lower_body_score")
                    )

                    db.add(analysis)
                    video.processing_status = ProcessingStatus.COMPLETED
                    video.processed_date = datetime.utcnow()
                else:
                    video.processing_status = ProcessingStatus.FAILED
                    video.processing_error = "No pose detected in image. Make sure the full body is visible."

                db.commit()

            except Exception as e:
                print(f"Error processing image: {e}")
                video.processing_status = ProcessingStatus.FAILED
                video.processing_error = f"Processing error: {str(e)}"
                db.commit()

        message = "Image processed successfully! View results below." if is_image else "Video uploaded successfully. Processing will begin shortly."

        return UploadResponse(
            video_id=video.id,
            filename=video.original_filename,
            status="success",
            message=message,
            upload_url=storage_url
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload video: {str(e)}"
        )


@app.delete("/api/v1/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """
    Delete video and its analysis.

    Args:
        video_id: UUID of the video
        db: Database session
    """
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format"
        )

    video = db.query(Video).filter(Video.id == video_uuid).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Delete from storage
    storage_service.delete_video(video.filename)

    # Delete from database (cascade will remove analyses)
    db.delete(video)
    db.commit()

    return None


# Analysis endpoints
@app.get("/api/v1/analysis/{video_id}", response_model=AnalysisResponse)
async def get_analysis(video_id: str, db: Session = Depends(get_db)):
    """
    Get analysis results for a video.

    Args:
        video_id: UUID of the video
        db: Database session

    Returns:
        Analysis results
    """
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format"
        )

    # Get the most recent analysis for this video
    analysis = db.query(Analysis).filter(
        Analysis.video_id == video_uuid
    ).order_by(Analysis.created_at.desc()).first()

    if not analysis:
        # Check if video exists
        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )

        # Video exists but no analysis yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not available yet. Video may still be processing."
        )

    return analysis


@app.get("/api/v1/analysis/{video_id}/skeleton")
async def get_skeleton_overlay(video_id: str, db: Session = Depends(get_db)):
    """
    Get photo with skeleton overlay drawn on it.

    Args:
        video_id: UUID of the video
        db: Database session

    Returns:
        Image with skeleton landmarks drawn (JPEG)
    """
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format"
        )

    # Get video
    video = db.query(Video).filter(Video.id == video_uuid).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Get analysis
    analysis = db.query(Analysis).filter(
        Analysis.video_id == video_uuid
    ).order_by(Analysis.created_at.desc()).first()

    if not analysis or not analysis.pose_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pose data available for this video"
        )

    try:
        # Fetch original image from storage
        response = requests.get(video.storage_url)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch original image"
            )

        image_bytes = response.content

        # Draw landmarks on image
        overlaid_image_bytes = pose_detector.draw_landmarks(
            image_bytes,
            analysis.pose_data
        )

        if not overlaid_image_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate skeleton overlay"
            )

        # Return image
        return Response(
            content=overlaid_image_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename=skeleton_{video.original_filename}"
            }
        )

    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch image: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating skeleton overlay: {str(e)}"
        )


@app.post("/api/v1/analysis/{video_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_video(video_id: str, db: Session = Depends(get_db)):
    """
    Trigger reprocessing of a video.

    Args:
        video_id: UUID of the video
        db: Database session
    """
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video ID format"
        )

    video = db.query(Video).filter(Video.id == video_uuid).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Update status to pending
    video.processing_status = ProcessingStatus.PENDING
    video.processing_error = None
    db.commit()

    return JSONResponse(
        content={
            "message": "Video queued for reprocessing",
            "video_id": str(video_id)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
