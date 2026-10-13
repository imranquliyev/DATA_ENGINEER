"""Staging module: operational data loading from MinIO to PostgreSQL staging."""
from src.staging.loader import StagingLoader

__all__ = ["StagingLoader"]
