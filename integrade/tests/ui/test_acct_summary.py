"""Tests for account summary list.

:caseautomation: automated
:casecomponent: ui
:caseimportance: high
:caselevel: integration
:requirement: Cloud Meter
:testtype: functional
:upstream: yes
"""
import calendar
import datetime
import math
import random
import time

from dateutil.relativedelta import relativedelta

import pytest

from selenium.webdriver.common.keys import Keys

from integrade.tests import utils
from integrade.utils import (
    get_expected_hours_in_past_30_days,
    round_hours,
)

from .utils import (
    element_has_text,
    fill_input_by_placeholder,
    find_element_by_text,
    page_has_text,
    retry_w_timeout,
    return_url,
)
from ...injector import (
    inject_aws_cloud_account,
    inject_instance_data,
)


def sum_usage(usage):
    """Sum up the total number of seconds from an usage list.

    :param usage: A list with an even number of items where each pair indicates
        instances' turn on and turn off events.
    :returns: the total number of seconds that an instance was running.
    """
    total_seconds = 0
    for start, end in zip(usage[0::2], usage[1::2]):
        total_seconds += (end - start).total_seconds()
    return total_seconds


def test_empty(cloud_account_data, browser_session, ui_acct_list):
    """Account summaries should shown 0 images and instances without data.

    :id: d23e7196-3139-4017-8d46-6d430c5c4f84
    :description: Looking at account summaries for a date range after creation
        but without any observed instances should show 0 counts.
    :steps:
        1) Add a cloud account
    :expectedresults:
        Both images and instance should show 0 counts
    """
    assert find_element_by_text(browser_session, '0RHEL')
    assert find_element_by_text(browser_session, '0RHOCP')
    assert page_has_text(browser_session, '0 Images')
    assert page_has_text(browser_session, '0 Instances')


def test_summary_list_layout(cloud_account_data, browser_session,
                             ui_acct_list):
    """Confirm aspects of the layout of elements on the summary list.

    :id: 873fb451-6ed7-4be4-9dfa-a8f0c22a4dfb
    :description: This test was created to check the behavior of long account
        names.
    :steps:
        1) Add a cloud account with a short name and another with a long name
        2) Check the lengths of both summary rows
    :expectedresults:
        - Confirm both lengths are equal
    """
    cloud_account_data('', [15], name='x ' * 127)
    browser_session.refresh()

    page_has_text(browser_session, 'x x x x', timeout=30)

    # Compare 'scrollWidth' of two list-group-item
    a, b = browser_session.execute_script("""
    var items = document.querySelectorAll('.list-group-item')
    return [items[0].scrollWidth, items[1].scrollWidth]
    """)

    assert a == b

    assert find_element_by_text(browser_session, '1 Images', timeout=1)
    assert find_element_by_text(browser_session, '1 Instances')


@pytest.mark.parametrize(
    'start', (45, 31, 30, 29, 28, 15))
def test_running_start_times(start, cloud_account_data, browser_session,
                             ui_acct_list):
    """Instances left running from various days ago should count today.

    :id: e3f8972d-d1dc-4a59-950f-d7a5ad1491a5
    :description: An instance and its image should be counted if it was started
        in the past and has not yet been stopped. This should be counted if it
        started prior to the 30 day window, at cusps of the month filter, and
        within the 30 day range.
    :steps:
        1) Add a cloud account
        2) Create instance data as begun at a certain day in the past
    :expectedresults:
        - Confirm the instance and its image is counted once within the default
          date filter
    """
    cloud_account_data('', [start])
    browser_session.refresh()
    assert find_element_by_text(browser_session, '1 Images', timeout=1)
    assert find_element_by_text(browser_session, '1 Instances')


@pytest.mark.parametrize(
    'tag', ('', 'rhel', 'openshift', 'rhel,openshift'))
