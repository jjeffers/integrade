"""Test account report summary API.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import datetime
from random import shuffle
from urllib.parse import urljoin

import pytest

from integrade import api
from integrade.injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)
from integrade.tests import urls, utils


def test_image_report_empty():
    """Test accounts without any instance or image report has empty summary.

    :id: 2a152ef6-fcd8-491c-b3cc-bda81699453a
    :description: Test that an account without any instances or images shows up
        in the results with 0 counts.
    :steps:
        1) Add a cloud account
        2) GET from the image report endpoint
    :expectedresults:
        - An empty list is returned
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    client = api.Client(authenticate=False)

    report_start, report_end = utils.get_time_range()
    params = {
        'start': report_start,
        'end': report_end,
        'account_id': acct['id'],
    }
    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)

    images = response.json()['images']

    assert images == [], repr(images)


def test_past_without_instances():
    """Test accounts with instances only after the filter period.

    :id: 72aaa6e2-2c60-4e71-bb47-3644bd6beb71
    :description: Test that an account with instances that were created prior
        to the current report end date.
    :steps:
        1) Add a cloud account
        2) Inject instance data for today
        3) GET from the account report endpoint for 30 days ago
    :expectedresults:
        - The account is in the response and matches the created account
        - Instances, images, RHEL, and Openshift all have None counts
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    client = api.Client(authenticate=False)

    # ask for last 30 days
    report_start, report_end = utils.get_time_range()
    params = {
        'start': report_start,
        'end': report_end,
        'account_id': acct['id'],
    }

    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)
    images = response.json()['images']

    assert images == [], repr(images)

    # No tagged images, started 60 days ago and stopped 45 days ago
    image_type = ''
    instance_start = 60
    instance_end = 45
    events = [instance_start, instance_end]
    inject_instance_data(acct['id'], image_type, events)

    # test that still have no images in report
    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)
    images = response.json()['images']

    assert images == [], repr(images)


@pytest.mark.debug
@pytest.mark.parametrize('conf', [
    ('', 1, 1, False, False, 2, 1, 0),
    ('windows', 1, 1, False, False, 2, 1, 0),
    ('rhel', 1, 1, True, False, 2, 1, 0),
    ('openshift', 1, 1, False, True, 2, 1, 0),
    ('rhel,openshift', 1, 1, True, True, 2, 1, 0),
])
def test_image_tagging(conf):
    """Test instance events generate image usage results with correct tags.

    :id: f3c84697-a40c-40d9-846d-117e2647e9d3
    :description: Test combinations of image tags, start/end events, and the
        resulting counts from the summary report API.
    :steps:
        1) Add a cloud account
        2) Insert instance, image, and event data
        3) GET from the image report endpoint
    :expectedresults:
        - The images have correct tags and usage amounts
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    image_type, exp_inst, exp_images, exp_rhel, exp_openshift, \
        instance_start, instance_end, offset = conf
    # start and end values indicate number of days in the past
    # so their difference is the whole number of days of runtime
    expected_runtime = (instance_start - instance_end) * 24 * 60 * 60
    client = api.Client(authenticate=False)

    events = [instance_start]
    if instance_end:
        events.append(instance_end)
    inject_instance_data(acct['id'], image_type, events)

    report_start, report_end = utils.get_time_range(offset)
    params = {
        'start': report_start,
        'end': report_end,
        'account_id': acct['id'],
    }
    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)

    image = response.json()['images'][0]
    assert image['rhel'] == exp_rhel, repr(image)
    assert image['openshift'] == exp_openshift, repr(image)
    assert int(image['runtime_seconds']) == int(expected_runtime), repr(image)


