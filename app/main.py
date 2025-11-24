import logging
import os
import uuid
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.service import SpleeterService

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public API - allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
spleeter_service = SpleeterService()


@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    """Add request ID and track request timing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()
    
    response = await call_next(request)
    
    # Add performance headers
    elapsed_time = time.perf_counter() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed_time:.3f}"
    
    # Log slow requests
    if elapsed_time > 1.0:
        logger.warning(
            f"[{request_id}] Slow request: {request.method} {request.url.path} "
            f"took {elapsed_time:.3f}s"
        )
    
    return response


@app.get("/", tags=["Health"])
def read_root() -> Dict[str, str]:
    """
    Root endpoint - API information.
    
    Returns:
        API status and usage information
    """
    return {
        "message": f"{settings.app_title} is running",
        "version": settings.app_version,
        "docs": "/docs",
        "endpoint": "POST /separate",
        "description": "Upload an audio file to separate into stems",
    }


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.
    
    Returns:
        Service health status
    """
    try:
        # Edge case: Check if directories are accessible
        upload_accessible = os.access(settings.upload_dir, os.W_OK)
        output_accessible = os.access(settings.output_dir, os.W_OK)
        
        # Edge case: Check disk space
        try:
            import shutil as shutil_module
            statvfs = os.statvfs(settings.upload_dir)
            free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 ** 3)
            disk_ok = free_space_gb > 0.2  # At least 200MB free
        except (AttributeError, OSError):
            # Windows or permission issue - assume OK
            free_space_gb = None
            disk_ok = True
        
        status = "healthy"
        if not upload_accessible or not output_accessible:
            status = "degraded"
        if not disk_ok:
            status = "degraded"
        
        health_data = {
            "status": status,
            "service": settings.app_title,
            "version": settings.app_version,
            "max_file_size_mb": settings.max_file_size_mb,
            "allowed_extensions": sorted(list(settings.allowed_extensions)),
            "directories": {
                "upload_accessible": upload_accessible,
                "output_accessible": output_accessible,
            },
        }
        
        if free_space_gb is not None:
            health_data["disk_space_gb"] = round(free_space_gb, 2)
            health_data["disk_ok"] = disk_ok
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": settings.app_title,
            "version": settings.app_version,
            "error": "Health check failed",
        }


@app.post("/separate", tags=["Separation"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def separate_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to separate (MP3, WAV, OGG, FLAC, M4A)"),
    stems: int = 2,
) -> FileResponse:
    """
    Separate audio file into stems.
    
    This endpoint accepts an audio file and separates it into individual stems
    (vocals, drums, bass, etc.) using Spleeter. The result is returned as a ZIP file.
    
    Args:
        request: FastAPI request object (for rate limiting)
        background_tasks: Background tasks for cleanup
        file: Audio file to separate
        stems: Number of stems (2, 4, or 5). Default: 2
        
    Returns:
        ZIP file containing separated audio stems
        
    Raises:
        HTTPException: If validation fails or processing error occurs
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Separation request received: "
        f"filename={file.filename}, stems={stems}"
    )
    
    # Edge case: Validate stems parameter type and value
    try:
        stems_int = int(stems)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stems value: {stems}. Must be an integer (2, 4, or 5)."
        )
    
    if stems_int not in [2, 4, 5]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stems value: {stems_int}. Must be 2, 4, or 5."
        )
    
    stems = stems_int  # Use validated integer

    # Validate file
    file_ext = spleeter_service.validate_file(file)
    
    # Generate unique ID for this request
    unique_id = str(uuid.uuid4())
    file_path = settings.upload_dir / f"{unique_id}{file_ext}"
    
    logger.info(f"[{request_id}] Processing file: {file_path}")

    # Save uploaded file
    spleeter_service.save_upload(file, file_path)
    cleanup_paths = [file_path]

    try:
        # Run Spleeter separation in thread pool (CPU bound / Blocking I/O)
        output_folder_path = await run_in_threadpool(
            spleeter_service.run_separation, file_path, stems
        )
        cleanup_paths.append(output_folder_path)

        # Create zip file
        zip_path = settings.output_dir / f"{unique_id}.zip"
        cleanup_paths.append(zip_path)

        # Create zip in thread pool (I/O bound)
        await run_in_threadpool(
            spleeter_service.create_zip, output_folder_path, zip_path
        )
        
        logger.info(f"[{request_id}] Separation completed: {zip_path}")

    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        spleeter_service.cleanup_files(cleanup_paths)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(
            f"[{request_id}] Unexpected error during separation: {e}",
            exc_info=True
        )
        spleeter_service.cleanup_files(cleanup_paths)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during audio separation. Please try again."
        ) from e

    # Edge case: Verify zip file exists and is readable before returning
    if not zip_path.exists():
        logger.error(f"[{request_id}] Zip file not found after creation: {zip_path}")
        spleeter_service.cleanup_files(cleanup_paths)
        raise HTTPException(
            status_code=500,
            detail="Output file was not created correctly."
        )
    
    # Edge case: Check zip file size
    try:
        zip_size = zip_path.stat().st_size
        if zip_size == 0:
            logger.error(f"[{request_id}] Zip file is empty: {zip_path}")
            spleeter_service.cleanup_files(cleanup_paths)
            raise HTTPException(
                status_code=500,
                detail="Output zip file is empty."
            )
        logger.info(f"[{request_id}] Zip file size: {zip_size / (1024 * 1024):.2f}MB")
    except OSError as e:
        logger.error(f"[{request_id}] Could not stat zip file: {e}")
        spleeter_service.cleanup_files(cleanup_paths)
        raise HTTPException(
            status_code=500,
            detail="Could not access output file."
        )

    # Schedule cleanup after response is sent
    background_tasks.add_task(spleeter_service.cleanup_files, cleanup_paths)

    # Edge case: Sanitize filename for safe download
    safe_filename = f"separated_{stems}stems_{unique_id[:8]}.zip"
    # Remove any potentially dangerous characters
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=safe_filename,
        headers={
            "X-Request-ID": request_id,
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Length": str(zip_size),
        },
    )


@app.get("/metrics", tags=["Monitoring"])
def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics endpoint (for monitoring).
    
    Returns:
        Performance statistics
    """
    try:
        from app.performance import get_performance_stats
        stats = get_performance_stats()
        return {
            "status": "ok",
            "metrics": stats,
            "timestamp": time.time(),
        }
    except ImportError:
        # Performance module not available (optional feature)
        return {
            "status": "ok",
            "metrics": {},
            "message": "Performance tracking not enabled",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unexpected errors."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"[{request_id}] Unhandled exception: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        },
    )