def test_running_tags(tag, cloud_account_data, browser_session, ui_acct_list):
    """Tags on images should not affect image or instance counts in summaries.

    :id: e9ea3960-051d-47cd-a23b-013ad8deb243
    :description: The presence of tags should not affect image or instance
    counts, but should be reflected in the summaries themselves.
    :steps:
        1) Add a cloud account
        2) Create images and instances with no tag, each tag, and both tags
    :expectedresults:
        - The image and instance counts should always be 1
        - The RHEL label should be 1 when the image has the rhel tag
        - The RHOCP label should be 1 when the image has the openshift tag
        - Both labels should be 1 when an image has both tags
    """
    cloud_account_data(tag, [10])
    hours, spare_min, events = get_expected_hours_in_past_30_days([10, None])
    hours = round_hours(hours, spare_min)
    browser_session.refresh()

    assert find_element_by_text(browser_session, '1 Images', timeout=1)
    assert find_element_by_text(browser_session, '1 Instances')

    for level in ('summary', 'detail'):
        with return_url(browser_session):
            if level == 'detail':
                find_element_by_text(
                    browser_session, 'First Account', timeout=1).click()
                time.sleep(1)

            if 'rhel' in tag:
                # No spaces because there are not spaces between the DOM nodes,
                # even tho they are rendered separately.
                assert find_element_by_text(browser_session,
                                            f'{hours}RHEL')
            else:
                assert find_element_by_text(browser_session, '0RHEL')
            if 'openshift' in tag:
                assert find_element_by_text(browser_session,
                                            f'{hours}RHOCP')
            else:
                assert find_element_by_text(browser_session, '0RHOCP')


def test_reused_image(cloud_account_data, browser_session, ui_acct_list):
    """An image used in multiple instance should only count once in summary.

    :id: 87a32f9c-da2c-4834-81d5-696b50433bf8
    :description: Multiple instances using the same image should not cause
        those images to be counted multiple times.
    :steps:
        1) Add a cloud account
        2) Create data for three instances with the same AMI ID
    :expectedresults:
        There should be 3 instances and only 1 instance
    """
    cloud_account_data('', [10], ec2_ami_id='image1')
    cloud_account_data('', [10], ec2_ami_id='image1')
    cloud_account_data('', [10], ec2_ami_id='image1')

    browser_session.refresh()

    assert find_element_by_text(browser_session, '1 Images', timeout=1)
    assert find_element_by_text(browser_session, '3 Instances')


@pytest.mark.skip(reason='http://gitlab.com/cloudigrade/frontigrade/issues/67')
def test_last_event_time(cloud_account_data, browser_session, ui_acct_list):
    """Account summaries show the date and time of the last observed event.

    :id: c6d5c52c-0640-4409-8b43-7beb600217d7
    :description: Each account should display including the time when the last
        instance was observed being powered on or off.
    :steps:
        1) Add a cloud account
        2) Inject instance and image data with a known event time powering on
        3) View the dashboard to observe the date shown
    :expectedresults:
        - The date should be the same date as the known power on event
    """
    when = datetime.datetime(2018, 8, 10, 9, 51)
    expected = 'Created 9:51AM, August 10th 2018'

    cloud_account_data('', [when], ec2_ami_id='image1')
    browser_session.refresh()
    assert find_element_by_text(browser_session, expected, timeout=1), \
        browser_session.page_source


def test_account_name_filter(
    cloud_account_data, browser_session, ui_user, ui_acct_list
):
    """Account summary list can be filtered by name.

    :id: e8c290d0-481d-46c8-9da6-540ec4f8dc24
    :description: The filter should show matching accounts in the summary list.
    :steps:
        1) Add two cloud account with a known and different names
        2) Enter a word in one account name, but not both, and apply the filter
        3) Click the link to clear the filters
    :expectedresults:
        The matching account should still be listed, the other account should
        not. When clearing the filter, both accounts should appear again.
    """
    acct2 = inject_aws_cloud_account(ui_user['id'], 'Second Account')

    for i in range(3):
        cloud_account_data('', [40, 39], ec2_ami_id='image2')
        cloud_account_data('', [10], ec2_ami_id='image1')

    inject_instance_data(acct2['id'], '', [10], ec2_ami_id='image1')
    browser_session.refresh()

    assert find_element_by_text(browser_session, 'First Account', timeout=1)
    assert find_element_by_text(browser_session, 'Second Account')

    input = fill_input_by_placeholder(
        browser_session, None,
        'Filter by Name', 'Second')

    input.send_keys(Keys.RETURN)
    assert not find_element_by_text(browser_session, 'First Account')
    assert find_element_by_text(browser_session, 'Second Account')

    input = fill_input_by_placeholder(
        browser_session, None,
        'Filter by Name', 'First')
    input.send_keys(Keys.RETURN)
    assert find_element_by_text(browser_session, 'First Account', timeout=1)
    assert not find_element_by_text(browser_session, 'Second Account')

    find_element_by_text(browser_session, 'Clear All Filters').click()
    assert find_element_by_text(browser_session, 'First Account', timeout=1)
    assert find_element_by_text(browser_session, 'Second Account')


DIM_INSTANCE = ('instance', 'Instance Hours')
DIM_MEMORY = ('gb', 'GB Memory Hours')
DIM_VCPU = ('cpu', 'Core Hours')


