from typing import override

from ..refrigerator import Refrigerator as BaseRefrigerator
from ..types import ApplianceInfo
from .appliance import Appliance
from .mqttclient import MqttClient


class Refrigerator(BaseRefrigerator, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
    ):
        super().__init__(mqttclient, appliance_info)

    @override
    def get_offset_temp(self) -> int | None:
        raise NotImplementedError()

    @override
    async def set_offset_temp(self, temp) -> bool:
        raise NotImplementedError()

    @override
    def get_temp(self) -> int | None:
        raise NotImplementedError()

    @override
    async def set_temp(self, temp: int) -> bool:
        raise NotImplementedError()

    @override
    def get_turbo_mode(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_turbo_mode(self, turbo: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_display_lock(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_display_lock(self, display: bool) -> bool:
        raise NotImplementedError()

    def get_refrigerator_setpoint(self) -> float | None:
        return self._get_path_float("refrigerator", "temperatureControl", "setpoint")

    def get_freezer_setpoint(self) -> float | None:
        return self._get_path_float("freezer", "temperatureControl", "setpoint")

    def get_pantry_setpoint(self) -> float | None:
        return self._get_path_float("pantry", "temperatureControl", "setpoint")

    def get_pantry_mode(self) -> str | None:
        setpoint = self.get_pantry_setpoint()
        if setpoint is None:
            return None
        return {
            -1.0: "meat",
            1.0: "drink",
            3.0: "deli",
            5.0: "wine",
        }.get(setpoint)

    def get_refrigerator_left_door_open(self) -> bool | None:
        state = self._get_path_str("refrigerator", "doors", "left")
        if state == "open":
            return True
        if state == "close":
            return False
        return None

    def get_refrigerator_right_door_open(self) -> bool | None:
        state = self._get_path_str("refrigerator", "doors", "right")
        if state == "open":
            return True
        if state == "close":
            return False
        return None

    def get_freezer_door_open(self) -> bool | None:
        state = self._get_path_str("freezer", "doors", "single")
        if state == "open":
            return True
        if state == "close":
            return False
        return None

    def get_pantry_door_open(self) -> bool | None:
        state = self._get_path_str("pantry", "doors", "single")
        if state == "open":
            return True
        if state == "close":
            return False
        return None

    def get_freezer_ice_maker(self) -> bool | None:
        return self._get_path_bool("freezer", "iceMaker")

    def get_icebox_ice_maker(self) -> bool | None:
        return self._get_path_bool("icebox", "iceMaker")

    def get_max_cool(self) -> bool | None:
        value = self._get_path_int("refrigerator", "maxCool", "time")
        if value is None:
            return None
        return value > 0

    def get_max_ice(self) -> bool | None:
        value = self._get_path_int("freezer", "maxIce", "time")
        if value is None:
            return None
        return value > 0

    def get_vacation_mode(self) -> bool | None:
        return self._get_path_bool("refrigerator", "vacation")

    async def set_vacation_mode(self, enabled: bool) -> None:
        await self._send_command(
            "set",
            {"addressee": "refrigerator", "vacation": enabled},
        )

    def get_control_lock(self) -> bool | None:
        return self._get_path_bool("hmiControlLockout")

    def get_sabbath_mode(self) -> bool | None:
        return self._get_path_bool("sabbathMode")

    def get_quiet_mode(self) -> bool | None:
        return self._get_path_bool("quietMode")

    def get_water_filter_overdue(self) -> bool | None:
        return self._get_path_bool("waterFilter", "overdue")

    def get_water_filter_stage(self) -> int | None:
        return self._get_path_int("waterFilter", "stage")

    def get_ice_type(self) -> str | None:
        return self._get_path_str("iceTypeSelection")

    def get_door_alarm(self) -> str | None:
        return self._get_path_str("doorAlarm")

    def get_refrigerator_power_outage_alarm(self) -> str | None:
        return self._get_path_str("refrigerator", "powerOutageAlarm", "state")

    def get_freezer_power_outage_alarm(self) -> str | None:
        return self._get_path_str("freezer", "powerOutageAlarm", "state")
