# Stage 33.4.31 — Time-Aware Backward Pass + Float

Date: 2026-09-24

## Implemented

Shared Core now has:
- time_backward_pass()
- calculate_time_floats()
- time_schedule()
- TimeFloatActivity
- TimeScheduleResult

The Backward Pass derives latest dates from successor late dates using the same FS/SS/FF/SF and signed working-hour lag semantics as the Forward Pass.

## Float

Total Float is measured in authoritative working hours between early and late start. Negative Total Float is preserved and is critical under the zero threshold.

Free Float is relationship-aware and uses the successor's early schedule and relationship-lag calendar.

## Calendar consistency

Activity duration uses the activity calendar. Relationship lag uses the successor-side relationship-lag calendar. No client implements an alternative calculation.

## Remaining gates

- time-aware constraint integration
- richer time-aware schedule options
- full project portability for per-activity duration/calendar data
- cross-client API schema/regression pack
- final P6 time-based parity certification

Runtime CI execution remains unverified.
