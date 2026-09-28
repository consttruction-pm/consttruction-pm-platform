from construction_pm.p6_option_registry import schedule_option_choices


def test_p6_schedule_option_choices_match_release_26_documentation():
    assert schedule_option_choices("ComputeTotalFloatType") == (
        "Start Float",
        "Finish Float",
        "Smallest of Start Float and Finish Float",
    )
    assert schedule_option_choices("CriticalActivityPathType") == (
        "Critical Float",
        "Longest Path",
    )
    assert schedule_option_choices("OutOfSequenceScheduleType") == (
        "Retained Logic",
        "Progress Override",
        "Actual Dates",
    )
    assert schedule_option_choices("RelationshipLagCalendar") == (
        "Predecessor Activity Calendar",
        "Successor Activity Calendar",
        "24 Hour Calendar",
        "Project Default Calendar",
    )
    assert schedule_option_choices("PercentCompleteType") == (
        "Physical",
        "Duration",
        "Units",
    )
