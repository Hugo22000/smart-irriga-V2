"""Constants for Smart Irrigation V2."""

# Domain
DOMAIN = "smart_irriga_v2"

# Platforms
PLATFORMS = ["sensor", "button", "switch"]

# Configuration keys
CONF_ZONE_NAME = "zone_name"
CONF_NUM_PUMPS = "num_pumps"
CONF_PUMPS = "pumps"
CONF_PUMP_SWITCH = "switch"
CONF_PUMP_FLOW_RATE = "flow_rate"
CONF_PUMP_HUMIDITY_SENSOR = "pump_humidity_sensor"

# Default values
DEFAULT_ZONE_NAME = "My Irrigation Zone"
DEFAULT_NUM_PUMPS = 1
MIN_FLOW_RATE = 5  # cL/min
MAX_FLOW_RATE = 300  # cL/min
DEFAULT_FLOW_RATE = 100  # cL/min

# Activation modes
CONF_ACTIVATION_MODE = "activation_mode"
CONF_IRRIGATION_DURATION = "irrigation_duration"
CONF_SCHEDULE_TIME = "schedule_time"
CONF_SCHEDULE_DAYS = "schedule_days"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_HUMIDITY_THRESHOLD = "humidity_threshold"

MODE_MANUAL = "manual"
MODE_SCHEDULE = "schedule"
MODE_HUMIDITY = "humidity"

DEFAULT_IRRIGATION_DURATION = 300  # seconds
DEFAULT_HUMIDITY_THRESHOLD = 40  # %

# Entity IDs
SENSOR_WATER_VOLUME = "water_volume"
SENSOR_NEXT_IRRIGATION = "next_irrigation"
BUTTON_START_IRRIGATION = "start_irrigation"
BUTTON_STOP_IRRIGATION = "stop_irrigation"

# Zone state
CONF_ZONE_ACTIVE = "zone_active"

# Services
SERVICE_SET_ZONE_OPTIONS = "set_zone_options"
