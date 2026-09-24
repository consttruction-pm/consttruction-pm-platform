from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 2
    max_delay_seconds: int = 300

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("INVALID_MAX_ATTEMPTS")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("INVALID_RETRY_DELAY")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("INVALID_RETRY_WINDOW")

    def delay_seconds(self, attempt: int) -> int:
        if attempt < 1:
            raise ValueError("INVALID_ATTEMPT")
        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)
