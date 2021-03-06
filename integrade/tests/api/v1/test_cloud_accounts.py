"""Tests for cloud accounts.

:caseautomation: automated
:casecomponent: api
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
from time import time
from urllib.parse import urljoin

import pytest

from integrade import api, config
from integrade.injector import (
    inject_aws_cloud_account,
)
from integrade.tests import aws_utils
from integrade.tests import urls
from integrade.tests.utils import (
    create_user_account,
    get_auth,
    needed_aws_profiles_present,
)
from integrade.utils import uuid4


@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(1),
                    reason='needs at least 1 aws profile')
def test_create_cloud_account(drop_account_data, cloudtrails_to_delete):
    """Ensure cloud accounts can be registered to a user.

    :id: f7a9225b-83af-4567-b59a-a8bb62d612c9
    :description: Ensure an user can register a cloud account by specifying
        the role ARN.
    :steps: 1) Create a user and authenticate with their password
        2) Send a POST with the cloud account information to 'api/v1/account/'
        3) Send a GET to 'api/v1/account/' to get a list of the cloud accounts
        4) Attempt to create a duplicate and expect it to be rejected
        5) Attempt to delete the account and expect to succeed
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) The account cannot be duplicated, and attempts to do so receive a
            400 status code.
        3) The account can be deleted and we get a 200 response.
    """
    auth = get_auth()
    client = api.Client(authenticate=False)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][0]
    profile_name = aws_profile['name']
    acct_arn = aws_profile['arn']
    cloud_account = {
        'account_arn': acct_arn,
        'name': uuid4(),
        'resourcetype': 'AwsAccount'
    }
    start = time()
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    end = time()
    create_data = create_response.json()
    assert end - start < 7
    assert create_response.status_code == 201
    assert create_data['account_arn'] == acct_arn
    assert create_data['aws_account_id'] == aws_profile['account_number']

    # Assert that a cloudtrail has been set up in the customer's account
    cloudtrail_client = aws_utils.aws_session(
        profile_name).client('cloudtrail')
    trail_names = [trail['Name']
                   for trail in
                   cloudtrail_client.describe_trails()['trailList']]
    assert aws_profile['cloudtrail_name'] in trail_names
    # since account was created, add trail to cleanup
    cloudtrails_to_delete.append(
        (profile_name, aws_profile['cloudtrail_name']))

    acct = create_response.json()

    # get specific account
    account_url = urljoin(urls.CLOUD_ACCOUNT, '{}/'.format(acct['id']))
    get_response = client.get(account_url, auth=auth)
    assert acct == get_response.json()

    # list cloud accounts associated with this user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth)
    assert acct in list_response.json()['results']

    # Check if account name can be patched
    payload = {
        'name': 'new_name',
        'resourcetype': 'AwsAccount',
    }
    response = client.patch(
        account_url, payload=payload, auth=auth)
    response = client.get(account_url, auth=auth)
    assert response.json()['name'] == 'new_name'

    # Check if an account can be updated
    payload = {
        'account_arn': acct_arn,
        'name': 'new_name2',
        'resourcetype': 'AwsAccount',
    }
    response = client.put(
        account_url, payload=payload, auth=auth)
    response = client.get(account_url, auth=auth)
    assert response.json()['name'] == 'new_name2'

    # assert we cannot create duplicate
    client.response_handler = api.echo_handler
    response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert response.status_code == 400
    assert 'account_arn' in response.json().keys()
    assert 'already exists' in response.json()['account_arn'][0]

    # attempt to delete the specific account
    delete_response = client.delete(
        urljoin(urls.CLOUD_ACCOUNT,
                '{}/'.format(acct['id'])
                ), auth=auth)
    assert delete_response.status_code == 204


@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(2),
                    reason='needs at least 2 aws profile')
def test_create_multiple_cloud_accounts(
        drop_account_data,
        cloudtrails_to_delete):
    """Ensure cloud accounts can be registered to a user.

    :id: f1db2617-fd15-4270-b9d3-595db001e1e7
    :description: Ensure an user can register multiple cloud accounts as long
        as each ARN is associated with unique cloud accounts.
    :steps: 1) Create a user and authenticate with their password
        2) Send POSTS with each of the cloud account's information to
            'api/v1/account/'
        3) Send a GET to 'api/v1/account/' to get a list of the cloud accounts
    :expectedresults: The server returns a 201 response with the information of
        the created accounts.
    """
    client = api.Client(authenticate=False)
    auth = get_auth()
    cfg = config.get_config()
    accts = []
    for profile in cfg['aws_profiles']:
        arn = profile['arn']
        cloud_account = {
            'account_arn': arn,
            'name': uuid4(),
            'resourcetype': 'AwsAccount'
        }
        create_response = client.post(
            urls.CLOUD_ACCOUNT,
            payload=cloud_account,
            auth=auth
        )
        assert create_response.status_code == 201
        cloudtrails_to_delete.append((
            profile['name'],
            profile['cloudtrail_name']
        ))

        accts.append(create_response.json())

    # list cloud accounts associated with this user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth)
    for acct in accts:
        assert acct in list_response.json()['results']


@pytest.mark.skip(
    reason='https://gitlab.com/cloudigrade/cloudigrade/issues/429')
@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(2),
                    reason='needs at least 2 aws profile')
def test_create_cloud_account_duplicate_names(
    drop_account_data, cloudtrails_to_delete
):
    """Ensure cloud accounts can be registered to a user.

    :id: 47b6b382-092a-420f-a8b0-63e6578e4857
    :description: Ensure an user can register a cloud account by specifying
        the role ARN.
    :steps: 1) Create a user and authenticate with their password
        2) Send a POST with the cloud account information to 'api/v1/account/'
        3) Send a GET to 'api/v1/account/' to get a list of the cloud accounts
        4) Attempt to create a duplicate and expect it to be rejected
        5) Attempt to delete the account and expect to be rejected
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) The account cannot be duplicated, and attempts to do so receive a
            400 status code.
        3) The account cannot be deleted and attempts to do so receive a 405
            response.
    """
    user = create_user_account()
    auth = get_auth(user)
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    cfg = config.get_config()
    inject_aws_cloud_account(user['id'], name=cfg['aws_profiles'][0]['name'])

    # Now try to reuse the name
    cloud_account = {
        'account_arn': cfg['aws_profiles'][0]['arn'],
        'name': cfg['aws_profiles'][0]['name'],
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 400


@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(2),
                    reason='needs at least 2 aws profile')
def test_create_cloud_account_duplicate_names_different_users(
    drop_account_data, cloudtrails_to_delete
):
    """Ensure cloud accounts can be registered to a user.

    :id: 7bf483b7-f0d0-40db-9c18-396dc4a58792
    :description: Ensure an user can register a cloud account by specifying
        the role ARN.
    :steps: 1) Create a user and authenticate with their password
        2) Send a POST with the cloud account information to 'api/v1/account/'
        3) Send a GET to 'api/v1/account/' to get a list of the cloud accounts
        4) Attempt to create a duplicate and expect it to be rejected
        5) Attempt to delete the account and expect to be rejected
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) The account cannot be duplicated, and attempts to do so receive a
            400 status code.
        3) The account cannot be deleted and attempts to do so receive a 405
            response.
    """
    user = create_user_account()
    auth = get_auth(user)
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][0]
    profile_name = aws_profile['name']
    inject_aws_cloud_account(user['id'], name=profile_name)

    # Now try to reuse the name
    auth = get_auth()
    aws_profile = cfg['aws_profiles'][1]
    acct_arn = aws_profile['arn']
    cloud_account = {
        'account_arn': acct_arn,
        'name': profile_name,
        'resourcetype': 'AwsAccount'
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 201, create_response.json()


@pytest.mark.serial_only
def test_negative_read_other_cloud_account(
        drop_account_data, cloudtrails_to_delete):
    """Ensure users cannot access eachother's cloud accounts.

    :id: b500d301-dd46-41b0-af3b-0145f9404784
    :description: Ensure one user is not allowed to read another user's cloud
        account data.
    :steps: 1) Create two users and authenticate with their passwords
        2) For each user, send a POST with the cloud account information to
            'api/v1/account/'
        3) For each, send a GET to 'api/v1/account/' to get a list of the
           cloud accounts
        4) Ensure a super user sees all accounts.
    :expectedresults: The server only returns cloud accounts related to the
        user making the request, except the super user, who sees all accounts.
    """
    client = api.Client(authenticate=False)
    user1 = create_user_account()
    user2 = create_user_account()
    auth1 = get_auth(user1)
    auth2 = get_auth(user2)

    # create cloud account for 1st user
    acct1 = inject_aws_cloud_account(user1['id'])
    # create account for 2nd user
    acct2 = inject_aws_cloud_account(user2['id'])

    # list cloud accounts associated with each user
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth1)
    acct_ids_found = [
        acct['aws_account_id']
        for acct in list_response.json()['results']
    ]
    assert acct1['aws_account_id'] in acct_ids_found
    assert acct2['aws_account_id'] not in acct_ids_found

    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth2)
    acct_ids_found = [
        acct['aws_account_id']
        for acct in list_response.json()['results']
    ]
    assert acct2['aws_account_id'] in acct_ids_found
    assert acct1['aws_account_id'] not in acct_ids_found

    # use super user token to see all
    superclient = api.Client()
    list_response = superclient.get(urls.CLOUD_ACCOUNT)
    acct_ids_found = [
        acct['aws_account_id']
        for acct in list_response.json()['results']
    ]
    assert acct2['aws_account_id'] in acct_ids_found
    assert acct1['aws_account_id'] in acct_ids_found

    # create cloud account with super user
    # update cloud account to differnt ARN
    # FIXME: clumsy way to get super user id
    all_users = superclient.get(urls.USER_LIST).json()
    super_user_id = [
        user['id'] for user in all_users if user['is_superuser']
    ][0]
    acct3 = inject_aws_cloud_account(super_user_id)
    list_response = superclient.get(urls.CLOUD_ACCOUNT)
    acct_ids_found = [
        acct['aws_account_id']
        for acct in list_response.json()['results']
    ]
    assert acct3['aws_account_id'] in acct_ids_found
    assert list_response.json()['count'] == 3

    # make sure user1 still just see theirs
    list_response = client.get(urls.CLOUD_ACCOUNT, auth=auth1)
    acct_ids_found = [
        acct['aws_account_id']
        for acct in list_response.json()['results']
    ]
    assert acct1['aws_account_id'] in acct_ids_found
    assert acct2['aws_account_id'] not in acct_ids_found
    assert acct3['aws_account_id'] not in acct_ids_found


@pytest.mark.parametrize('field_to_delete', [
    'resourcetype',
    'account_arn',
    ])
def test_negative_create_cloud_account_missing(drop_account_data,
                                               field_to_delete):
    """Ensure attempts to create cloud accounts missing data are rejected.

    :id: a93821ba-4181-47e7-b685-dbe642c1441e
    :description: Ensure an user cannot register a cloud account missing data.
    :steps: 1) Create a user and authenticate with their password
        2) Send a POST with the incomplete cloud account information to
            'api/v1/account/'
    :expectedresults: The server rejects the incomplete request.
    """
    auth = get_auth()
    client = api.Client(authenticate=False, response_handler=api.echo_handler)
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][0]
    profile_name = aws_profile['name']
    acct_arn = aws_profile['arn']

    cloud_account = {
        'account_arn': acct_arn,
        'resourcetype': 'AwsAccount',
        'name': profile_name,
    }
    # remove one field
    cloud_account.pop(field_to_delete)
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    missing_fields = create_response.json().keys()
    assert create_response.status_code == 400, create_response.json()
    assert field_to_delete in missing_fields, create_response.json()


@pytest.mark.serial_only
@pytest.mark.skipif(not needed_aws_profiles_present(1),
                    reason='needs at least 1 aws profile')
def test_cloudtrail_updated(
        drop_account_data,
        cloudtrails_and_buckets_to_delete):
    """Ensure the cloudtrail is updated if a pre-existing one is found.

    :id: f4a93a35-41e5-490d-bc3f-7c0df9ea805b
    :description: Ensure that at cloud account creation, if a pre-existing
        cloudigrade cloudtrail is found, it is updated.
    :steps: 1) Create a user and authenticate with their password
        2) Create a cloudtrail with the same name that cloudigrade uses but
            a different s3 bucket.
        3) Create a cloud account using this same AWS account.
        4) Assert that the cloudtrail is updated and now uses correct s3
            bucket.
    :expectedresults:
        1) The server returns a 201 response with the information
            of the created account.
        2) The cloudtrail is updated to use the correct s3 bucket.
    """
    auth = get_auth()
    cfg = config.get_config()
    aws_profile = cfg['aws_profiles'][0]
    profile_name = aws_profile['name']
    acct_arn = aws_profile['arn']
    client = api.Client(authenticate=False)
    cloudtrail_client = aws_utils.aws_session(
        profile_name).client('cloudtrail')

    # create our own cloud trail with a different s3 bucket
    bucket_name = aws_utils.create_bucket_for_cloudtrail(profile_name)
    # Queue the bucket for cleanup
    cloudtrails_and_buckets_to_delete.append(
        (profile_name, None, bucket_name))
    if cloudtrail_client.describe_trails(
            trailNameList=[aws_profile['cloudtrail_name']]
    ).get('trailList'):
        cloudtrail_client.update_trail(
            Name=aws_profile['cloudtrail_name'],
            S3BucketName=bucket_name
        )
    else:
        cloudtrail_client.create_trail(
            Name=aws_profile['cloudtrail_name'],
            S3BucketName=bucket_name
        )
    # Queue the cloudtrail for cleanup
    cloudtrails_and_buckets_to_delete.append(
        (profile_name, aws_profile['cloudtrail_name'], None))
    cloud_account = {
        'account_arn': acct_arn,
        'resourcetype': 'AwsAccount',
        'name': 'name',
    }
    create_response = client.post(
        urls.CLOUD_ACCOUNT,
        payload=cloud_account,
        auth=auth
    )
    assert create_response.status_code == 201, create_response.json()

    acct = create_response.json()

    # get specific account
    get_response = client.get(
        urljoin(urls.CLOUD_ACCOUNT,
                '{}/'.format(acct['id'])
                ), auth=auth)
    assert acct == get_response.json()

    # Assert that a cloudtrail has been set up in the customer's account
    trails = [trail for trail in cloudtrail_client.describe_trails()[
        'trailList']]
    trail_names = [trail['Name'] for trail in trails]
    assert aws_profile['cloudtrail_name'] in trail_names
    the_trail = [trail for trail in trails if trail['Name']
                 == aws_profile['cloudtrail_name']][0]
    assert the_trail['S3BucketName'].endswith('-cloudigrade-s3')
    assert bucket_name not in the_trail['S3BucketName']
