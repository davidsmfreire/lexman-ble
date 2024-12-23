import asyncio
import logging
from collections.abc import Callable
from dataclasses import replace
from typing import Optional

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakDBusError, BleakError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    BleakNotFoundError,
    establish_connection,
    retry_bluetooth_connection_error,
)

from .const import (
    CCT_TEMPERATURE_MAX,
    CCT_TEMPERATURE_MIN,
    CCT_TEMPERATURE_REAL_MAX,
    CCT_TEMPERATURE_REAL_MIN,
    READ_CHAR_UUID,
    WRITE_CHAR_UUID,
    CctSmartBulbCommand,
    CctSmartBulbCommandInstance,
)
from .exceptions import CharacteristicMissingError
from .models import LexmanCCTSmartBulbState

BLEAK_BACKOFF_TIME = 0.25

DISCONNECT_DELAY = 120

RETRY_BACKOFF_EXCEPTIONS = (BleakDBusError,)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

DEFAULT_ATTEMPTS = 3

# The lexman smart bulb responds to all commands
WRITE_WITH_RESPONSE = True


class LexmanCCTSmartBulb:
    def __init__(
        self, ble_device: BLEDevice, advertisement_data: AdvertisementData | None = None
    ) -> None:
        """Init the LEDBLE."""
        self._ble_device: BLEDevice = ble_device
        self._advertisement_data: AdvertisementData | None = advertisement_data
        self._operation_lock: asyncio.Lock = asyncio.Lock()
        self._state: LexmanCCTSmartBulbState = LexmanCCTSmartBulbState()
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._read_char: BleakGATTCharacteristic | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._client: BleakClientWithServiceCache | None = None
        self._expected_disconnect: bool = False
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self._callbacks: list[Callable[[LexmanCCTSmartBulbState], None]] = []
        self._last_command: CctSmartBulbCommandInstance | None = None

    def set_ble_device_and_advertisement_data(
        self, ble_device: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Set the ble device."""
        self._ble_device = ble_device
        self._advertisement_data = advertisement_data

    @property
    def address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def _address(self) -> str:
        """Return the address."""
        return self._ble_device.address

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self._ble_device.name or self._ble_device.address

    @property
    def rssi(self) -> int | None:
        """Get the rssi of the device."""
        if self._advertisement_data:
            return self._advertisement_data.rssi
        return None

    @property
    def state(self) -> LexmanCCTSmartBulbState:
        """Return the state."""
        return self._state

    @property
    def on(self) -> Optional[bool]:
        return self._state.power

    @property
    def brightness(self) -> Optional[int]:
        """Return current brightness 0-254."""
        return self._state.brightness

    @property
    def temperature(self) -> Optional[int]:
        f"""Return current temperature {CCT_TEMPERATURE_MIN}-{CCT_TEMPERATURE_MAX}."""
        return self._state.temperature

    @property
    def temperature_kelvin(self) -> Optional[int]:
        f"""Return current temperature {CCT_TEMPERATURE_REAL_MIN}-{CCT_TEMPERATURE_REAL_MAX}."""
        return self._state.temperature_kelvin

    @property
    def temperature_range_kelvin(self) -> tuple[int, int]:
        return (CCT_TEMPERATURE_REAL_MAX, CCT_TEMPERATURE_REAL_MIN)

    async def command(self, command: str):
        await self._send_command(command)

    async def ping(self) -> None:
        await self._send_command(CctSmartBulbCommand.PING.query)

    async def update(self) -> None:
        await self._send_command(CctSmartBulbCommand.SWITCH.query)
        await self._send_command(CctSmartBulbCommand.BRIGHTNESS.query)
        await self._send_command(CctSmartBulbCommand.TEMPERATURE.query)

    async def turn_on(self) -> None:
        """Turn on."""
        _LOGGER.debug("%s: Turn on", self.name)
        await self._send_command(CctSmartBulbCommand.SWITCH.set(1))
        self._state = replace(self._state, power=True)

    async def turn_off(self) -> None:
        """Turn off."""
        _LOGGER.debug("%s: Turn off", self.name)
        await self._send_command(CctSmartBulbCommand.SWITCH.set(0))
        self._state = replace(self._state, power=False)

    async def set_brightness(self, value: int) -> None:
        """Set the brightness. Value from 0 to 100 (%)"""
        _LOGGER.debug("%s: Set brightness: %s", self.name, value)
        if not 0 <= value <= 100:
            raise ValueError(f"Value `{value}` is outside the valid range of 0 - 100")
        brightness = round(max(min(100, value), 0) / 100 * 254)
        await self._send_command(CctSmartBulbCommand.BRIGHTNESS.set(brightness))
        self._state = replace(self._state, brightness=value)

    async def set_temperature(self, value: int) -> None:
        """Set the temperature. Value from 2700 to 6500, where 2700 is warmer and 6500 is cooler"""
        _LOGGER.debug("%s: Set temperature: %s", self.name, value)
        value = max(min(CCT_TEMPERATURE_REAL_MIN, value), CCT_TEMPERATURE_REAL_MAX)
        temperature = round(
            (value - CCT_TEMPERATURE_REAL_MIN)
            * (CCT_TEMPERATURE_MAX - CCT_TEMPERATURE_MIN)
            / (CCT_TEMPERATURE_REAL_MAX - CCT_TEMPERATURE_REAL_MIN)
            + CCT_TEMPERATURE_MIN
        )
        temperature = max(min(CCT_TEMPERATURE_MAX, temperature), CCT_TEMPERATURE_MIN)
        await self._send_command(CctSmartBulbCommand.TEMPERATURE.set(temperature))
        self._state = replace(self._state, temperature=value)

    async def stop(self) -> None:
        """Stop the LEDBLE."""
        _LOGGER.debug("%s: Stop", self.name)
        await self._execute_disconnect()

    def _fire_callbacks(self) -> None:
        """Fire the callbacks."""
        for callback in self._callbacks:
            callback(self._state)

    def register_callback(
        self, callback: Callable[[LexmanCCTSmartBulbState], None]
    ) -> Callable[[], None]:
        """Register a callback to be called when the state changes."""

        def unregister_callback() -> None:
            self._callbacks.remove(callback)

        self._callbacks.append(callback)
        return unregister_callback

    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            _LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            _LOGGER.debug("%s: Connecting; RSSI: %s", self.name, self.rssi)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self.name,
                self._disconnected,
                use_services_cache=True,
                ble_device_callback=lambda: self._ble_device,
            )
            _LOGGER.debug("%s: Connected; RSSI: %s", self.name, self.rssi)
            self._resolve_characteristics(client.services)

            self._client = client
            self._reset_disconnect_timer()

            _LOGGER.debug(
                "%s: Subscribe to notifications; RSSI: %s", self.name, self.rssi
            )
            if self._read_char is None:
                raise RuntimeError("read_char should be set by now")

            await client.start_notify(self._read_char, self._notification_handler)

    def _notification_handler(
        self, _sender: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle notification responses."""
        if self._last_command is None:
            _LOGGER.debug(
                "%s: Notification received: Unknown: %s", self.name, data.hex(sep=":")
            )
            return

        responses_to_expect = [self._last_command] + [
            c.instance() for c in CctSmartBulbCommand if c != self._last_command.type
        ]

        reference_command = None
        for expected in responses_to_expect:
            is_match, new_value = expected.match_response(data.hex(sep=":"))

            if is_match:
                reference_command = expected
                break
        else:
            _LOGGER.error(
                "%s: Notification received: Expected %s's response but got %s",
                self.name,
                self._last_command.name,
                data.hex(sep=":"),
            )
            return

        _LOGGER.debug(
            "%s: Notification received: %s response: %s",
            self.name,
            reference_command.name,
            data.hex(sep=":"),
        )

        if reference_command.type == CctSmartBulbCommand.SWITCH:
            self._state = replace(self._state, power=new_value == 1)
        elif reference_command.type == CctSmartBulbCommand.BRIGHTNESS:
            self._state = replace(self._state, brightness=new_value)
        elif reference_command.type == CctSmartBulbCommand.TEMPERATURE:
            self._state = replace(self._state, temperature=new_value)
        else:
            return

        self._fire_callbacks()

    def _reset_disconnect_timer(self) -> None:
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        self._disconnect_timer = self.loop.call_later(
            DISCONNECT_DELAY, self._disconnect
        )

    def _disconnected(self, _client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            _LOGGER.debug(
                "%s: Disconnected from device; RSSI: %s", self.name, self.rssi
            )
            return
        _LOGGER.warning(
            "%s: Device unexpectedly disconnected; RSSI: %s",
            self.name,
            self.rssi,
        )

    def _disconnect(self) -> None:
        """Disconnect from device."""
        self._disconnect_timer = None
        _ = asyncio.create_task(self._execute_timed_disconnect())

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        _LOGGER.debug(
            "%s: Disconnecting after timeout of %s",
            self.name,
            DISCONNECT_DELAY,
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            read_char = self._read_char
            client = self._client
            self._expected_disconnect = True
            self._client = None
            self._read_char = None
            self._write_char = None
            if client and client.is_connected:
                if read_char:
                    try:
                        await client.stop_notify(read_char)
                    except BleakError:
                        _LOGGER.debug(
                            "%s: Failed to stop notifications", self.name, exc_info=True
                        )
                _ = await client.disconnect()

    @retry_bluetooth_connection_error(DEFAULT_ATTEMPTS)
    async def _send_command_locked(self, command: bytes) -> None:
        """Send command to device and read response."""
        try:
            await self._execute_command_locked(command)
        except BleakDBusError as ex:
            # Disconnect so we can reset state and try again
            await asyncio.sleep(BLEAK_BACKOFF_TIME)
            _LOGGER.debug(
                "%s: RSSI: %s; Backing off %ss; Disconnecting due to error: %s",
                self.name,
                self.rssi,
                BLEAK_BACKOFF_TIME,
                ex,
            )
            await self._execute_disconnect()
            raise
        except BleakError as ex:
            # Disconnect so we can reset state and try again
            _LOGGER.debug(
                "%s: RSSI: %s; Disconnecting due to error: %s", self.name, self.rssi, ex
            )
            await self._execute_disconnect()
            raise

    async def _send_command(
        self, command: CctSmartBulbCommandInstance | str | bytes
    ) -> None:
        """Send command to device and read response."""
        await self._ensure_connected()
        self._last_command = None
        if isinstance(command, CctSmartBulbCommandInstance):
            self._last_command = command
            _command_bytes = command.request_bytes
            if _command_bytes is None:
                raise ValueError("Cannot send command without request bytes")
        elif isinstance(command, str):
            _command_bytes = bytes.fromhex(command.replace(":", ""))
        else:
            _command_bytes = command
        await self._send_command_while_connected(_command_bytes)

    async def _send_command_while_connected(self, command: bytes) -> None:
        """Send command to device and read response."""
        _LOGGER.debug(
            "%s: Sending command %s",
            self.name,
            command.hex(sep=":"),
        )
        if self._operation_lock.locked():
            _LOGGER.debug(
                "%s: Operation already in progress, waiting for it to complete; RSSI: %s",
                self.name,
                self.rssi,
            )
        async with self._operation_lock:
            try:
                await self._send_command_locked(command)
                return
            except BleakNotFoundError:
                _LOGGER.error(
                    "%s: device not found, no longer in range, or poor RSSI: %s",
                    self.name,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except CharacteristicMissingError as ex:
                _LOGGER.debug(
                    "%s: characteristic missing: %s; RSSI: %s",
                    self.name,
                    ex,
                    self.rssi,
                    exc_info=True,
                )
                raise
            except BLEAK_EXCEPTIONS:
                _LOGGER.debug("%s: communication failed", self.name, exc_info=True)
                raise

    async def _execute_command_locked(self, command: bytes) -> None:
        """Execute command and read response."""
        assert self._client is not None  # nosec
        if not self._read_char:
            raise CharacteristicMissingError("Read characteristic missing")
        if not self._write_char:
            raise CharacteristicMissingError("Write characteristic missing")
        await self._client.write_gatt_char(
            self._write_char, command, response=WRITE_WITH_RESPONSE
        )

    def _resolve_characteristics(self, services: BleakGATTServiceCollection):
        """Resolve characteristics."""
        if char := services.get_characteristic(READ_CHAR_UUID):
            self._read_char = char
        else:
            raise CharacteristicMissingError("Read characteristic missing")

        if char := services.get_characteristic(WRITE_CHAR_UUID):
            self._write_char = char
        else:
            raise CharacteristicMissingError("Write characteristic missing")
