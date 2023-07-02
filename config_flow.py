import logging
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_IP_ADDRESS
import voluptuous as vol
from .const import DOMAIN
from maxsmart import MaxSmartDiscovery

_LOGGER = logging.getLogger(__name__)


class MaxSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    VERSION = 1


    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is None:
            _LOGGER.info("Starting user-initiated device discovery without IP.")
            devices = await self.hass.async_add_executor_job(
                MaxSmartDiscovery.discover_maxsmart
            )
            _LOGGER.info(f"Discovered devices without IP: {devices}")
        else:
            _LOGGER.info("Starting user-initiated device discovery with IP.")
            devices = await self.hass.async_add_executor_job(
                MaxSmartDiscovery.discover_maxsmart, user_input[CONF_IP_ADDRESS]
            )
            _LOGGER.info(f"Discovered devices with IP: {devices}")

        if devices:
            _LOGGER.info("Devices have been found. Attempting to create entries")
            for device in devices:
                await self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data=device
                )
            return self.async_abort(reason="devices_found")
        else:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required(CONF_IP_ADDRESS): str}),
                errors={"base": "no_devices_found"},
            )

    _LOGGER.info("Finished step user")

    async def async_step_import(self, device):
        """Create entry for a device"""
        try:
            pname = device.get("pname")
            # sw_version = device.get("ver")
            port_data = {}

            if pname is None:
                port_data = {
                    "master": {"port_id": 0, "port_name": "0. Master"},
                    "individual_ports": [
                        {"port_id": 1, "port_name": "1. Port"}
                    ],
                }
            else:
                port_data = {
                    "master": {"port_id": 0, "port_name": "0. Master"},
                    "individual_ports": [
                        {"port_id": i + 1, "port_name": f"{i + 1}. {port_name}"}
                        for i, port_name in enumerate(pname)
                    ],
                }

            device_data = {
                "device_unique_id": device["sn"],
                "device_ip": device["ip"],
                "device_name": f"MaxSmart {device['name']}",
                "sw_version": device["ver"],
                "ports": port_data,
            }

            await self.async_set_unique_id(device["sn"])

            current_entries = self._async_current_entries()
            existing_entry = next((entry for entry in current_entries if entry.unique_id == device["sn"]), None)

            if existing_entry:
                _LOGGER.info("Device %s with name %s is already configured", device["sn"], device["name"])
                if existing_entry.data != device_data:
                    _LOGGER.info("Updating config entry for device %s", device["sn"])
                    self.hass.config_entries.async_update_entry(existing_entry, data=device_data)
                return self.async_abort(reason="Device already configured")

            return self.async_create_entry(
                title=f"maxsmart_{device['sn']}",
                data=device_data,
            )

        except Exception as err:
            _LOGGER.error("Failed to create device entry: %s", err)

