import uuid

import boto3
from botocore.config import Config as BotoConfig
from flask import current_app

ALLOWED_PROOF_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
ALLOWED_PRODUCT_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class StorageError(Exception):
    pass


def _client():
    settings = current_app.config
    required = ("OBJECT_STORAGE_ENDPOINT", "OBJECT_STORAGE_BUCKET", "OBJECT_STORAGE_ACCESS_KEY_ID", "OBJECT_STORAGE_SECRET_ACCESS_KEY")
    if not all(settings.get(key) for key in required):
        raise StorageError("Payment proof storage is not configured.")
    return boto3.client("s3", endpoint_url=str(settings["OBJECT_STORAGE_ENDPOINT"]).strip(), aws_access_key_id=str(settings["OBJECT_STORAGE_ACCESS_KEY_ID"]).strip(), aws_secret_access_key=str(settings["OBJECT_STORAGE_SECRET_ACCESS_KEY"]).strip(), region_name=str(settings.get("OBJECT_STORAGE_REGION", "auto")).strip() or "auto", config=BotoConfig(signature_version="s3v4"))


def create_upload(user_id: int, filename: str, content_type: str, size_bytes: int) -> dict:
    if content_type not in ALLOWED_PROOF_TYPES or size_bytes < 1 or size_bytes > current_app.config["PAYMENT_PROOF_MAX_BYTES"]:
        raise StorageError("Only PDF, JPG, PNG or WEBP files within the permitted size are accepted.")
    key = f"payment-proofs/{user_id}/{uuid.uuid4()}-{filename.rsplit('/', 1)[-1][:180]}"
    client = _client(); bucket = current_app.config["OBJECT_STORAGE_BUCKET"]
    return {"key": key, "upload_url": client.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": key, "ContentType": content_type}, ExpiresIn=current_app.config["PAYMENT_PROOF_SIGNED_URL_TTL_SECONDS"]), "expires_in": current_app.config["PAYMENT_PROOF_SIGNED_URL_TTL_SECONDS"]}


def save_proof_file(file_bytes: bytes, user_id: int, filename: str, content_type: str, size_bytes: int) -> dict:
    """Upload a file directly to R2 from the server (no CORS issues)."""
    if content_type not in ALLOWED_PROOF_TYPES or size_bytes < 1 or size_bytes > current_app.config["PAYMENT_PROOF_MAX_BYTES"]:
        raise StorageError("Only PDF, JPG, PNG or WEBP files within the permitted size are accepted.")
    key = f"payment-proofs/{user_id}/{uuid.uuid4()}-{filename.rsplit('/', 1)[-1][:180]}"
    config = current_app.config
    required = ("OBJECT_STORAGE_ENDPOINT", "OBJECT_STORAGE_BUCKET", "OBJECT_STORAGE_ACCESS_KEY_ID", "OBJECT_STORAGE_SECRET_ACCESS_KEY")
    if not all(config.get(key) for key in required):
        raise StorageError("Payment proof storage is not configured.")
    client = boto3.client("s3", endpoint_url=config["OBJECT_STORAGE_ENDPOINT"], aws_access_key_id=config["OBJECT_STORAGE_ACCESS_KEY_ID"], aws_secret_access_key=config["OBJECT_STORAGE_SECRET_ACCESS_KEY"], region_name=config.get("OBJECT_STORAGE_REGION", "auto"), config=BotoConfig(signature_version="s3v4"))
    client.put_object(Bucket=config["OBJECT_STORAGE_BUCKET"], Key=key, Body=file_bytes, ContentType=content_type)
    return {"key": key}


def proof_exists(key: str) -> bool:
    try:
        _client().head_object(Bucket=current_app.config["OBJECT_STORAGE_BUCKET"], Key=key)
        return True
    except Exception:
        return False


def read_url(key: str) -> str:
    return _client().generate_presigned_url("get_object", Params={"Bucket": current_app.config["OBJECT_STORAGE_BUCKET"], "Key": key}, ExpiresIn=current_app.config["PAYMENT_PROOF_SIGNED_URL_TTL_SECONDS"])


def save_image_file(file_bytes: bytes, product_id: int, filename: str, content_type: str, size_bytes: int) -> dict:
    """Upload a product image directly to R2 from the server (no CORS issues)."""
    config = current_app.config
    required = ("PRODUCT_IMAGE_ENDPOINT", "PRODUCT_IMAGE_BUCKET", "OBJECT_STORAGE_ACCESS_KEY_ID", "OBJECT_STORAGE_SECRET_ACCESS_KEY")
    if not all(config.get(key) for key in required): raise StorageError("Product image storage is not configured.")
    if content_type not in ALLOWED_PRODUCT_IMAGE_TYPES or size_bytes < 1 or size_bytes > config["PRODUCT_IMAGE_MAX_BYTES"]: raise StorageError("Only JPG, PNG or WEBP product images within the permitted size are accepted.")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    key = f"products/{product_id}/image.{suffix}"
    client = boto3.client("s3", endpoint_url=str(config["PRODUCT_IMAGE_ENDPOINT"]).strip(), aws_access_key_id=str(config["OBJECT_STORAGE_ACCESS_KEY_ID"]).strip(), aws_secret_access_key=str(config["OBJECT_STORAGE_SECRET_ACCESS_KEY"]).strip(), region_name=str(config.get("OBJECT_STORAGE_REGION", "auto")).strip() or "auto", config=BotoConfig(signature_version="s3v4"))
    client.put_object(Bucket=config["PRODUCT_IMAGE_BUCKET"], Key=key, Body=file_bytes, ContentType=content_type)
    public_base = config.get("PRODUCT_IMAGE_PUBLIC_URL") or f"{config['PRODUCT_IMAGE_ENDPOINT'].rstrip('/')}/{config['PRODUCT_IMAGE_BUCKET']}"
    return {"key": key, "public_url": f"{public_base.rstrip('/')}/{key}"}


def create_product_image_upload(product_id: int, filename: str, content_type: str, size_bytes: int) -> dict:
    config = current_app.config
    required = ("PRODUCT_IMAGE_ENDPOINT", "PRODUCT_IMAGE_BUCKET", "OBJECT_STORAGE_ACCESS_KEY_ID", "OBJECT_STORAGE_SECRET_ACCESS_KEY")
    if not all(config.get(key) for key in required): raise StorageError("Product image storage is not configured.")
    if content_type not in ALLOWED_PRODUCT_IMAGE_TYPES or size_bytes < 1 or size_bytes > config["PRODUCT_IMAGE_MAX_BYTES"]: raise StorageError("Only JPG, PNG or WEBP product images within the permitted size are accepted.")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    key = f"products/{product_id}/image.{suffix}"
    client = boto3.client("s3", endpoint_url=config["PRODUCT_IMAGE_ENDPOINT"], aws_access_key_id=config["OBJECT_STORAGE_ACCESS_KEY_ID"], aws_secret_access_key=config["OBJECT_STORAGE_SECRET_ACCESS_KEY"], region_name=config.get("OBJECT_STORAGE_REGION", "auto"), config=BotoConfig(signature_version="s3v4"))
    public_base = config.get("PRODUCT_IMAGE_PUBLIC_URL") or f"{config['PRODUCT_IMAGE_ENDPOINT'].rstrip('/')}/{config['PRODUCT_IMAGE_BUCKET']}"
    return {"key": key, "upload_url": client.generate_presigned_url("put_object", Params={"Bucket": config["PRODUCT_IMAGE_BUCKET"], "Key": key, "ContentType": content_type}, ExpiresIn=config["PAYMENT_PROOF_SIGNED_URL_TTL_SECONDS"]), "public_url": f"{public_base.rstrip('/')}/{key}"}
