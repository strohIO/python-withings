
# python-withings

Withings API Python Client Implementation



## Requirements

*  `requests-oauthlib`_ (always)
.. _requests-oauthlib: https://pypi.python.org/pypi/requests-oauthlib


## Usage

```python

from withings import Withings
from withings import WithingsAUTH

# If first time authorizing user
with_auth = WithingsAUTH('developer client id',
						 'developer callback url')
auth_code = with_auth.authorize("user email address",
								"user password")

# Pass in authorization code to use API
withings = Withings('developer client id',
					'developer client secret',
					'developer callback url',
					auth_code=auth_code)

# Start making calls
sleep = withings.get_sleep_detail_data(
			last_update_date=datetime(year=2021, month=5, day=18))

```