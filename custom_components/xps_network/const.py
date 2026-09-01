DOMAIN = "xps_network"

BASE_URL = "https://www4.xpsnetwork.com"
GRAPHQL_URL = f"{BASE_URL}/xpsweb"

APP_NAME = "xpsweb"
APP_VERSION = "1.0.0"

DEFAULT_SCAN_INTERVAL_MINUTES = 15
SCHEDULE_LOOKAHEAD_DAYS = 30
SCHEDULE_LOOKBACK_DAYS = 1
AGENDA_PAGE_SIZE = 200

# Attendance status values as sent/received on the wire by XPS Network's own
# web app (`updateAttendance2` mutation, `Practice.attendance[].attendance`).
STATUS_ATTENDED = "Attended"
STATUS_SICK = "Sick"
STATUS_INJURED = "Injured"
STATUS_OTHER = "Other"
STATUS_UNKNOWN = "Unknown"

ATTENDANCE_STATUSES = [
    STATUS_ATTENDED,
    STATUS_SICK,
    STATUS_INJURED,
    STATUS_OTHER,
    STATUS_UNKNOWN,
]

SERVICE_SET_ATTENDANCE = "set_attendance"
ATTR_ATHLETE_ID = "athlete_id"
ATTR_SESSION_ID = "session_id"
ATTR_STATUS = "status"
ATTR_COMMENT = "comment"
