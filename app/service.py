import logging
import os
import shutil
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from spleeter.separator import Separator

from app.config import settings

logger = logging.getLogger(__name__)

# Cache for Separator instances to avoid recreating models
_SEPARATOR_CACHE: dict[str, Separator | None] = {}


class SpleeterService:
    """Service for handling Spleeter operations."""

    def __init__(self) -> None:
        """Initialize the Spleeter service and ensure directories exist."""
        # Ensure directories exist
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"SpleeterService initialized. Upload dir: {settings.upload_dir}, "
            f"Output dir: {settings.output_dir}"
        )

    def validate_file(self, file: UploadFile) -> str:
        """
        Validates the uploaded file extension and size.

        Args:
            file: The uploaded file to validate

        Returns:
            The file extension (lowercase)

        Raises:
            HTTPException: If file is invalid
        """
        # Edge case: Missing filename
        if not file.filename:
            raise HTTPException(
                status_code=400, detail="Filename is missing. Please provide a valid filename."
            )

        # Edge case: Filename too long (prevent path issues)
        if len(file.filename) > 255:
            raise HTTPException(
                status_code=400, detail="Filename is too long. Maximum length is 255 characters."
            )

        # Edge case: Invalid characters in filename (optimized: use set for O(1) lookup)
        invalid_chars = {"<", ">", ":", '"', "|", "?", "*", "\x00"}
        if any(char in invalid_chars for char in file.filename):
            raise HTTPException(status_code=400, detail="Filename contains invalid characters.")

        # Edge case: No extension
        file_ext = Path(file.filename).suffix.lower()
        if not file_ext:
            raise HTTPException(
                status_code=400,
                detail="File must have an extension. Allowed types: "
                + f"{', '.join(sorted(settings.allowed_extensions))}",
            )

        # Edge case: Invalid extension
        if file_ext not in settings.allowed_extensions:
            logger.warning(f"Invalid file extension attempted: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid file type '{file_ext}'. "
                    f"Allowed types: {', '.join(sorted(settings.allowed_extensions))}"
                ),
            )

        # Edge case: Check file size if available (before upload completes)
        if hasattr(file, "size") and file.size is not None:
            if file.size <= 0:
                raise HTTPException(
                    status_code=400, detail="File size is zero. Please upload a valid audio file."
                )
            if file.size > settings.max_file_size_bytes:
                max_size_mb = settings.max_file_size_mb
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File too large. Maximum size: {max_size_mb}MB. "
                        f"Your file: {file.size / (1024 * 1024):.2f}MB"
                    ),
                )

        return file_ext

    def save_upload(self, file: UploadFile, destination: Path) -> None:
        """
        Saves the uploaded file to disk with validation.

        Args:
            file: The uploaded file
            destination: Path where to save the file

        Raises:
            HTTPException: If save fails or file is invalid
        """
        # Edge case: Check disk space before saving (rough estimate)
        try:
            statvfs = os.statvfs(settings.upload_dir)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            # Reserve at least 200MB free space (lowered for testing)
            min_free_space = 200 * 1024 * 1024
            if free_space < min_free_space:
                raise HTTPException(
                    status_code=507, detail="Insufficient disk space. Please try again later."
                )
        except AttributeError:
            # Windows doesn't have statvfs, skip check
            pass
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")

        # Edge case: File already exists (shouldn't happen with UUID, but handle it)
        if destination.exists():
            logger.warning(f"File already exists, removing: {destination}")
            try:
                destination.unlink()
            except Exception as e:
                logger.error(f"Failed to remove existing file: {e}")

        try:
            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Edge case: Check write permissions
            if not os.access(destination.parent, os.W_OK):
                raise HTTPException(
                    status_code=500, detail="No write permission to upload directory."
                )

            # Save file with size tracking (optimized: larger chunk size for better I/O)
            bytes_written = 0
            chunk_size = 64 * 1024  # 64KB chunks for better performance
            with open(destination, "wb") as buffer:
                while True:
                    chunk = file.file.read(chunk_size)
                    if not chunk:
                        break
                    # Edge case: Check size during upload
                    bytes_written += len(chunk)
                    if bytes_written > settings.max_file_size_bytes:
                        buffer.close()
                        if destination.exists():
                            destination.unlink()
                        max_size_mb = settings.max_file_size_mb
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                f"File too large. Maximum size: {max_size_mb}MB. "
                                f"Uploaded: {bytes_written / (1024 * 1024):.2f}MB"
                            ),
                        )
                    buffer.write(chunk)

            logger.info(f"File saved successfully: {destination} ({bytes_written} bytes)")

        except HTTPException:
            raise
        except PermissionError as e:
            logger.error(f"Permission denied saving file {destination}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Permission denied. Please check server configuration."
            ) from e
        except OSError as e:
            logger.error(f"Failed to save file {destination}: {e}", exc_info=True)
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=500, detail="Failed to save uploaded file. Please try again."
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error saving file {destination}: {e}", exc_info=True)
            # Clean up partial file
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=500, detail="An unexpected error occurred while saving the file."
            ) from e

        # Validate file size after save
        try:
            if not destination.exists():
                raise HTTPException(status_code=500, detail="File was not saved correctly.")

            file_size = destination.stat().st_size

            # Edge case: Empty file
            if file_size == 0:
                self.cleanup_files([destination])
                logger.warning(f"Uploaded file {destination} is empty")
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty. Please upload a valid audio file.",
                )

            # Edge case: File too large (double-check)
            if file_size > settings.max_file_size_bytes:
                self.cleanup_files([destination])
                max_size_mb = settings.max_file_size_mb
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File too large. Maximum size: {max_size_mb}MB. "
                        f"Your file: {file_size / (1024 * 1024):.2f}MB"
                    ),
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating saved file {destination}: {e}", exc_info=True)
            self.cleanup_files([destination])
            raise HTTPException(status_code=500, detail="Error validating uploaded file.") from e

    def _get_separator(self, stems: int) -> Separator:
        """
        Get or create a Separator instance (cached for performance).

        Args:
            stems: Number of stems (2, 4, or 5)

        Returns:
            Separator instance
        """
        model_key = f"spleeter:{stems}stems"

        # Check cache first
        if model_key in _SEPARATOR_CACHE and _SEPARATOR_CACHE[model_key] is not None:
            return _SEPARATOR_CACHE[model_key]

        # Configure TensorFlow to limit memory growth and prevent OOM
        import tensorflow as tf

        # Limit TensorFlow memory growth to prevent OOM errors
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                logger.warning(f"GPU memory growth setting failed: {e}")

        # Limit TensorFlow to use only necessary memory
        # This helps prevent crashes on Railway's limited memory
        try:
            # Set inter/intra op threads to reduce memory usage
            tf.config.threading.set_inter_op_parallelism_threads(1)
            tf.config.threading.set_intra_op_parallelism_threads(1)
        except Exception as e:
            logger.warning(f"Could not set TensorFlow threading: {e}")

        logger.info(f"Creating new Separator instance for {model_key}...")
        separator = Separator(model_key)

        # Cache the separator (but allow it to be cleared if needed)
        _SEPARATOR_CACHE[model_key] = separator

        return separator

    def _clear_separator_cache(self) -> None:
        """Clear the separator cache to free memory."""
        global _SEPARATOR_CACHE
        for separator in _SEPARATOR_CACHE.values():
            if separator is not None:
                try:
                    # Clean up TensorFlow resources
                    del separator
                except Exception as e:
                    logger.warning(f"Error clearing separator: {e}")
        _SEPARATOR_CACHE.clear()
        logger.info("Separator cache cleared")

    def run_separation(self, file_path: Path, stems: int) -> Path:
        """
        Runs Spleeter separation (blocking operation).

        Args:
            file_path: Path to the audio file to separate
            stems: Number of stems (2, 4, or 5)

        Returns:
            Path to the output directory containing separated stems

        Raises:
            HTTPException: If separation fails
        """
        logger.info(f"Starting separation for {file_path} with {stems} stems")

        # Validate stems parameter
        if stems not in [2, 4, 5]:
            raise HTTPException(
                status_code=400, detail=f"Invalid stems value: {stems}. Must be 2, 4, or 5."
            )

        try:
            # Get cached or create new separator
            separator = self._get_separator(stems)

            logger.info(f"Running separation for {file_path}...")
            separator.separate_to_file(str(file_path), str(settings.output_dir))
            logger.info(f"Separation completed for {file_path}")

        except ValueError as e:
            logger.error(f"Invalid Spleeter configuration: {e}", exc_info=True)
            raise HTTPException(
                status_code=400, detail=f"Invalid separation configuration: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Spleeter separation failed for {file_path}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=(
                    "Audio separation failed. "
                    "Please ensure the file is a valid audio file and try again."
                ),
            ) from e

        # Verify output was created
        output_folder_path = settings.output_dir / file_path.stem
        if not output_folder_path.exists():
            logger.error(f"Output folder {output_folder_path} not found after separation")
            raise HTTPException(
                status_code=500, detail="Separation completed but output files were not found."
            )

        logger.info(f"Separation output created at: {output_folder_path}")
        return output_folder_path

    def create_zip(self, source_dir: Path, output_path: Path) -> None:
        """
        Creates a zip archive from a directory (blocking operation).

        Args:
            source_dir: Directory to zip
            output_path: Path for the output zip file

        Raises:
            HTTPException: If zip creation fails
        """
        logger.info(f"Creating zip archive: {source_dir} -> {output_path}")

        # Edge case: Validate source directory exists
        if not source_dir.exists():
            raise HTTPException(
                status_code=500, detail="Source directory does not exist for zip creation."
            )

        if not source_dir.is_dir():
            raise HTTPException(status_code=500, detail="Source path is not a directory.")

        # Edge case: Check if directory is empty
        try:
            if not any(source_dir.iterdir()):
                raise HTTPException(
                    status_code=500, detail="Source directory is empty. No files to zip."
                )
        except PermissionError as e:
            raise HTTPException(
                status_code=500, detail="Permission denied accessing source directory."
            ) from e

        # Edge case: Output file already exists
        if output_path.exists():
            logger.warning(f"Output zip already exists, removing: {output_path}")
            try:
                output_path.unlink()
            except Exception as e:
                logger.error(f"Failed to remove existing zip: {e}")

        # Ensure output directory exists
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise HTTPException(
                status_code=500, detail="Permission denied creating output directory."
            ) from e

        # Edge case: Check write permissions
        if not os.access(output_path.parent, os.W_OK):
            raise HTTPException(status_code=500, detail="No write permission to output directory.")

        try:
            files_added = 0
            total_size = 0

            # Optimized: Use Path objects and collect files first to reduce I/O
            files_to_zip: list[tuple] = []
            max_zip_size = 500 * 1024 * 1024  # 500MB

            # Collect all files first (single walk)
            for root, _, files in os.walk(source_dir):
                for file_name in files:
                    file_path = Path(root) / file_name

                    # Edge case: Skip if file doesn't exist (race condition)
                    if not file_path.exists():
                        logger.warning(f"Skipping non-existent file: {file_path}")
                        continue

                    # Edge case: Skip if not a file (symlink, etc.)
                    if not file_path.is_file():
                        logger.warning(f"Skipping non-file: {file_path}")
                        continue

                    # Edge case: Check file size before adding
                    try:
                        file_size = file_path.stat().st_size
                        total_size += file_size

                        # Prevent extremely large zips (safety limit)
                        if total_size > max_zip_size:
                            raise HTTPException(
                                status_code=500, detail="Output zip file would be too large."
                            )

                        # Calculate relative path for archive
                        try:
                            arcname = file_path.relative_to(source_dir)
                            # Edge case: Sanitize arcname to prevent zip slip
                            if ".." in str(arcname):
                                arcname = Path(file_name)
                        except ValueError:
                            # Fallback if relative path fails
                            arcname = Path(file_name)

                        files_to_zip.append((file_path, str(arcname)))
                    except OSError as e:
                        logger.warning(f"Could not get size for {file_path}: {e}")
                        continue

            # Now create zip with collected files (optimized: single write operation)
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path, arcname in files_to_zip:
                    try:
                        zipf.write(str(file_path), arcname)
                        files_added += 1
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Failed to add {file_path} to zip: {e}")
                        # Continue with other files
                        continue

            # Edge case: Check if any files were added
            if files_added == 0:
                if output_path.exists():
                    output_path.unlink()
                raise HTTPException(
                    status_code=500, detail="No files were added to the zip archive."
                )

            logger.info(
                f"Zip archive created successfully: {output_path} "
                f"({files_added} files, {total_size / (1024 * 1024):.2f}MB)"
            )

        except HTTPException:
            raise
        except zipfile.BadZipFile as e:
            logger.error(f"Invalid zip file created {output_path}: {e}", exc_info=True)
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=500, detail="Failed to create valid zip archive."
            ) from e
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to create zip archive {output_path}: {e}", exc_info=True)
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=500, detail="Failed to create zip archive. Please try again."
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error creating zip {output_path}: {e}", exc_info=True)
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while creating the zip archive.",
            ) from e

    def cleanup_files(self, file_paths: list[Path]) -> None:
        """
        Removes temporary files and directories.

        Args:
            file_paths: List of file or directory paths to remove
        """
        for path in file_paths:
            try:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                        logger.debug(f"Cleaned up directory: {path}")
                    else:
                        path.unlink()
                        logger.debug(f"Cleaned up file: {path}")
            except (OSError, PermissionError) as e:
                logger.warning(f"Failed to cleanup {path}: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error cleaning up {path}: {e}", exc_info=True)
