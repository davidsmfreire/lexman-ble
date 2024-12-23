from copy import deepcopy
from enum import Enum
from typing import cast
import warnings
import parse

READ_CHAR_UUID: str = "0000a102-1115-1000-0001-617573746f6d"
WRITE_CHAR_UUID: str = "0000a101-1115-1000-0001-617573746f6d"


def _hex_string_formatting(string: str, value: int):
    values: list[str] = []
    _value = deepcopy(value)
    for i in range(8):
        if f"{{{i}}}" in string:
            values.append(format(_value & 0xFF, "02x"))
            _value = _value >> 8
    return string.format(*values)


def _hex_string_parsing(string: str, template: str) -> int:
    result = parse.parse(template, string, evaluate_result=True)
    if result is None:
        raise ValueError("Could not parse string")
    result = cast(parse.Result, result)

    fmt_indices = []
    for i in range(8):
        if f"{{{i}}}" in template:
            loc = template.find(f"{{{i}}}")
            fmt_indices.append((i, template.count(f"{{{i}}}"), loc))

    fmt_indices = sorted(fmt_indices, key=lambda x: x[2])

    value: int = 0
    for i, (fmt_index, _count, _) in enumerate(fmt_indices):
        _val = int(result.fixed[i], 16)
        for _ in range(_count):
            _cmp = int(result.fixed[i + len(fmt_indices)], 16)
            if _val != _cmp:
                raise ValueError(
                    f"Mismatch between same format placeholders: {i} {{{fmt_index}}}={_val} {{{i+len(fmt_indices)}}}={_cmp}"
                )
        value += _val << fmt_index * 8
    return value


CCT_TEMPERATURE_MIN = 153  # cooler
CCT_TEMPERATURE_MAX = 454  # warmer

CCT_TEMPERATURE_REAL_MIN = 6500  # k  # cooler
CCT_TEMPERATURE_REAL_MAX = 2700  # k  # warmer


class CctSmartBulbCommand(Enum):
    # fmt: off
    # set, query, response
    PING        = ( None                          , "00:00:20:01:02:00:02", "00:00:20:03:02:00:02"           )
    SWITCH      = ( "00:00:10:01:03:{0}:00:00"    , "00:00:10:02"         , "00:00:10:03:02:{0}:{0}"         )
    BRIGHTNESS  = ( "00:00:11:01:03:{0}:00:00"    , "00:00:11:02"         , "00:00:11:03:02:{0}:{0}"         )
    TEMPERATURE = ( "00:00:12:01:04:{1}:{0}:00:00", "00:00:12:02"         , "00:00:12:03:04:{1}:{0}:{1}:{0}" )
    # fmt: on

    def __init__(
        self, set_cmd: str | None, query_cmd: str | None, response_template: str | None
    ):
        self.set_cmd = set_cmd
        self.query_cmd = query_cmd
        self.response_template = response_template

    def instance(self) -> "CctSmartBulbCommandInstance":
        return CctSmartBulbCommandInstance(self)

    @property
    def query(self) -> "CctSmartBulbCommandInstance":
        return self.instance().query

    def set(self, value: int | None = None) -> "CctSmartBulbCommandInstance":
        return self.instance().set(value)


class CctSmartBulbCommandInstance:
    def __init__(self, command: CctSmartBulbCommand):
        self.type: CctSmartBulbCommand = command
        self._value: int | None = None
        self._request: str | None = None

    @property
    def name(self) -> str:
        return self.type.name

    @property
    def value_set(self) -> int | None:
        return self._value

    def set(self, value: int | None = None) -> "CctSmartBulbCommandInstance":
        if self.type.set_cmd is None:
            raise ValueError(f"{self.type.name} doesn't have a set command")

        self._value = value
        if value is not None:
            self._request = _hex_string_formatting(self.type.set_cmd, value)
        else:
            self._request = self.type.set_cmd

        if self._request and "{" in self._request:
            raise ValueError(f"This request requires a value: {self.type.name}")
        return self

    @property
    def is_set(self) -> bool:
        return self._value is not None

    @property
    def query(self) -> "CctSmartBulbCommandInstance":
        self._value = None
        self._request = self.type.query_cmd
        return self

    def match_response(self, _response: str) -> tuple[bool, int | None]:
        template = self.type.response_template

        if template is None:
            return False, None

        if self._value is not None:
            expected_response = _hex_string_formatting(template, self._value)
            if _response == expected_response:
                return True, self._value
            warnings.warn(f"Expected: {expected_response}, got: {_response}")
            return False, None

        if "{" in template:
            try:
                value = _hex_string_parsing(_response, template)
                return True, value
            except Exception:
                return False, None

        return template == _response, None

    @property
    def request(self) -> str | None:
        return self._request

    @property
    def request_bytes(self) -> bytes | None:
        if self._request is None:
            return None
        return bytes.fromhex(self._request.replace(":", ""))
