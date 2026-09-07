import pytest
from google.genai.errors import ClientError

from lecture_notes_rag.generation.gemini import GeminiRateLimitError, _raise_rate_limit_error


def test_google_client_error_is_classified_using_sdk_code_attribute() -> None:
    error = ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded. Please retry in 49.25s.",
                "status": "RESOURCE_EXHAUSTED",
            }
        },
    )

    with pytest.raises(GeminiRateLimitError) as raised:
        _raise_rate_limit_error(error)

    assert raised.value.retry_after_seconds == 49.25


def test_non_quota_google_client_error_is_not_reclassified() -> None:
    error = ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT"}})

    with pytest.raises(ClientError):
        _raise_rate_limit_error(error)
