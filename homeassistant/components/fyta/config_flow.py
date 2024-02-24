"""Config flow for FYTA integration."""
from __future__ import annotations

import logging
from typing import Any

from fyta_cli.fyta_connector import FytaConnector
from fyta_cli.fyta_exceptions import (
    FytaAuthentificationError,
    FytaConnectionError,
    FytaPasswordError,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)


class FytaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fyta."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors = {}
        if user_input:
            fyta = FytaConnector(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])

            try:
                await fyta.login()
                await fyta.client.close()
            except FytaConnectionError:
                errors["base"] = "cannot_connect"
            except FytaAuthentificationError:
                errors["base"] = "auth_error"
            except FytaPasswordError:
                errors["base"] = "auth_error"
                errors[CONF_PASSWORD] = "password_error"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
            else:
                self._async_abort_entries_match()

                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
