from __future__ import annotations

from dataclasses import dataclass

from .const import (
    CCT_TEMPERATURE_MAX,
    CCT_TEMPERATURE_MIN,
    CCT_TEMPERATURE_REAL_MAX,
    CCT_TEMPERATURE_REAL_MIN,
)


@dataclass(frozen=True)
class LexmanCCTSmartBulbState:
    power: bool | None = None
    brightness: int | None = None
    temperature: int | None = None

    @property
    def temperature_kelvin(self) -> int | None:
        if self.temperature is None:
            return None
        return round(
            (self.temperature - CCT_TEMPERATURE_MIN)
            * (CCT_TEMPERATURE_REAL_MAX - CCT_TEMPERATURE_REAL_MIN)
            / (CCT_TEMPERATURE_MAX - CCT_TEMPERATURE_MIN)
            + CCT_TEMPERATURE_REAL_MIN
        )
