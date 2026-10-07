"""Tests for AWS IoT refrigerator support."""

from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from tests.awsiot.mocks import (
    FakeMqttClient,
    make_mqtt_factory,
    mock_aws_http_api,
    patch_aws_manager_mqtt,
)
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.refrigerator import Refrigerator
from whirlpool.backendselector import BackendSelector

REFRIGERATOR_SAID = "WPR1R00000001"
REFRIGERATOR_MODEL = "WRFC7036RZ00"
REFRIGERATOR_CAP_PART = "W10000001"

REFRIGERATOR_THING: dict[str, Any] = {
    "thingName": REFRIGERATOR_SAID,
    "thingTypeName": REFRIGERATOR_MODEL,
    "attributes": {
        "Name": "5465737420526566726967657261746f72",  # Test Refrigerator
        "Category": "REFRIGERATION",
        "Serial": "TESTSERIAL",
        "CapabilityPartNumber": REFRIGERATOR_CAP_PART,
    },
}

REFRIGERATOR_CAPABILITY: dict[str, Any] = {
    "partNumber": REFRIGERATOR_CAP_PART,
}

REFRIGERATOR_STATE: dict[str, Any] = {
    "refrigerator": {
        "temperatureControl": {"setpoint": 2.8},
        "doors": {"left": "close", "right": "close"},
        "maxCool": {"time": 0},
        "vacation": False,
        "powerOutageAlarm": {"state": "idle"},
    },
    "freezer": {
        "temperatureControl": {"setpoint": -17.8},
        "doors": {"single": "close"},
        "iceMaker": True,
        "maxIce": {"time": 0},
        "powerOutageAlarm": {"state": "idle"},
    },
    "pantry": {
        "temperatureControl": {"setpoint": 5},
        "doors": {"single": "close"},
    },
    "icebox": {
        "iceMaker": True,
    },
    "hmiControlLockout": False,
    "sabbathMode": False,
    "quietMode": False,
    "waterFilter": {
        "overdue": False,
        "stage": 0,
    },
    "iceTypeSelection": "cubed",
    "doorAlarm": "idle",
}


@pytest_asyncio.fixture
async def aws_refrigerator_manager(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> AsyncGenerator[tuple[AwsAppliancesManager, FakeMqttClient]]:
    """Return an AWS manager containing one refrigerator."""
    holder: dict[str, FakeMqttClient] = {}
    mqtt_factory = make_mqtt_factory(
        REFRIGERATOR_STATE,
        {REFRIGERATOR_CAP_PART: REFRIGERATOR_CAPABILITY},
        holder,
    )
    mock_aws_http_api(
        aiointercept_mock,
        backend_selector,
        [REFRIGERATOR_THING],
    )

    with patch_aws_manager_mqtt(mqtt_factory):
        manager = AwsAppliancesManager(
            auth,
            client_session_fixture,
            lambda: None,
        )
        assert await manager.connect() is True
        yield manager, holder["client"]


async def test_refrigeration_category_registers_refrigerator(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_refrigerator_manager

    assert len(manager.refrigerators) == 1
    refrigerator = manager.refrigerators[0]
    assert isinstance(refrigerator, Refrigerator)
    assert refrigerator.said == REFRIGERATOR_SAID
    assert refrigerator.name == "Test Refrigerator"


async def test_initial_state_populates_read_only_getters(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]

    assert refrigerator.get_refrigerator_setpoint() == 2.8
    assert refrigerator.get_freezer_setpoint() == -17.8
    assert refrigerator.get_pantry_setpoint() == 5.0
    assert refrigerator.get_pantry_mode() == "wine"

    assert refrigerator.get_refrigerator_left_door_open() is False
    assert refrigerator.get_refrigerator_right_door_open() is False
    assert refrigerator.get_freezer_door_open() is False
    assert refrigerator.get_pantry_door_open() is False

    assert refrigerator.get_freezer_ice_maker() is True
    assert refrigerator.get_icebox_ice_maker() is True
    assert refrigerator.get_max_cool() is False
    assert refrigerator.get_max_ice() is False
    assert refrigerator.get_vacation_mode() is False
    assert refrigerator.get_control_lock() is False
    assert refrigerator.get_sabbath_mode() is False
    assert refrigerator.get_quiet_mode() is False

    assert refrigerator.get_water_filter_overdue() is False
    assert refrigerator.get_water_filter_stage() == 0
    assert refrigerator.get_ice_type() == "cubed"
    assert refrigerator.get_door_alarm() == "idle"
    assert refrigerator.get_refrigerator_power_outage_alarm() == "idle"
    assert refrigerator.get_freezer_power_outage_alarm() == "idle"


@pytest.mark.parametrize(
    ("setpoint", "expected"),
    (
        (-1, "meat"),
        (1, "drink"),
        (3, "deli"),
        (5, "wine"),
        (2, None),
    ),
)
async def test_pantry_mode_mapping(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
    setpoint: int,
    expected: str | None,
) -> None:
    manager, _ = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]

    refrigerator.update_state(
        {"pantry": {"temperatureControl": {"setpoint": setpoint}}}
    )

    assert refrigerator.get_pantry_mode() == expected


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        ("open", True),
        ("close", False),
        ("unknown", None),
    ),
)
async def test_door_state_mapping(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
    state: str,
    expected: bool | None,
) -> None:
    manager, _ = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]

    refrigerator.update_state(
        {
            "refrigerator": {
                "doors": {
                    "left": state,
                    "right": state,
                }
            },
            "freezer": {"doors": {"single": state}},
            "pantry": {"doors": {"single": state}},
        }
    )

    assert refrigerator.get_refrigerator_left_door_open() is expected
    assert refrigerator.get_refrigerator_right_door_open() is expected
    assert refrigerator.get_freezer_door_open() is expected
    assert refrigerator.get_pantry_door_open() is expected