def test_runtime_requests_from_future():
    """Test future start and end times for empty set result.

    :id: 133A04EE-55C3-4948-B2F9-D89A6A84C9FC
    :description: Test events that start/end in the future ensuring
        that results are empty [].
    :steps:
        1) Add a cloud account
        2) Insert past instance, image, and event data
        3) Insert future instance, image, and event data
        4) GET from the image report endpoint
    :expectedresults:
        - When start/end times are in the future OR when start>end
            expect runtine_seconds to be empty.
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    image_type = 'openshift'
    instance_start = 2
    instance_end = 1
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    events = [instance_start]
    if instance_end:
        events.append(instance_end)
    inject_instance_data(acct['id'], image_type, events)

    report_start, report_end = utils.get_time_range(180)
    params = {
        'start': report_start,
        'end': report_end,
        'account_id': acct['id'],
    }
    response = client.get(urls.REPORT_ACCOUNTS, params=params, auth=auth)
    response_data = response.json()['cloud_account_overviews'][0]
    rhel_instances = response_data['rhel_instances']
    openshift_instances = response_data['openshift_instances']
    rhel_runtime_seconds = response_data['rhel_runtime_seconds']
    openshift_runtime_seconds = response_data['openshift_runtime_seconds']

    assert rhel_instances is None
    assert openshift_instances is None
    assert rhel_runtime_seconds is None
    assert openshift_runtime_seconds is None
    past_date = datetime.datetime.now() + datetime.timedelta(-30)
    backwards_params = {
        'start': report_start,
        'end': past_date,
        'account_id': acct['id'],
    }
    response = client.get(
        urls.REPORT_ACCOUNTS,
        params=backwards_params,
        auth=auth,
        )
    response_error = response.json()['non_field_errors'][0]
    assert response_error == 'End date must be after start date.'


def test_flagged_account_numbers():
    """Test the number of flagged images in accounts.

    :id: BBD687F5-0B78-4E86-8368-C5C8EEBD9263
    :description: Test that the number of images reported as flagged matches
    the flagged/challenged images in accounts.

    :steps:
        1) Add a cloud account
        2) Insert RHEL and RHOCP image
        3) Check number of challenged/flagged RHEL/RHOCP images
        4) Challenge images
        5) Check number of challenged/flagged RHEL/RHOCP images
    :expectedresults:
        - Challenged RHEL images = 0 when none are challenged
        - Challenged RHEL images > 0 when one or more are challenged
        - Challenged RHOCP images = 0 when none are challenged
        - Challenged RHOCP images > 0 when one or more are challenged
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])

    images = {}
    for tag in ('rhel', 'openshift'):
        image_type = tag
        events = [1, 2]
        client = api.Client(
            authenticate=False,
            response_handler=api.echo_handler
        )
        images[tag] = inject_instance_data(
            acct['id'],
            image_type,
            events,
        )

        report_start, report_end = utils.get_time_range()
        params = {
            'start': report_start,
            'end': report_end,
            'account_id': acct['id'],
        }
    response = client.get(
        urls.REPORT_ACCOUNTS,
        params=params,
        auth=auth
        ).json()['cloud_account_overviews'][0]
    assert response['rhel_instances'] == 1
    assert response['openshift_instances'] == 1
    assert response['rhel_images_challenged'] == 0
    assert response['openshift_images_challenged'] == 0

    rhel_image = images.get('rhel')
    openshift_image = images.get('openshift')
    images = [rhel_image, openshift_image]
    # Shuffle images to be sure that each is called first, to ensure that
    # order doesn't matter
    shuffle(images)
    first_image_url = urljoin(urls.IMAGE, str(images[0]['image_id'])) + '/'
    second_image_url = urljoin(urls.IMAGE, str(images[1]['image_id'])) + '/'
    first_image_response = client.get(first_image_url, auth=auth).json()
    second_image = ''
    challenged_image = ''
    unchallenged_image = ''

    # Challenge first image
    if first_image_response['rhel']:
        first_image_response['rhel_challenged'] = True
        client.put(
            first_image_url,
            first_image_response,
            auth=auth
        )
        first_image = 'rhel'
        second_image = 'openshift'
        challenged_image = 'rhel_images_challenged'
        unchallenged_image = 'openshift_images_challenged'
    else:
        first_image_response['openshift_challenged'] = True
        client.put(
            first_image_url,
            first_image_response,
            auth=auth
        )
        first_image = 'openshift'
        second_image = 'rhel'
        challenged_image = 'openshift_images_challenged'
        unchallenged_image = 'rhel_images_challenged'
    first_response = client.get(
        urls.REPORT_ACCOUNTS,
        params=params,
        auth=auth
        ).json()['cloud_account_overviews'][0]

    assert first_response[challenged_image] == 1
    assert first_response[unchallenged_image] == 0
    assert first_response[f'{second_image}_instances'] == 1
    assert first_response[f'{first_image}_instances'] == 0

    # Challenge second image
    second_image_response = client.get(second_image_url, auth=auth).json()
    second_image_response[f'{second_image}_challenged'] = True

    client.put(
        second_image_url,
        second_image_response,
        auth=auth
    )
    second_response = client.get(
        urls.REPORT_ACCOUNTS,
        params=params,
        auth=auth
        ).json()['cloud_account_overviews'][0]

    assert second_response[challenged_image] == 1
    assert second_response[unchallenged_image] == 1
    assert second_response[f'{second_image}_instances'] == 0
    assert second_response[f'{first_image}_instances'] == 0


@pytest.mark.parametrize('impersonate', (False, True))
def test_list_images_while_impersonating(impersonate):
    """Test account data fetched via impersonating a user as a superuser.

    :id: 5f99c7ec-a4d3-4040-868f-9340015e4c9c
    :description: Test that the same assertions can be made for fetching data
        as a regular user and fetching data impersonating that same user
    :steps:
        1) Add a cloud account
        2) Insert instance, image, and event data
        3) GET from the image report endpoint as regular user
        3) GET from the image report endpoint as super user impersonating
    :expectedresults:
        - The images are returned for the user and a super user, but
            no one else.
    """
    user = utils.create_user_account()
    auth = utils.get_auth(user)
    acct = inject_aws_cloud_account(user['id'])
    image_type = 'rhel'
    exp_rhel = True
    exp_openshift = False
    start = 12
    end = 10
    offset = 0
    # start and end values indicate number of days in the past
    # so their difference is the whole number of days of runtime
    expected_runtime = (start - end) * 24 * 60 * 60

    # authenticate (as superuser) if we are impersonating
    client = api.Client(authenticate=impersonate)

    events = [start]
    if end:
        events.append(end)
    inject_instance_data(acct['id'], image_type, events)

    report_start, report_end = utils.get_time_range(offset)
    params = {
        'start': report_start,
        'end': report_end,
        'account_id': acct['id'],
    }
    response = client.get(urls.REPORT_IMAGES, params=params, auth=auth)

    image = response.json()['images'][0]
    assert image['rhel'] == exp_rhel, repr(image)
    assert image['openshift'] == exp_openshift, repr(image)
    assert int(image['runtime_seconds']) == int(expected_runtime), repr(image)
