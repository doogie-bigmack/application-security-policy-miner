"""LLM provider abstraction for private endpoints."""
import logging
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def create_message(self, prompt: str, max_tokens: int = 4096, temperature: float = 0) -> str:
        """Create a message using the LLM provider.

        Args:
            prompt: The user prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation (0-1)

        Returns:
            The LLM response text
        """
        pass


class AWSBedrockProvider(LLMProvider):
    """AWS Bedrock LLM provider using Anthropic Claude models."""

    def __init__(self):
        """Initialize AWS Bedrock provider."""
        try:
            import boto3
            from botocore.config import Config

            # Configure boto3 with private VPC endpoint if needed
            config = Config(
                region_name=settings.AWS_BEDROCK_REGION,
                signature_version="v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )

            # Create Bedrock client
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.client = boto3.client(
                    "bedrock-runtime",
                    config=config,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
            else:
                # Use IAM role or instance profile
                self.client = boto3.client("bedrock-runtime", config=config)

            self.model_id = settings.AWS_BEDROCK_MODEL_ID
            logger.info(f"AWS Bedrock provider initialized with model {self.model_id}")

        except ImportError:
            raise ImportError(
                "boto3 is required for AWS Bedrock. Install with: pip install boto3"
            )

    def create_message(self, prompt: str, max_tokens: int = 4096, temperature: float = 0) -> str:
        """Create a message using AWS Bedrock.

        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            The LLM response text
        """
        import json

        try:
            # Build request body for Anthropic Claude on Bedrock
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            # Call Bedrock API
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            content = response_body["content"]

            # Extract text from content blocks
            if isinstance(content, list) and len(content) > 0:
                return content[0]["text"]
            else:
                raise ValueError(f"Unexpected response format: {response_body}")

        except Exception as e:
            logger.error(f"Error calling AWS Bedrock: {e}")
            raise


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI LLM provider using Anthropic Claude models."""

    def __init__(self):
        """Initialize Azure OpenAI provider."""
        try:
            from openai import AzureOpenAI

            if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_API_KEY:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set"
                )

            # Create Azure OpenAI client
            self.client = AzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )

            self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
            logger.info(
                f"Azure OpenAI provider initialized with deployment {self.deployment_name}"
            )

        except ImportError:
            raise ImportError(
                "openai is required for Azure OpenAI. Install with: pip install openai"
            )

    def create_message(self, prompt: str, max_tokens: int = 4096, temperature: float = 0) -> str:
        """Create a message using Azure OpenAI.

        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            The LLM response text
        """
        try:
            # Call Azure OpenAI API
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract response text
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                raise ValueError(f"Unexpected response format: {response}")

        except Exception as e:
            logger.error(f"Error calling Azure OpenAI: {e}")
            raise


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider.

    Returns:
        LLM provider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "aws_bedrock":
        return AWSBedrockProvider()
    elif provider_name == "azure_openai":
        return AzureOpenAIProvider()
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_name}. "
            "Supported providers: aws_bedrock, azure_openai"
        )
