"""Service AWS S3 — stockage des fichiers audio."""

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import uuid

from core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def upload_audio(file_path: str, meeting_id: str, filename: str) -> str:
    """Upload un fichier audio vers S3. Retourne la clé S3."""
    s3 = get_s3_client()
    ext = Path(filename).suffix
    key = f"meetings/{meeting_id}/audio{ext}"

    s3.upload_file(
        file_path,
        settings.aws_s3_bucket,
        key,
        ExtraArgs={"ContentType": "audio/mpeg"},
    )
    return key


def download_audio(s3_key: str, local_path: str) -> str:
    """Télécharge un audio depuis S3 vers un chemin local."""
    s3 = get_s3_client()
    s3.download_file(settings.aws_s3_bucket, s3_key, local_path)
    return local_path


def get_presigned_url(s3_key: str, expiry: int = 3600) -> str:
    """Génère une URL signée pour accès temporaire."""
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": s3_key},
        ExpiresIn=expiry,
    )
