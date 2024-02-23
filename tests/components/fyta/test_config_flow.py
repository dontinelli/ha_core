"""Test the fyta config flow."""
from collections.abc import Generator
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fyta_cli.fyta_exceptions import (
    FytaAuthentificationError,
    FytaConnectionError,
    FytaPasswordError,
)
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.fyta import config_flow
from homeassistant.components.fyta.const import DOMAIN
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

USERNAME = "fyta_user"
PASSWORD = "fyta_pass"
ACCESS_TOKEN = "123xyz"
EXPIRATION = datetime.now()


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.fyta.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ), patch(
        "homeassistant.components.fyta.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == USERNAME
    assert result2["data"] == {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    assert len(mock_setup_entry.mock_calls) == 1


def init_config_flow(hass: HomeAssistant):
    """Init a configuration flow."""
    flow = config_flow.FytaConfigFlow()
    flow.hass = hass
    return flow


async def test_user(hass: HomeAssistant) -> None:
    """Test user config."""
    flow = init_config_flow(hass)

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # tests with connection error
    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ) as mock:
        fyta = mock.return_value
        fyta.login.side_effect = FytaConnectionError

        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}

    # tests with authentication error
    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ) as mock:
        fyta = mock.return_value
        fyta.login.side_effect = FytaAuthentificationError

        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}

    # tests with password error
    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ) as mock:
        fyta = mock.return_value
        fyta.login.side_effect = FytaPasswordError

        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth", CONF_PASSWORD: "password_error"}

    # tests with other error
    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ) as mock:
        fyta = mock.return_value
        fyta.login.side_effect = Exception

        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}

    # tests with all information provided
    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ) as mock:
        fyta = mock.return_value
        fyta.login.return_value = {
            "access_token": ACCESS_TOKEN,
            "expiration": EXPIRATION,
        }

        result = await flow.async_step_user(
            {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["data"][CONF_USERNAME] == USERNAME
    assert result["data"][CONF_PASSWORD] == PASSWORD


async def test_validate_input(hass: HomeAssistant) -> None:
    """Test validate_input."""
    flow = init_config_flow(hass)

    with patch(
        "homeassistant.components.fyta.config_flow.FytaConnector",
        return_value=AsyncMock(),
    ) as mock:
        fyta = mock.return_value
        fyta.login.return_value = {
            "access_token": ACCESS_TOKEN,
            "expiration": EXPIRATION,
        }

        result = await flow.validate_input(
            hass, {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
        )

    assert result["title"] == USERNAME
