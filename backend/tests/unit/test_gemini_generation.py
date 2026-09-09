from types import SimpleNamespace

from lecture_notes_rag.generation.gemini import GeminiProvider, GroundingContext


class _FakeModels:
    def __init__(self) -> None:
        self.config = None

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.config = kwargs["config"]
        return SimpleNamespace(
            text=(
                '{"answer":"Supported claim [S1]","citations":["S1"],'
                '"grounded":true}'
            )
        )


def test_generation_explicitly_disables_automatic_function_calling() -> None:
    models = _FakeModels()
    provider = object.__new__(GeminiProvider)
    provider._settings = SimpleNamespace(gemini_generation_model="gemini-test")
    provider._client = SimpleNamespace(models=models)

    provider.answer(
        "What is the claim?",
        [
            GroundingContext(
                label="S1",
                title="Notes",
                source_path="notes.pdf",
                semester=1,
                course="Test",
                page_start=1,
                page_end=1,
                text="Supported claim.",
            )
        ],
    )

    assert models.config.automatic_function_calling.disable is True
