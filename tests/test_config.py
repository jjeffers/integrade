"""Unit tests for :mod:`integrade.config`."""
import os
from unittest import mock

from integrade import config, exceptions
from integrade.utils import uuid4

import pytest


@pytest.mark.parametrize('ssl', [True, False])
@pytest.mark.parametrize('protocol', ['http', 'https'])
def test_get_config(ssl, protocol):
    """If a base url is specified in the environment, we use it."""
    with mock.patch.object(config, '_CONFIG', None):
        token = uuid4()
        user = uuid4()
        os.environ['CLOUDIGRADE_TOKEN'] = token
        os.environ['CLOUDIGRADE_USER'] = user
        os.environ['CLOUDIGRADE_BASE_URL'] = 'example.com'
        os.environ['USE_HTTPS'] = 'True' if protocol == 'https' else 'False'
        os.environ['SSL_VERIFY'] = 'True' if ssl else 'False'
        cfg = config.get_config()
        assert cfg['superuser_token'] == token
        assert cfg['superuser'] == user
        assert cfg['base_url'] == 'example.com'
        assert cfg['scheme'] == protocol
        assert cfg['ssl-verify'] == ssl
        assert cfg['api_version'] == 'v1'


def test_get_config_negative():
    """If a base url is specified in the environment, we use it."""
    with mock.patch.object(config, '_CONFIG', None):
        with pytest.raises(exceptions.BaseUrlNotFound):
            os.environ['CLOUDIGRADE_TOKEN'] = uuid4()
            os.environ.pop('CLOUDIGRADE_BASE_URL')
            config.get_config()

    with mock.patch.object(config, '_CONFIG', None):
        with pytest.raises(exceptions.TokenNotFound):
            os.environ.pop('CLOUDIGRADE_TOKEN')
            os.environ['CLOUDIGRADE_BASE_URL'] = 'example.com'
            config.get_config()
