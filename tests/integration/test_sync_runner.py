from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.offline_store import InMemoryOfflineMutationStore
from construction_pm.client_sync.sync_adapter import ApplicationSyncAdapter
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome
from construction_pm.client_sync.sync_runner import SyncRunner
from construction_pm.client_sync.server_gateway import IdempotentMutationGateway
from construction_pm.client_sync.server_idempotency import InMemoryServerIdempotencyStore


class Gateway:
    def __init__(self, disposition: SyncDisposition) -> None:
        self.disposition = disposition
        self.received: list[str] = []

    def submit_mutation(self, mutation: OfflineMutation) -> SyncOutcome:
        self.received.append(mutation.mutation_id)
        return SyncOutcome(mutation.mutation_id, self.disposition, retry_after_seconds=2 if self.disposition == SyncDisposition.RETRY else None)


def mutation() -> OfflineMutation:
    return OfflineMutation("m1", "t1", "p1", 7, "update_activity", {"activity_id": "A1"}, "idem-1")


def test_acknowledged_is_removed() -> None:
    store = InMemoryOfflineMutationStore()
    store.append(mutation())
    runner = SyncRunner(store, ApplicationSyncAdapter(Gateway(SyncDisposition.ACKNOWLEDGED)))
    outcomes = runner.run_once()
    assert outcomes[0].disposition == SyncDisposition.ACKNOWLEDGED
    assert store.pending() == ()


def test_retry_and_conflict_are_retained() -> None:
    for disposition in (SyncDisposition.RETRY, SyncDisposition.CONFLICT, SyncDisposition.REJECTED):
        store = InMemoryOfflineMutationStore()
        store.append(mutation())
        runner = SyncRunner(store, ApplicationSyncAdapter(Gateway(disposition)))
        runner.run_once()
        assert len(store.pending()) == 1


def test_runner_connects_through_application_adapter_to_versioned_gateway() -> None:
    class VersionedGateway:
        def __init__(self) -> None:
            self.received: list[OfflineMutation] = []
            self.idempotent = IdempotentMutationGateway(InMemoryServerIdempotencyStore())

        def submit_mutation(self, mutation: OfflineMutation) -> SyncOutcome:
            self.received.append(mutation)
            return self.idempotent.execute(
                mutation,
                SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED),
            )

    gateway = VersionedGateway()
    store = InMemoryOfflineMutationStore()
    store.append(mutation())
    runner = SyncRunner(store, ApplicationSyncAdapter(gateway))

    outcomes = runner.run_once()

    assert outcomes == (SyncOutcome("m1", SyncDisposition.ACKNOWLEDGED),)
    assert [item.mutation_id for item in gateway.received] == ["m1"]
    assert store.pending() == ()


def test_runner_preserves_non_acknowledged_outcomes_through_application_gateway() -> None:
    for disposition in (SyncDisposition.RETRY, SyncDisposition.CONFLICT, SyncDisposition.REJECTED):
        class VersionedGateway:
            def submit_mutation(self, submitted: OfflineMutation) -> SyncOutcome:
                return SyncOutcome(
                    submitted.mutation_id,
                    disposition,
                    retry_after_seconds=2 if disposition == SyncDisposition.RETRY else None,
                )

        store = InMemoryOfflineMutationStore()
        store.append(mutation())
        runner = SyncRunner(store, ApplicationSyncAdapter(VersionedGateway()))

        outcomes = runner.run_once()

        assert outcomes == (
            SyncOutcome(
                "m1",
                disposition,
                retry_after_seconds=2 if disposition == SyncDisposition.RETRY else None,
            ),
        )
        assert store.pending() == (mutation(),)