async def test_partial_mqtt_update_is_merged_and_fires_callback(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, mqtt = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]
    calls: list[int] = []
    refrigerator.register_attr_callback(lambda: calls.append(1))

    mqtt.inject(
        f"dt/{REFRIGERATOR_MODEL}/{REFRIGERATOR_SAID}/state/update",
        {"refrigerator": {"doors": {"left": "open"}}},
    )

    assert refrigerator.get_refrigerator_left_door_open() is True
    assert refrigerator.get_refrigerator_right_door_open() is False
    assert refrigerator.get_refrigerator_setpoint() == 2.8
    assert calls == [1]


async def test_max_cool_and_max_ice_active_when_time_remaining(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]

    refrigerator.update_state(
        {
            "refrigerator": {"maxCool": {"time": 600}},
            "freezer": {"maxIce": {"time": 1200}},
        }
    )

    assert refrigerator.get_max_cool() is True
    assert refrigerator.get_max_ice() is True


async def test_missing_fields_return_none(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]

    refrigerator._data_dict = {}

    assert refrigerator.get_refrigerator_setpoint() is None
    assert refrigerator.get_freezer_setpoint() is None
    assert refrigerator.get_pantry_setpoint() is None
    assert refrigerator.get_pantry_mode() is None
    assert refrigerator.get_refrigerator_left_door_open() is None
    assert refrigerator.get_refrigerator_right_door_open() is None
    assert refrigerator.get_freezer_door_open() is None
    assert refrigerator.get_pantry_door_open() is None
    assert refrigerator.get_freezer_ice_maker() is None
    assert refrigerator.get_icebox_ice_maker() is None
    assert refrigerator.get_max_cool() is None
    assert refrigerator.get_max_ice() is None
    assert refrigerator.get_vacation_mode() is None
    assert refrigerator.get_control_lock() is None
    assert refrigerator.get_sabbath_mode() is None
    assert refrigerator.get_quiet_mode() is None
    assert refrigerator.get_water_filter_overdue() is None
    assert refrigerator.get_water_filter_stage() is None
    assert refrigerator.get_ice_type() is None
    assert refrigerator.get_door_alarm() is None
    assert refrigerator.get_refrigerator_power_outage_alarm() is None
    assert refrigerator.get_freezer_power_outage_alarm() is None


async def test_aws_refrigerator_setters_are_not_implemented(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, mqtt = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]
    published_before = len(mqtt.published)

    with pytest.raises(NotImplementedError):
        await refrigerator.set_offset_temp(0)
    with pytest.raises(NotImplementedError):
        await refrigerator.set_temp(10)
    with pytest.raises(NotImplementedError):
        await refrigerator.set_turbo_mode(True)
    with pytest.raises(NotImplementedError):
        await refrigerator.set_display_lock(True)

    # The failed setters must not publish any command.
    assert len(mqtt.published) == published_before


async def test_subscribes_to_expected_topics(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    _, mqtt = aws_refrigerator_manager
    cid = mqtt.client_id

    assert {
        f"cmd/{REFRIGERATOR_MODEL}/{REFRIGERATOR_SAID}/response/{cid}",
        f"dt/{REFRIGERATOR_MODEL}/{REFRIGERATOR_SAID}/state/update",
        f"$aws/events/presence/connected/{REFRIGERATOR_SAID}",
        f"$aws/events/presence/disconnected/{REFRIGERATOR_SAID}",
    }.issubset(mqtt.subscribed_topics)


async def test_set_vacation_mode_publishes_command(
    aws_refrigerator_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, mqtt = aws_refrigerator_manager
    refrigerator = manager.refrigerators[0]

    await refrigerator.set_vacation_mode(True)
    _, message = mqtt.published[-1]

    assert message["payload"] == {
        "addressee": "refrigerator",
        "command": "set",
        "vacation": True,
    }

    await refrigerator.set_vacation_mode(False)
    _, message = mqtt.published[-1]

    assert message["payload"] == {
        "addressee": "refrigerator",
        "command": "set",
        "vacation": False,
    }
