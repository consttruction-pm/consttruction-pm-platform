from __future__ import annotations

from dataclasses import dataclass

CALENDAR_KINDS = frozenset({'working-day', 'working-time'})

@dataclass(frozen=True)
class ClientCalendarReference:
    calendar_id: str
    calendar_version: str
    kind: str = 'working-day'
    contract_version = 'client-calendar-reference.v1'

    def validate(self) -> None:
        if not self.calendar_id.strip(): raise ValueError('calendar_id is required')
        if not self.calendar_version.strip(): raise ValueError('calendar_version is required')
        if self.kind not in CALENDAR_KINDS: raise ValueError('unsupported calendar kind')

    def to_payload(self) -> dict[str, str]:
        self.validate()
        return {'contract_version': self.contract_version, 'calendar_id': self.calendar_id, 'calendar_version': self.calendar_version, 'kind': self.kind}

@dataclass(frozen=True)
class ClientCalendarContext:
    project: ClientCalendarReference
    activity: ClientCalendarReference | None = None
    relationship_lag: ClientCalendarReference | None = None
    contract_version = 'client-calendar-context.v1'

    def validate(self) -> None:
        self.project.validate()
        if self.activity is not None: self.activity.validate()
        if self.relationship_lag is not None: self.relationship_lag.validate()

    def effective_activity(self) -> ClientCalendarReference:
        self.validate()
        return self.activity or self.project

    def effective_relationship_lag(self) -> ClientCalendarReference:
        self.validate()
        return self.relationship_lag or self.effective_activity()

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {'contract_version': self.contract_version, 'project': self.project.to_payload(), 'activity': None if self.activity is None else self.activity.to_payload(), 'relationship_lag': None if self.relationship_lag is None else self.relationship_lag.to_payload()}
