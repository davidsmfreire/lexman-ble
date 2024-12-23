"""Lexman BLE integration light platform."""

from __future__ import annotations

from typing import Any

from lexman_ble import LexmanCCTSmartBulb

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_FLASH,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .models import LexmanCCTSmartBulbData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform for Lexman cct smart bulb."""
    data: LexmanCCTSmartBulbData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [LexmanCCTSmartBulbEntity(data.coordinator, data.device, entry.title)]
    )


class LexmanCCTSmartBulbEntity(
    CoordinatorEntity[DataUpdateCoordinator[None]], LightEntity
):
    """Representation of Lexman CCT smart bulb device."""

    _attr_supported_color_modes: set[ColorMode] | set[str] | None = {
        ColorMode.COLOR_TEMP
    }
    _attr_color_mode: ColorMode | str | None = ColorMode.COLOR_TEMP
    _attr_has_entity_name: bool = True
    _attr_name: str | None = None
    _attr_supported_features: LightEntityFeature = LightEntityFeature.FLASH

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[None],
        device: LexmanCCTSmartBulb,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = device.address
        self._attr_device_info = DeviceInfo(
            name=name,
            connections={(dr.CONNECTION_BLUETOOTH, device.address)},
        )
        self._attr_min_color_temp_kelvin = device.temperature_range_kelvin[0]
        self._attr_max_color_temp_kelvin = device.temperature_range_kelvin[1]
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        device = self._device
        self._attr_brightness = device.brightness
        self._attr_color_temp_kelvin = device.temperature_kelvin
        self._attr_is_on = device.on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if brightness is not None:
                await self._device.set_brightness(round(brightness / 255 * 100))
                self._handle_coordinator_update()
                return

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            await self._device.set_temperature(kwargs[ATTR_COLOR_TEMP_KELVIN])
            self._handle_coordinator_update()
            return

        if ATTR_FLASH in kwargs:
            await self._device.ping()
            self._handle_coordinator_update()
            return

        await self._device.turn_on()
        self._handle_coordinator_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        await self._device.turn_off()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            self._device.register_callback(self._handle_coordinator_update)
        )
        return await super().async_added_to_hass()
