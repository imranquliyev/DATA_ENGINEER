import json
from datetime import datetime
from typing import Dict, List
from src.common.config import get_settings
from src.common.database import get_minio_client
from src.common.logger import get_logger

logger = get_logger("s3_uploader")


class MinIOUploader:
    """Uploads raw operational dataset batches to MinIO S3 landing buckets."""

    def __init__(self):
        self.settings = get_settings()
        self.s3_client = get_minio_client()
        self.raw_bucket = self.settings.minio_raw_bucket

    def upload_batch(self, data_type: str, records: List[Dict]) -> str:
        """Uploads a list of records as JSON batch to MinIO S3 partition."""
        now = datetime.utcnow()
        partition_path = now.strftime("%Y/%m/%d/%H")
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        object_key = f"{data_type}/{partition_path}/{data_type}_{timestamp_str}.json"

        body = json.dumps(records, indent=2)

        try:
            self.s3_client.put_object(
                Bucket=self.raw_bucket,
                Key=object_key,
                Body=body,
                ContentType='application/json'
            )
            s3_uri = f"s3://{self.raw_bucket}/{object_key}"
            logger.info(f"Successfully uploaded batch to {s3_uri} ({len(records)} records)")
            return s3_uri
        except Exception as e:
            logger.error(f"Failed to upload batch to MinIO S3: {e}")
            raise
