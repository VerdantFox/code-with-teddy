"""constants: Constants for the app."""

import pytz

# String constants
REQUEST = "request"
CURRENT_USER = "current_user"
FORM = "form"
MESSAGE = "message"
LOGIN_FORM = "login_form"
GUEST_ID = "guest_id"

# Number constants
ONE_YEAR_IN_SECONDS = 60 * 60 * 24 * 365  # 1 year

# List constants
TIMEZONES = [(timezone, timezone) for timezone in pytz.common_timezones]
