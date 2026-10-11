"""Constants for the Fox ESS Cloud integration."""
import logging

DOMAIN = "foxess_cloud"
LOGGER = logging.getLogger(__package__)

BASE_URL = "https://www.foxesscloud.com"

# Config keys
CONF_API_KEY = "api_key"
CONF_DEVICE_SN = "device_sn"
CONF_DEVICE_ID = "device_id"

# Options
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 5  # minutes

# API endpoints
ENDPOINT_DEVICE_LIST = "/op/v0/device/list"
ENDPOINT_DEVICE_DETAIL = "/op/v0/device/detail"
ENDPOINT_REAL_QUERY = "/op/v0/device/real/query"
ENDPOINT_REPORT_QUERY = "/op/v0/device/report/query"
ENDPOINT_GENERATION = "/op/v0/device/generation"
ENDPOINT_BATTERY_SOC_GET = "/op/v0/device/battery/soc/get"
ENDPOINT_BATTERY_SOC_SET = "/op/v0/device/battery/soc/set"
ENDPOINT_SETTING_GET = "/op/v0/device/setting/get"
ENDPOINT_SETTING_SET = "/op/v0/device/setting/set"
ENDPOINT_SCHEDULER_GET = "/op/v3/device/scheduler/get"
ENDPOINT_SCHEDULER_ENABLE = "/op/v3/device/scheduler/enable"
ENDPOINT_SCHEDULER_FLAG_GET = "/op/v1/device/scheduler/get/flag"
ENDPOINT_SCHEDULER_FLAG_SET = "/op/v1/device/scheduler/set/flag"

# Explicit variable lists for API calls
REALTIME_VARIABLES = [
    "pvPower", "pv1Power", "pv1Volt", "pv1Current",
    "pv2Power", "pv2Volt", "pv2Current",
    "pv3Power", "pv3Volt", "pv3Current",
    "pv4Power", "pv4Volt", "pv4Current",
    "generationPower", "gridConsumptionPower", "feedinPower", "loadsPower",
    "batChargePower", "batDischargePower", "SoC", "SoH",
    "batTemperature", "ResidualEnergy", "invBatPower",
    "RVolt", "RCurrent", "RPower", "RFreq",
    "SVolt", "SCurrent", "SPower", "SFreq",
    "TVolt", "TCurrent", "TPower", "TFreq",
    "ambientTemperation", "boostTemperation", "invTemperation",
    "runningState", "PowerFactor", "ReactivePower", "meterPower2",
]

REPORT_VARIABLES = [
    "generation", "feedin", "gridConsumption",
    "chargeEnergyToTal", "dischargeEnergyToTal", "loads",
]

# Work modes
WORK_MODES = ["SelfUse", "Backup", "Feedin", "PeakShaving"]

# Mode Scheduler (Open API v3)
SCHEDULER_WORK_MODES = ["SelfUse", "Feedin", "Backup", "ForceCharge", "ForceDischarge"]
# Service field -> Open API extraParam key. Keys are only sent if the inverter
# advertises them in the v3 scheduler "properties" (matched case-insensitively).
SCHEDULER_EXTRA_PARAMS = {
    "min_soc_on_grid": "minSocOnGrid",
    "max_soc": "maxSoc",
    "fd_soc": "fdSoc",
    "fd_pwr": "fdPwr",
    "import_limit": "importLimit",
    "export_limit": "exportLimit",
    "pv_limit": "pvLimit",
}
DEFAULT_MAX_GROUPS = 8

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_GET_SCHEDULE = "get_schedule"

# Running states
RUNNING_STATES = {
    160: "Self Test",
    161: "Waiting",
    162: "Checking",
    163: "On Grid",
    164: "Off Grid",
    165: "Fault",
    166: "Permanent Fault",
    167: "Standby",
    168: "Upgrading",
    169: "FCT",
    170: "Illegal",
}
