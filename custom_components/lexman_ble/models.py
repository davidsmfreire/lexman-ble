"""The lexman BLE integration models."""

from __future__ import annotations

from dataclasses import dataclass

from lexman_ble import LexmanCCTSmartBulb

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


@dataclass
class LexmanCCTSmartBulbData:
    """Data for the lexman ble integration."""

    title: str
    device: LexmanCCTSmartBulb
    coordinator: DataUpdateCoordinator[None]
