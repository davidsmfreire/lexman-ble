import asyncio
import logging

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from lexman_ble import LexmanCCTSmartBulb, LexmanCCTSmartBulbState

_LOGGER = logging.getLogger(__name__)

ADDRESS = "dc:8e:95:e6:86:ee"
# ADDRESS = "F0:82:C0:8C:BD:02"


async def run() -> None:
    future: asyncio.Future[tuple[BLEDevice, AdvertisementData]] = asyncio.Future()

    def on_detected(device: BLEDevice, adv: AdvertisementData) -> None:
        if future.done():
            return
        _LOGGER.info("Detected: %s", device)
        if device.address.lower() == ADDRESS.lower():
            _LOGGER.info("Found device: %s", device.address)
            future.set_result((device, adv))

    scanner = BleakScanner(on_detected)
    await scanner.start()

    _LOGGER.info("Scanning...")

    def on_state_changed(state: LexmanCCTSmartBulbState) -> None:
        _LOGGER.info("State changed: %s", state)

    device, adv = await future
    led = LexmanCCTSmartBulb(device, adv)
    cancel_callback = led.register_callback(on_state_changed)

    await led.update()
    await asyncio.sleep(2)

    await led.turn_on()
    await asyncio.sleep(2)

    await led.set_brightness(50)
    await asyncio.sleep(2)

    await led.set_temperature(2700)
    await asyncio.sleep(2)

    await led.turn_off()
    await asyncio.sleep(2)

    cancel_callback()
    await scanner.stop()


logging.basicConfig(level=logging.INFO)
logging.getLogger("lexman_ble").setLevel(logging.DEBUG)
asyncio.run(run())
