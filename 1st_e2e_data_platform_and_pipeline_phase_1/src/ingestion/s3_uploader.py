import json
from typing import Dict, List
from botocore.exceptions import ClientError
from src.common.config import get_settings
from src.common.database import get_minio_client
from src.common.logger import get_logger

logger = get_logger("ingestion_s3_uploader")


class MinIOUploader:
    """
    Manages raw storage landings on MinIO S3 object lake.
    Partitions raw files deterministically by logical date:
    s3://fastroute-raw/{data_type}/{logical_date}/{data_type}_{logical_date}.json
    """

    def __init__(self):
        self.settings = get_settings()
        self._s3_client = None
        self.raw_bucket = self.settings.minio_raw_bucket
        self._bucket_checked = False

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = get_minio_client()
        return self._s3_client

    def _ensure_bucket_exists(self):
        """Ensures the raw bucket exists in MinIO."""
        if self._bucket_checked:
            return
        try:
            self.s3_client.head_bucket(Bucket=self.raw_bucket)
            self._bucket_checked = True
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.raw_bucket)
                self._bucket_checked = True
                logger.info(f"Created MinIO bucket '{self.raw_bucket}'")
            except Exception as e:
                logger.warning(f"Could not verify/create bucket '{self.raw_bucket}': {e}")

    def upload_batch(self, data_type: str, records: List[Dict], logical_date: str) -> str:
        """
        Uploads records to MinIO S3 partition keyed by logical date.
        Re-running for the same logical date cleanly overwrites the partition file.
        """
        self._ensure_bucket_exists()
        object_key = f"{data_type}/{logical_date}/{data_type}_{logical_date}.json"
        body = json.dumps(records, indent=2)

        try:
            self.s3_client.put_object(
                Bucket=self.raw_bucket,
                Key=object_key,
                Body=body.encode("utf-8"),
                ContentType='application/json'
            )
            s3_uri = f"s3://{self.raw_bucket}/{object_key}"
            logger.info(
                f"Successfully landed raw artifact to {s3_uri} ({len(records)} records, {len(body)} bytes)"
            )
            return s3_uri
        except Exception as e:
            logger.error(f"Failed to upload raw batch to MinIO S3: {e}")
            raise

    def read_batch(self, data_type: str, logical_date: str) -> List[Dict]:
        """
        Reads raw JSON records back from MinIO S3 partition for the designated logical date.
        """
        object_key = f"{data_type}/{logical_date}/{data_type}_{logical_date}.json"
        try:
            response = self.s3_client.get_object(
                Bucket=self.raw_bucket,
                Key=object_key
            )
            content = response['Body'].read().decode('utf-8')
            records = json.loads(content)
            logger.info(
                f"Read {len(records)} raw records from s3://{self.raw_bucket}/{object_key}"
            )
            return records
        except Exception as e:
            logger.error(f"Failed reading raw batch s3://{self.raw_bucket}/{object_key}: {e}")
            raise
