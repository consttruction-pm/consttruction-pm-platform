from construction_pm.scheduling.schedule import (
    CriticalActivityPathType as ScheduleCriticalActivityPathType,
    ScheduleMode as ScheduleModeFromSchedule,
    ScheduleOptions as ScheduleOptionsFromSchedule,
    TotalFloatCalculationType as ScheduleTotalFloatCalculationType,
)
from construction_pm.scheduling.schedule_options import (
    CriticalActivityPathType,
    ScheduleMode,
    ScheduleOptions,
    StartToStartLagCalculationType,
    TotalFloatCalculationType,
    start_to_start_lag_type_from_p6,
    start_to_start_lag_type_to_p6,
)


def test_schedule_options_has_one_canonical_identity():
    assert ScheduleOptionsFromSchedule is ScheduleOptions
    assert ScheduleModeFromSchedule is ScheduleMode
    assert ScheduleTotalFloatCalculationType is TotalFloatCalculationType
    assert ScheduleCriticalActivityPathType is CriticalActivityPathType


def test_p6_start_to_start_boolean_adapter_is_preserved():
    assert start_to_start_lag_type_from_p6(False) is StartToStartLagCalculationType.EARLY_START
    assert start_to_start_lag_type_from_p6(True) is StartToStartLagCalculationType.ACTUAL_START
    assert start_to_start_lag_type_to_p6(StartToStartLagCalculationType.EARLY_START) is False
    assert start_to_start_lag_type_to_p6(StartToStartLagCalculationType.ACTUAL_START) is True
