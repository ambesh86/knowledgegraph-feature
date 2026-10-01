#C:\Users\Ambesh.Kumar\Downloads\CSL-Bio-informatics\knowledgegraph-feature-nextgen\agents\eugene-agent-ws\src
#!/usr/bin/env python3
"""
Fetch secrets from AWS Secrets Manager and write to .env file
"""
import json
import argparse
import logging
import boto3
from botocore.exceptions import ClientError


# Configure logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_secret(secret_name: str, region_name: str = "us-east-1") -> dict:
    """
    Retrieve secret from AWS Secrets Manager

    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region (default: us-east-1)

    Returns:
        Dictionary containing secret key-value pairs
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise Exception(f"Error retrieving secret: {e}")

    secret = get_secret_value_response["SecretString"]
    return json.loads(secret)


def write_env_file(secrets: dict, env_file_path: str = ".env"):
    """
    Write secrets to .env file

    Args:
        secrets: Dictionary of environment variables
        env_file_path: Path to .env file (default: .env)
    """
    with open(env_file_path, "w") as f:
        for key, value in secrets.items():
            f.write(f"{key}={value}\n")
    logger.info(f"Successfully wrote {len(secrets)} variables to {env_file_path}")


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Fetch secrets from AWS Secrets Manager and write to .env file"
    )
    parser.add_argument(
        "--secret-name",
        default="eugene/dev/agent_ws/env",
        help="Name of the secret in AWS Secrets Manager (default: eugene/dev/agent_ws/env)",
    )
    parser.add_argument(
        "--env-file", default=".env", help="Path to output .env file (default: .env)"
    )
    parser.add_argument(
        "--region", default="us-east-1", help="AWS region (default: us-east-1)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Eugene identity/configuration is required; provider credentials are optional.
    required_keys = [
        "EUGENE_MCP_SERVER_URL",
        "EUGENE_AGENT_ALLOWLIST",
        "EUGENE_CLIENT_ID",
        "EUGENE_CLIENT_SECRET",
        "EUGENE_TENANT_ID",
    ]
    optional_keys = [
        "LLM_PROVIDER",
        "LLM_FALLBACK_PROVIDER",
        "BEDROCK_MODEL_ID",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "OPENAI_API_KEY",
        "OPENAI_MODEL_ID",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL_ID",
    ]

    logger.info(f"Fetching secrets from AWS Secrets Manager: {args.secret_name}")
    secrets = get_secret(args.secret_name, args.region)

    # Filter to only expected keys (optional - remove if you want all keys)
    allowed_keys = set(required_keys + optional_keys)
    filtered_secrets = {k: v for k, v in secrets.items() if k in allowed_keys}

    # Warn about missing keys
    missing_keys = set(required_keys) - set(filtered_secrets.keys())
    if missing_keys:
        logger.info(f"Warning: Missing keys in secret: {missing_keys}")

    write_env_file(filtered_secrets, args.env_file)


if __name__ == "__main__":
    main()
