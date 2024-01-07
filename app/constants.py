"""constants: Constants for the app."""

import pytz

# String constants
REQUEST = "request"
CURRENT_USER = "current_user"
FORM = "form"
MESSAGE = "message"

TIMEZONES = [(timezone, timezone) for timezone in pytz.common_timezones]
