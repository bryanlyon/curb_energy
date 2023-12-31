import logging
import requests
import json
from datetime import datetime, timedelta
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.util import Throttle
from homeassistant.components.sensor import PLATFORM_SCHEMA

_LOGGER = logging.getLogger(__name__)

DOMAIN = "curb_energy"
SCAN_INTERVAL = timedelta(minutes=5)  # Update data every 15 minutes

RANGE = '5m'
RESOLUTION = '5m'

BASE_URL = "https://app.energycurb.com/api/v3"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required('username'): cv.string,
    vol.Required('password'): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    if not config:
        # This might be an empty configuration call, so we'll return early
        return
    username = config['username']
    password = config['password']

    curb_api = CurbAPI(username, password)

    if not curb_api.authenticate():
        _LOGGER.error("Unable to authenticate with Curb API")
        return False
    
    curb_api.get_circuits()
    sensors = []
    for circuit in curb_api.circuits:
        try:
            entity_id = f"{DOMAIN}.{circuit['label'].lower().replace(' ', '_').replace('/','_')}"
            _LOGGER.debug(f"Adding sensor {entity_id}")
            sensors.append(
                CurbEnergySensor(entity_id, circuit["label"], curb_api)
            )
        except:
            _LOGGER.error(f"Failed to add sensor {circuit}")

    _LOGGER.debug(f"Adding {len(sensors)} sensors")

    add_entities(sensors, update_before_add=True)
    hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)

    return True


class CurbAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.access_token = None
        self.token_expiration = None
        self.circuits = []

    def authenticate(self):
        auth_data = {
            "grant_type": "password",
            "audience": "app.energycurb.com/api",
            "username": self.username,
            "password": self.password,
            "client_id": "iKAoRkr3qyFSnJSr3bodZRZZ6Hm3GqC3",
            "client_secret": "dSoqbfwujF72a1DhwmjnqP4VAiBTqFt3WLLUtnpGDmCf6_CMQms3WEy8DxCQR3KY",
        }

        try:
            response = requests.post(
                "https://energycurb.auth0.com/oauth/token",
                headers={"Content-Type": "application/json"},
                data=json.dumps(auth_data),
                timeout=8
            )
        except TimeoutError as e:
            _LOGGER.error(f"Timeout error authenticating with Curb API: {e}")
            return False

        if response.status_code == 200:
            auth_data = response.json()
            self.access_token = auth_data["access_token"]
            self.token_expiration = datetime.now() + timedelta(
                seconds=int(auth_data["expires_in"]*.8)
            )
            self.get_circuits()  # Retrieve circuit data
            return True

        return False
    
    @Throttle(SCAN_INTERVAL)
    def get_circuits(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        locationResponse = requests.get(f"{BASE_URL}/locations", headers=headers, timeout=8)
        for location in locationResponse.json():
            # response = requests.get(f"{BASE_URL}/latest/{location['id']}", headers=headers, timeout=8)
            response = requests.get(f"{BASE_URL}/aggregate/{location['id']}/{RANGE}/{RESOLUTION}", headers=headers, timeout=8)
        if response.status_code == 200:
            self.circuits = response.json()
        else:
            self.circuits = []

        if len(self.circuits) > 0:
            _LOGGER.debug(f"Retrieved {len(self.circuits)} circuits")
        else:
            _LOGGER.error("No circuits found")


class CurbEnergySensor(Entity):
    def __init__(self, entity_id, circuit_label, curb_api):
        self.entity_id = entity_id
        self._name = f"Curb Energy {circuit_label}"
        self._state = None
        self._unit_of_measurement = "W"
        self.circuit_label = circuit_label
        self.curb_api = curb_api

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @Throttle(SCAN_INTERVAL)
    def update(self):
        self.curb_api.get_circuits()
        if self.curb_api.token_expiration < datetime.now():
            # If the token is expired, re-authenticate
            if not self.curb_api.authenticate():
                return
        for circuit in self.curb_api.circuits:
            if circuit["label"] == self.circuit_label:
                self._state = int(circuit['avg'])
                _LOGGER.debug(f"Updating {self.entity_id} to {self._state}")