def test_graph_modes(drop_account_data, cloud_account_data,
                     browser_session, ui_acct_list):
    """Test the three "dimensions" of both RHEL and RHOCP usage.

    :id: 753b6e47-501a-4cae-af20-a8eece9ef50d
    :description: Usage of images is measured in instance hours, GB of memory
        per hour, and vCPU core per hour. RHEL graphs default to Instance
        Hours while RHOCP default to GB Memory Hours, both can be viewed for
        either.
    :steps:
        1) Look at an account with both RHEL and RHOCP usage with instances of
           different types
        2) Check the default type of each graph and that the value displayed
           matches
        3) Change each of the graphs to their two non-default types,
           confirming each
    :expectedresults:
        - RHEL and RHOCP graphs should display Instance Hours and GB Memory
          Hours, respectively
        - Each graph can be changed to one of the other dimensions without
          affecting the other
        - Navigation returns to the default for each graph
        - GB Memory Hours displayed reflect the runtime of instances
          multiplied by the number of GB of the instance type
        - Core Hours displayed reflect the runtime of instances multiplied by
          the number of cores of the instance type
    """
    cloud_account_data('rhel', [10], vcpu=2, memory=0.5)
    cloud_account_data('rhel,openshift', [5], vcpu=2, memory=0.5)
    cloud_account_data('openshift', [10], vcpu=4, memory=4)

    hours1, min1, events = get_expected_hours_in_past_30_days([10, None])
    hours2, min2, events = get_expected_hours_in_past_30_days([5, None])

    c = math.ceil

    # RHEL Hours for each "dimension"
    # image1 for 10 days + image2 for 5 days
    rhel_hours = {
        'instance': round_hours(hours1 + hours2, min1 + min2),
        'gb': round_hours(c((hours1 + hours2) / 2), c((min1 + min2) / 2)),
        'cpu': round_hours(hours1*2 + hours2*2, min1*2 + min2*2),
    }
    # RHOCP, image2 for 5 days + image3 for 10 days
    rhocp_hours = {
        'instance': round_hours(hours1 + hours2, min1 + min2),
        'gb': round_hours(c(hours1*4 + hours2/2), c(min1*4 + min2/2)),
        'cpu': round_hours(hours1*4 + hours2*2, min1*4 + min2*2),
    }

    browser_session.refresh()

    # Find the graph card based on the product header
    def graph_card(header):
        el = find_element_by_text(
            browser_session,
            header,
        )
        el = el.find_element_by_xpath('..')
        el = el.find_element_by_xpath('..')
        return el

    for tag in ('RHEL', 'RHOCP'):

        # Establish expectations based on the current product
        if tag == 'RHEL':
            header = 'Red Hat Enterprise Linux'
            hours = rhel_hours
            dimensions = (
                DIM_INSTANCE,
                DIM_MEMORY,
                DIM_VCPU,
            )
        else:
            header = 'Red Hat OpenShift Container Platform'
            hours = rhocp_hours
            dimensions = (
                DIM_VCPU,
                DIM_INSTANCE,
                DIM_MEMORY,
            )

        # Check the graphs on both the summary and detail pages
        for level in ('summary', 'detail'):

            # For detail pages, navigate to the image list for the account
            # and return back afterwards
            with return_url(browser_session):
                if level == 'detail':
                    find_element_by_text(
                        browser_session, 'First Account', timeout=1).click()
                    time.sleep(1)

                # Starting with the default dimension for this product,
                # walk through each via the dropdown menu on the appropriate
                # graph card and verify the numbers we see based on the
                # expected hours calculated above.
                for i, (dim, dropdown) in enumerate(dimensions):
                    if i > 0:
                        find_element_by_text(graph_card(header), dropdown,
                                             timeout=1).click()
                        time.sleep(0.25)

                    assert find_element_by_text(graph_card(header),
                                                f'{hours[dim]}{tag}',
                                                timeout=1)

                    find_element_by_text(graph_card(header), dropdown,
                                         timeout=1).click()


