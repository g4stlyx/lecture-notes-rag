from lecture_notes_rag.services.rate_limit import RequestPacer


def test_request_pacer_spaces_out_embedding_requests() -> None:
    current_time = [0.0]
    waits: list[float] = []

    def clock() -> float:
        return current_time[0]

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        current_time[0] += seconds

    pacer = RequestPacer(60, clock=clock, sleep=sleep)
    pacer.wait_for_slot(units=2)
    pacer.wait_for_slot()

    assert waits == [2.0]


def test_request_pacer_honors_provider_retry_delay() -> None:
    current_time = [0.0]
    waits: list[float] = []

    def clock() -> float:
        return current_time[0]

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        current_time[0] += seconds

    pacer = RequestPacer(120, clock=clock, sleep=sleep)
    pacer.defer_for(25)
    pacer.wait_for_slot()

    assert waits == [25]


def test_request_pacer_rejects_non_positive_request_cost() -> None:
    pacer = RequestPacer(60)

    try:
        pacer.wait_for_slot(units=0)
    except ValueError as error:
        assert "at least one" in str(error)
    else:
        raise AssertionError("Expected invalid request cost to fail")
