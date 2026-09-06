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
    pacer.wait_for_slot()
    pacer.wait_for_slot()

    assert waits == [1.0]


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