def test_account_date_filter(
    cloud_account_data, browser_session, ui_user, ui_acct_list
):
    """The date dropdown should select and filter by previous months.

    :id: 4eacca3e-c1a1-4de1-a874-bf730cd5596b
    :description: The default date filter of "Last 30 Days" is a dropdown that
        lists the 12 previous months, each of which can be selected to filter
        the account summary list to results from that month.
    :steps:
        1) Create a cloud account with images and instances that ran for 1 day
           in a previous month on a day that is not within the last 30 days.
        2) Confirm these do not show up in the default 30 days filter.
        3) Click the dropdown and select the month in which the events were
           created.
        4) Confirm the account list now reflects the appropriate counts.
    :expectedresults:
        The counts shown in the account summary should reflect images and
        instances as they were counted within the time frame of the selected
        date filter.
    """
    day = datetime.timedelta(days=1)
    first = datetime.date.today().replace(day=1)
    end_of_last = first - day
    start_of_last = end_of_last.replace(day=1)
    end_of_two_months_ago = start_of_last - day
    start = end_of_two_months_ago.replace(day=1)
    end = start + datetime.timedelta(days=1)
    month_label = start.strftime('%Y %B')

    for i in range(3):
        cloud_account_data('', [start, end], ec2_ami_id='image2')

    browser_session.refresh()

    assert find_element_by_text(browser_session, '0 Images', timeout=1)
    assert find_element_by_text(browser_session, '0 Instances')

    find_element_by_text(browser_session, 'Last 30 Days').click()
    find_element_by_text(browser_session, month_label, timeout=0.25).click()

    assert find_element_by_text(browser_session, '1 Images', timeout=1)
    assert find_element_by_text(browser_session, '3 Instances')

    long_ago = datetime.date.today() - datetime.timedelta(days=180)
    long_ago_label = long_ago.strftime('%Y %B')
    find_element_by_text(browser_session, month_label).click()
    find_element_by_text(browser_session, long_ago_label).click()

    assert find_element_by_text(browser_session, 'N/A Images', timeout=1)
    assert find_element_by_text(browser_session, 'N/A Instances')
    # No spaces because there are not spaces between the DOM nodes, even tho
    # they are rendered separately.
    assert find_element_by_text(browser_session, 'N/ARHEL')
    assert find_element_by_text(browser_session, 'N/ARHOCP')


