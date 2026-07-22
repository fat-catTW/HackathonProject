"""AWS session helpers shared by Bedrock, DynamoDB, and Lambda clients."""
from __future__ import annotations

import os
from functools import lru_cache

try:
    import boto3
    from botocore.config import Config
except ImportError:  # pragma: no cover - optional before dependencies are installed
    boto3 = None
    Config = None

from ..config import get_settings


def _session_kwargs() -> dict:
    settings = get_settings()
    kwargs: dict = {}
    for env_name in ("AWS_PROFILE", "AWS_SESSION_TOKEN", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        if os.getenv(env_name) == "":
            os.environ.pop(env_name, None)
    if settings.aws_profile:
        kwargs["profile_name"] = settings.aws_profile
    if settings.aws_region:
        kwargs["region_name"] = settings.aws_region
    if settings.has_explicit_aws_credentials:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token
    return kwargs


@lru_cache
def get_boto3_session():
    if boto3 is None:
        raise RuntimeError("boto3 is not installed. Run `pip install -r backend/requirements.txt`.")
    return boto3.Session(**_session_kwargs())


def has_aws_credentials() -> bool:
    try:
        return get_boto3_session().get_credentials() is not None
    except Exception:
        return False


def get_aws_client(service_name: str):
    if Config is None:
        raise RuntimeError("botocore is not installed. Run `pip install -r backend/requirements.txt`.")
    settings = get_settings()
    return get_boto3_session().client(
        service_name,
        region_name=settings.aws_region,
        config=Config(read_timeout=20, connect_timeout=5, retries={"max_attempts": 2}),
    )


def get_aws_resource(service_name: str):
    settings = get_settings()
    return get_boto3_session().resource(service_name, region_name=settings.aws_region)
