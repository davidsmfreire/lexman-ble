# LexmanBLE

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

Python package and Home assistant custom component for controlling [Lexman (Leroy Merlin brand) CCT smart bulbs](https://www.leroymerlin.fr/produits/decoration-eclairage/ampoule-et-led/ampoule-led/ampoule-e27/ampoule-led-connectee-e27-806lm-60w-variations-blanc-couleurs-lexman-enki-84372272.html) over bluetooth.

Pip package installation:

```shell
pip install lexman-ble
```

Home assistant installation through [HACS](https://www.hacs.xyz/):

HACS > Menu > Custom repositories > Paste `https://github.com/davidsmfreire/lexman-ble` and select Type "Integration"

Then search for LexmanBLE and download.

**The custom component will set up the following platforms.**

| Platform | Description          |
| -------- | -------------------- |
| `light`  | Control a smart bulb |

![logo][lexmanimg]

## Home assistant manual custom_components installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `lexman_ble`.
4. Download _all_ the files from the `custom_components/lexman_ble/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "LexmanBLE"

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

The lexman_ble library implementation was inspired in [@Bluetooth-Devices](https://github.com/Bluetooth-Devices)'s [led_ble](https://github.com/Bluetooth-Devices/led-ble) project.

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/davidsmfreire
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/davidsmfreire/lexman-ble.svg?style=for-the-badge
[commits]: https://github.com/davidsmfreire/lexman-ble/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[lexmanimg]: images/logo.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/davidsmfreire/lexman-ble.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40davidsmfreire-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/davidsmfreire/lexman-ble.svg?style=for-the-badge
[releases]: https://github.com/davidsmfreire/lexman-ble/releases
[user_profile]: https://github.com/davidsmfreire
