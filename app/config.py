"""
Centralized application configuration.

All configuration is loaded from environment variables (or a local .env file
during development). Nothing sensitive is hardcoded, and AWS credentials are
optional -- in a real AWS deployment (Lambda/ECS/EC2 with an attached IAM
role) these should be left blank and boto3 will resolve credentials from the
execution role automatically.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Application ---
    app_name: str = "OrderFlow"
    environment: str = "development"
    debug: bool = True

    # --- Database ---
    database_url: str = "postgresql+psycopg2://orderflow:orderflow@localhost:5432/orderflow"

    # --- JWT ---
    jwt_secret_key: str = "insecure-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # --- AWS core ---
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_endpoint_url: Optional[str] = None  # useful for localstack

    # --- AWS SQS ---
    sqs_queue_url: Optional[str] = None
    sqs_dlq_url: Optional[str] = None

    # --- AWS SNS ---
    sns_topic_arn: Optional[str] = None

    # --- AWS S3 ---
    s3_bucket_name: Optional[str] = None

    # When true, AWS wrapper modules log-and-skip instead of calling AWS.
    # This lets the full application run locally without any AWS account.
    aws_disabled: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
