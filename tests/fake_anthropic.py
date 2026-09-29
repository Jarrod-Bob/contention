"""An in-memory stand-in for the Anthropic Message Batches API, for tests."""


class FakeBatches:
    def __init__(self, results_by_batch: dict[str, list]):
        self.results_by_batch = results_by_batch
        self.calls = []

    def results(self, batch_id):
        self.calls.append(("results", batch_id))
        return iter(self.results_by_batch[batch_id])

    def delete(self, batch_id):
        self.calls.append(("delete", batch_id))
        del self.results_by_batch[batch_id]


class FakeMessages:
    def __init__(self, batches: FakeBatches):
        self.batches = batches


class FakeAnthropic:
    def __init__(self, results_by_batch: dict[str, list]):
        self.messages = FakeMessages(FakeBatches(results_by_batch))
