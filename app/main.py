import asyncio
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Union

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.jobs import JobStatus, job_manager
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


async def process_separation_job(job_id: str, file_path: Path, stems: int) -> None:
    """
    Process a separation job in the background.

    Args:
        job_id: Job identifier
        file_path: Path to the audio file
        stems: Number of stems to separate into
    """
    logger.info(f"[{job_id}] Starting background separation processing")
    job_manager.update_job_status(job_id, JobStatus.PROCESSING, progress=0.1)

    cleanup_paths = [file_path]
    zip_path = settings.output_dir / f"{job_id}.zip"

    try:
        # Run Spleeter separation
        job_manager.update_job_status(job_id, JobStatus.PROCESSING, progress=0.3)
        output_folder_path = await run_in_threadpool(
            spleeter_service.run_separation, file_path, stems
        )
        cleanup_paths.append(output_folder_path)

        # Create zip file
        job_manager.update_job_status(job_id, JobStatus.PROCESSING, progress=0.7)
        await run_in_threadpool(spleeter_service.create_zip, output_folder_path, zip_path)
        cleanup_paths.append(zip_path)

        # Verify zip file
        if not zip_path.exists() or zip_path.stat().st_size == 0:
            raise Exception("Zip file was not created or is empty")

        # Mark job as completed
        job_manager.update_job_status(
            job_id, JobStatus.COMPLETED, progress=1.0, result_path=zip_path
        )
        logger.info(f"[{job_id}] Separation completed successfully: {zip_path}")

        # Schedule cleanup after 1 hour (give time for download)
        await asyncio.sleep(3600)
        spleeter_service.cleanup_files(cleanup_paths)
        logger.info(f"[{job_id}] Cleaned up temporary files")

    except Exception as e:
        logger.error(f"[{job_id}] Separation failed: {e}", exc_info=True)
        job_manager.update_job_status(
            job_id, JobStatus.FAILED, progress=1.0, error=str(e)
        )
        # Cleanup on failure
        spleeter_service.cleanup_files(cleanup_paths)


@app.on_event("startup")
async def startup_event():
    """Pre-warm TensorFlow models on startup and start background tasks."""
    logger.info("Starting application startup tasks...")

    # Start background cleanup task first (non-blocking)
    async def periodic_cleanup():
        """Periodically clean up old jobs."""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            job_manager.cleanup_old_jobs()

    asyncio.create_task(periodic_cleanup())

    # Pre-warm TensorFlow models in background (non-blocking)
    async def pre_warm_models():
        """Pre-warm TensorFlow models in background."""
        try:
            logger.info("Pre-warming TensorFlow models...")
            for stems in [2, 4]:
                logger.info(f"Pre-warming {stems}-stem model...")
                # Pre-initialize separator to load model into memory (run in thread pool)
                await run_in_threadpool(spleeter_service._get_separator, stems)
                logger.info(f"{stems}-stem model ready")
            logger.info("All models pre-warmed successfully")
        except Exception as e:
            logger.warning(f"Model pre-warming failed (non-critical): {e}")

    # Start model pre-warming in background (don't wait for it)
    asyncio.create_task(pre_warm_models())
    logger.info("Application startup complete (models pre-warming in background)")


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
def read_root() -> dict[str, str]:
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
def health_check() -> dict[str, Any]:
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
            statvfs = os.statvfs(settings.upload_dir)
            free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
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
            "allowed_extensions": sorted(settings.allowed_extensions),
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


