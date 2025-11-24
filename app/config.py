import os
from pathlib import Path
from typing import Set

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings."""

    app_title: str = "Stem Splitter API"
    app_version: str = "1.0.0"
    app_description: str = "FastAPI service for audio stem separation using Spleeter"
    
    # Directory settings
    upload_dir: Path = Path("temp/uploads")
    output_dir: Path = Path("temp/output")
    
    # File validation settings
    allowed_extensions: Set[str] = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}
    max_file_size_mb: int = 100
    max_file_size_bytes: int = 100 * 1024 * 1024  # 100MB default
    
    # Rate limiting settings
    rate_limit_per_minute: int = 30
    
    # Processing settings
    max_concurrent_separations: int = 3
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Resolve paths to absolute
        self.upload_dir = self.upload_dir.resolve()
        self.output_dir = self.output_dir.resolve()
        # Normalize allowed_extensions to ensure they have dots
        # Pydantic may parse env vars and strip dots, so we normalize here
        normalized_extensions = set()
        for ext in self.allowed_extensions:
            # Ensure extension starts with dot
            if not ext.startswith('.'):
                normalized_extensions.add(f'.{ext}')
            else:
                normalized_extensions.add(ext)
        self.allowed_extensions = normalized_extensions
        # Calculate max file size from MB setting
        if self.max_file_size_mb:
            self.max_file_size_bytes = self.max_file_size_mb * 1024 * 1024


settings = Settings()
