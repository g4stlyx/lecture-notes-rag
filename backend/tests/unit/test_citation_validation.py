from lecture_notes_rag.domain.schemas import GeminiAnswerDraft
from lecture_notes_rag.generation.gemini import validate_answer_draft


def test_citation_validation_removes_hallucinated_labels() -> None:
    draft = GeminiAnswerDraft(
        answer="A stack is LIFO [S1]. Ignore this [S99].",
        citations=["S1", "S99"],
        grounded=True,
    )

    validated = validate_answer_draft(draft, {"S1", "S2"})

    assert validated.grounded is True
    assert validated.citations == ["S1"]
    assert "[S99]" not in validated.answer


def test_citation_validation_refuses_unsupported_grounded_answer() -> None:
    draft = GeminiAnswerDraft(
        answer="An unsupported claim [S99].", citations=["S99"], grounded=True
    )

    validated = validate_answer_draft(draft, {"S1"})

    assert validated.grounded is False
    assert validated.citations == []
    assert "could not produce" in validated.answer.lower()