@app.post("/separate", tags=["Separation"], response_model=None)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def separate_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to separate (MP3, WAV, OGG, FLAC, M4A)"),
    stems: int = 2,
    async_mode: bool = True,
) -> Union[JSONResponse, FileResponse]:
    """
    Separate audio file into stems.

    This endpoint accepts an audio file and separates it into individual stems
    (vocals, drums, bass, etc.) using Spleeter.

    Args:
        request: FastAPI request object (for rate limiting)
        background_tasks: Background tasks for cleanup
        file: Audio file to separate
        stems: Number of stems (2, 4, or 5). Default: 2
        async_mode: If True, returns job ID immediately and processes in background.
                   If False, waits for completion (may timeout on Railway). Default: True

    Returns:
        If async_mode=True: JSON with job_id and status endpoint
        If async_mode=False: ZIP file containing separated audio stems

    Raises:
        HTTPException: If validation fails or processing error occurs
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        f"[{request_id}] Separation request received: filename={file.filename}, "
        f"stems={stems}, async_mode={async_mode}"
    )

    # Edge case: Validate stems parameter type and value
    try:
        stems_int = int(stems)
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stems value: {stems}. Must be an integer (2, 4, or 5).",
        ) from e

    if stems_int not in [2, 4, 5]:
        raise HTTPException(
            status_code=400, detail=f"Invalid stems value: {stems_int}. Must be 2, 4, or 5."
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

    # Async mode: Create job and return immediately
    if async_mode:
        job = job_manager.create_job(file_path, stems)
        # Start background processing
        asyncio.create_task(process_separation_job(job.job_id, file_path, stems))

        return JSONResponse(
            status_code=202,  # Accepted
            content={
                "job_id": job.job_id,
                "status": "pending",
                "message": "Separation job created. Use the job_id to check status.",
                "status_url": f"/jobs/{job.job_id}/status",
                "result_url": f"/jobs/{job.job_id}/result",
            },
            headers={"X-Request-ID": request_id},
        )

    # Synchronous mode: Process immediately (may timeout on Railway)
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
        await run_in_threadpool(spleeter_service.create_zip, output_folder_path, zip_path)

        logger.info(f"[{request_id}] Separation completed: {zip_path}")

    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        spleeter_service.cleanup_files(cleanup_paths)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"[{request_id}] Unexpected error during separation: {e}", exc_info=True)
        spleeter_service.cleanup_files(cleanup_paths)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during audio separation. Please try again.",
        ) from e

    # Edge case: Verify zip file exists and is readable before returning
    if not zip_path.exists():
        logger.error(f"[{request_id}] Zip file not found after creation: {zip_path}")
        spleeter_service.cleanup_files(cleanup_paths)
        raise HTTPException(status_code=500, detail="Output file was not created correctly.")

    # Edge case: Check zip file size
    try:
        zip_size = zip_path.stat().st_size
        if zip_size == 0:
            logger.error(f"[{request_id}] Zip file is empty: {zip_path}")
            spleeter_service.cleanup_files(cleanup_paths)
            raise HTTPException(status_code=500, detail="Output zip file is empty.")
        logger.info(f"[{request_id}] Zip file size: {zip_size / (1024 * 1024):.2f}MB")
    except OSError as e:
        logger.error(f"[{request_id}] Could not stat zip file: {e}")
        spleeter_service.cleanup_files(cleanup_paths)
        raise HTTPException(status_code=500, detail="Could not access output file.") from e

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


@app.get("/jobs/{job_id}/status", tags=["Separation"])
def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Get the status of a separation job.

    Args:
        job_id: Job identifier returned from /separate endpoint

    Returns:
        Job status information including progress and result URL

    Raises:
        HTTPException: If job not found
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "status": "ok",
        "job": job.to_dict(),
    }


@app.get("/jobs/{job_id}/result", tags=["Separation"])
def get_job_result(job_id: str) -> FileResponse | JSONResponse:
    """
    Download the result of a completed separation job.

    Args:
        job_id: Job identifier

    Returns:
        ZIP file if job is completed, error message otherwise

    Raises:
        HTTPException: If job not found or not completed
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != JobStatus.COMPLETED:
        return JSONResponse(
            status_code=202,
            content={
                "status": "not_ready",
                "job_id": job_id,
                "current_status": job.status.value,
                "message": "Job is still processing. Please check status endpoint.",
                "status_url": f"/jobs/{job_id}/status",
            },
        )

    if not job.result_path or not job.result_path.exists():
        raise HTTPException(
            status_code=500, detail="Result file not found. Job may have been cleaned up."
        )

    try:
        zip_size = job.result_path.stat().st_size
        safe_filename = f"separated_{job.stems}stems_{job_id[:8]}.zip"
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")

        return FileResponse(
            job.result_path,
            media_type="application/zip",
            filename=safe_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
                "Content-Length": str(zip_size),
            },
        )
    except OSError as e:
        logger.error(f"Error accessing result file for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not access result file.") from e


@app.get("/metrics", tags=["Monitoring"])
def get_performance_metrics() -> dict[str, Any]:
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
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": request_id,
        },
    )
