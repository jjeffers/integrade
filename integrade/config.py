"""Tools to manage global configuration of integrade."""
import os
from copy import deepcopy

from integrade import exceptions


# `get_config` uses this as a cache. It is intentionally a global. This design
# lets us do interesting things like flush the cache at run time or completely
# avoid a config file by fetching values from the UI.
_CONFIG = None


def get_config():
    """Return a copy of the global config dictionary.

    This method makes use of a cache. If the cache is empty, the configuration
    file is parsed and the cache is populated. Otherwise, a copy of the cached
    configuration object is returned.

    :returns: A copy of the global server configuration object.
    """
    global _CONFIG  # pylint:disable=global-statement
    if _CONFIG is None:
        _CONFIG = {}
        _CONFIG['api_version'] = os.environ.get(
            'CLOUDIGRADE_API_VERSION', 'v1')
        _CONFIG['base_url'] = os.environ.get('CLOUDIGRADE_BASE_URL', '')
        # expect CLOUDIGRADE_CUSTOMER_ROLE_ARNS to be a whitespace delimitted
        # list of valid ARNs, each tied to a different AWS account
        _CONFIG['valid_roles'] = os.environ.get(
            'CLOUDIGRADE_CUSTOMER_ROLE_ARNS', '')
        if len(_CONFIG['valid_roles']) > 0:
            _CONFIG['valid_roles'] = _CONFIG['valid_roles'].split()
        else:
            _CONFIG['valid_roles'] = []
        if _CONFIG['base_url'] == '':
            raise exceptions.BaseUrlNotFound(
                'Make sure you have $CLOUDIGRADE_BASE_URL set in in'
                ' your environment.'
            )
        _CONFIG['superuser_token'] = os.environ.get('CLOUDIGRADE_TOKEN', None)
        if os.environ.get('USE_HTTPS', 'false').lower() == 'true':
            _CONFIG['scheme'] = 'https'
        else:
            _CONFIG['scheme'] = 'http'
        if os.environ.get('SSL_VERIFY', 'false').lower() == 'true':
            _CONFIG['ssl-verify'] = True
        else:
            _CONFIG['ssl-verify'] = False
    return deepcopy(_CONFIG)
