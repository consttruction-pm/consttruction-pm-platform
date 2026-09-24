from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
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


def test_conflict_preserves_expected_revision_and_requests_refresh() -> None:
    from construction_pm.client_sync.e2e_conflict_flow import ConflictSyncFlow

    class ConflictTransport:
        def submit(self, submitted: OfflineMutation) -> SyncOutcome:
            return SyncOutcome(submitted.mutation_id, SyncDisposition.CONFLICT, error_code="STALE_REVISION")

    result = ConflictSyncFlow(ConflictTransport()).submit_once(mutation())

    assert result.outcome.disposition is SyncDisposition.CONFLICT
    assert result.outcome.error_code == "STALE_REVISION"
    assert result.requires_refresh is True
    assert result.preserved_expected_revision == 7


def test_application_sync_gateway_maps_stale_revision_to_conflict() -> None:
    class OptimisticLockError(Exception):
        pass

    class Handler:
        def handle(self, submitted: OfflineMutation) -> None:
            assert submitted.expected_revision == 7
            raise OptimisticLockError("stale")

    outcome = ApplicationSyncGateway("t1", "p1", Handler()).submit_mutation(mutation())

    assert outcome == SyncOutcome("m1", SyncDisposition.CONFLICT, error_code="STALE_REVISION")


def test_application_sync_gateway_rejects_cross_project_context() -> None:
    class Handler:
        def handle(self, submitted: OfflineMutation) -> None:
            raise AssertionError("handler must not run")

    altered = OfflineMutation("m2", "t1", "p2", 7, "update_activity", {}, "idem-2")
    outcome = ApplicationSyncGateway("t1", "p1", Handler()).submit_mutation(altered)

    assert outcome == SyncOutcome("m2", SyncDisposition.REJECTED, error_code="INVALID_PROJECT_CONTEXT")


def test_atomic_application_gateway_delegates_to_transactional_executor() -> None:
    from construction_pm.client_sync.application_gateway import AtomicApplicationSyncGateway

    mutation_value = mutation()
    class Executor:
        def __init__(self):
            self.seen = None
        def submit(self, submitted):
            self.seen = submitted
            return SyncOutcome(submitted.mutation_id, SyncDisposition.ACKNOWLEDGED)

    executor = Executor()
    gateway = AtomicApplicationSyncGateway("t1", "p1", executor)
    outcome = gateway.submit_mutation(mutation_value)
    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert executor.seen == mutation_value

    rejected = gateway.submit_mutation(OfflineMutation("m3", "t1", "other", 7, "update_activity", {}, "idem-3"))
    assert rejected.disposition is SyncDisposition.REJECTED
    assert rejected.error_code == "INVALID_PROJECT_CONTEXT"


def test_transactional_application_gateway_persists_conflict_atomically() -> None:
    from construction_pm.client_sync.application_gateway import TransactionalApplicationSyncGateway
    from construction_pm.client_sync.server_idempotency import InMemoryServerIdempotencyStore

    class Tx:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0
        class Ctx:
            def __init__(self, outer): self.outer = outer
            def __enter__(self): return None
            def __exit__(self, typ, value, tb):
                if typ is None: self.outer.commits += 1
                else: self.outer.rollbacks += 1
                return False
        def transaction(self): return self.Ctx(self)

    class Persistence(InMemoryServerIdempotencyStore):
        def __init__(self):
            super().__init__()
            self.conflicts = {}
        def get_idempotency(self, tenant_id, project_id, key):
            return self.lookup(OfflineMutation("probe", tenant_id, project_id, 0, "probe", {}, key))
        def put_idempotency(self, record): self._records[(record.tenant_id, record.project_id, record.idempotency_key)] = record
        def save_conflict(self, mutation_id, tenant_id, project_id, context): self.conflicts[(tenant_id, project_id, mutation_id)] = context
        def get_conflict(self, mutation_id, tenant_id, project_id): return self.conflicts.get((tenant_id, project_id, mutation_id))

    class Handler:
        def handle(self, submitted):
            class OptimisticLockError(Exception): pass
            raise OptimisticLockError("stale")

    persistence = Persistence()
    tx = Tx()
    gateway = TransactionalApplicationSyncGateway("t1", "p1", persistence, tx, Handler())
    outcome = gateway.submit_mutation(mutation())
    assert outcome.disposition is SyncDisposition.CONFLICT
    assert persistence.get_conflict("m1", "t1", "p1") is not None
    assert tx.commits == 1
    replay = gateway.submit_mutation(mutation())
    assert replay == outcome
    assert tx.commits == 2