def test_summary_cards(cloud_account_data, browser_session, ui_acct_list):
    """Ensure the summary cards provide the summary usage information.

    :id: 53aeef62-79a8-4576-8cc5-b9dcc66d61b8
    :description: Test that the summary cards on the top of the accounts page
        show the summary usage information. The usage information must be the
        usage on the selected month and should only include RHEL and/or
        OpenShift usage.
    :steps:
        1) Create a cloud account with images and instances that ran across 3
           different months: 2 months ago, 1 month ago and the current month.
           Make sure to include usage from non RHEL and OpenShift, that should
           not be shown on the report.
        2) Select the past month as the usage period. Confirm the usage is
           reported as expected.
        3) Do the same for 2 months ago as the usage period. Confirm the usage
           is reported as expected.
        4) Click on summary row. Confirm that RHEL and RHOCP hours are as
           expected.
    :expectedresults:
        The usage report should count only RHEL and OpenShift hours. Any usage
        from a non RHEL or OpenShift image should not be considered.
    """
    now = utils.utc_now()
    one_month = relativedelta(months=1)
    last_month = now - one_month
    month_after = last_month + one_month
    month_before = last_month - one_month
    last_day = utils.days_in_month(last_month.year, last_month.month)
    rhel_runtime = 0
    openshift_runtime = 0
    plain_ami_id = str(random.randint(100000, 999999999999))
    rhel_ami_id = str(random.randint(100000, 999999999999))
    openshift_ami_id = str(random.randint(100000, 999999999999))
    rhel_openshift_ami_id = str(random.randint(100000, 999999999999))

    cloud_account_data(
        '',
        [
            utils.utc_dt(2018, last_month.month, 9, 3, 0, 0),
            utils.utc_dt(2018, last_month.month, 11, 3, 0, 0),
        ],
        ec2_ami_id=plain_ami_id,
    )

    usage = [
        utils.utc_dt(2018, last_month.month, 11, 7, 0, 0),
        utils.utc_dt(2018, last_month.month, 13, 5, 0, 0),
    ]
    cloud_account_data('openshift', usage, ec2_ami_id=openshift_ami_id)
    openshift_runtime += sum_usage(usage)

    usage = [
        utils.utc_dt(2018, last_month.month, 1, 4, 0, 0),
        utils.utc_dt(2018, last_month.month, last_day, 21, 0, 0),
    ]
    cloud_account_data('openshift', usage, ec2_ami_id=openshift_ami_id)
    openshift_runtime += sum_usage(usage)

    usage = [
        utils.utc_dt(month_before.year, month_before.month, 22, 3, 0, 0),
        utils.utc_dt(month_before.year, month_before.month, 27, 3, 0, 0),
        utils.utc_dt(2018, last_month.month, 8, 5, 0, 0),
        utils.utc_dt(2018, last_month.month, 10, 5, 0, 0),
        utils.utc_dt(2018, last_month.month, 11, 5, 0, 0),
        utils.utc_dt(2018, last_month.month, 11, 6, 0, 0),
        utils.utc_dt(2018, last_month.month, 11, 7, 0, 0),
        utils.utc_dt(2018, last_month.month, 11, 8, 0, 0),
        utils.utc_dt(2018, last_month.month, 11, 9, 0, 0),
        utils.utc_dt(2018, last_month.month, 11, 10, 0, 0),
        utils.utc_dt(month_after.year, month_after.month, 20, 5, 0, 0),
        utils.utc_dt(month_after.year, month_after.month, 23, 5, 0, 0),
    ]
    cloud_account_data('rhel', usage, ec2_ami_id=rhel_ami_id)
    rhel_runtime += sum_usage(usage[2:10])

    _, last_day = calendar.monthrange(2018, last_month.month)
    usage = [
        utils.utc_dt(2018, last_month.month, last_day, 5, 0, 0),
        utils.utc_dt(2018, last_month.month, last_day, 6, 0, 0),
        utils.utc_dt(2018, last_month.month, last_day, 7, 0, 0),
        utils.utc_dt(2018, last_month.month, last_day, 8, 0, 0),
        utils.utc_dt(2018, last_month.month, last_day, 9, 0, 0),
        utils.utc_dt(2018, last_month.month, last_day, 10, 0, 0),
    ]
    cloud_account_data('rhel', usage, ec2_ami_id=rhel_ami_id)
    rhel_runtime += sum_usage(usage)

    usage = [
        utils.utc_dt(2018, last_month.month, 12, 0, 0, 0),
        utils.utc_dt(2018, last_month.month, 12, 6, 0, 0),
        utils.utc_dt(2018, last_month.month, 12, 7, 0, 0),
        utils.utc_dt(2018, last_month.month, 12, 8, 0, 0),
        utils.utc_dt(2018, last_month.month, 12, 9, 0, 0),
        utils.utc_dt(2018, last_month.month, 12, 23, 0, 0),
    ]
    cloud_account_data('rhel', usage, ec2_ami_id=rhel_ami_id)
    rhel_runtime += sum_usage(usage)

    usage = [
        utils.utc_dt(2018, last_month.month, 9, 9, 0, 0),
        utils.utc_dt(2018, last_month.month, 14, 9, 0, 0),
    ]
    cloud_account_data(
        'rhel,openshift', usage, ec2_ami_id=rhel_openshift_ami_id)
    openshift_runtime += sum_usage(usage)
    rhel_runtime += sum_usage(usage)

    browser_session.refresh()

    # Convert runtime from seconds to hours
    rhel_runtime = int(rhel_runtime / 3600)
    openshift_runtime = int(openshift_runtime / 3600)

    month_label = last_month.strftime('%Y %B')
    find_element_by_text(browser_session, 'Last 30 Days', timeout=2).click()
    find_element_by_text(browser_session, month_label, timeout=1).click()
    time.sleep(1)
    summary_row = retry_w_timeout(
        1,
        browser_session.find_elements_by_css_selector,
        '.cloudmeter-list-view-card'
        )
    cards = browser_session.find_elements_by_css_selector(
        '.cloudmeter-utilization-graph'
        )
    assert len(cards) == 2
    assert element_has_text(cards[0], f'{rhel_runtime} RHEL')
    assert element_has_text(cards[1], f'{openshift_runtime} RHOCP')
    assert element_has_text(summary_row[0], '4 Images')
    assert element_has_text(summary_row[0], '7 Instances')
    assert element_has_text(summary_row[0], f'{rhel_runtime} RHEL')
    assert element_has_text(summary_row[0], f'{openshift_runtime} RHOCP')
    month_before_label = month_before.strftime('%Y %B')
    find_element_by_text(browser_session, month_label).click()
    find_element_by_text(browser_session, month_before_label,
                         timeout=0.25).click()
    assert page_has_text(browser_session, '120 RHEL')
    assert page_has_text(browser_session, '0 RHOCP')
    assert page_has_text(browser_session, '1 Images')
    assert page_has_text(browser_session, '1 Instances')
    info_bar = browser_session.find_element_by_css_selector(
        '.cloudmeter-list-view-card .list-group-item-heading'
        )
    info_bar.click()
    cards = browser_session.find_elements_by_css_selector(
        '.cloudmeter-utilization-graph'
        )

    assert page_has_text(browser_session, '120 RHEL')
    assert page_has_text(browser_session, '0 RHOCP')
