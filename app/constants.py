"""constants: Constants for the app."""

import pytz

INVALID_FORM_FIELDS = "Invalid form field(s). See errors on form."
REQUEST = "request"
CURRENT_USER = "current_user"
TIMEZONES = [(timezone, timezone) for timezone in pytz.common_timezones]
