# -*- coding: utf-8 -*-
"""Tests for the Digital Marketplace MailChimp integration."""
import mock

from dmutils.email.dm_mailchimp import DMMailChimpClient
from requests import RequestException


def test_create_campaign():
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', 'logger')
    with mock.patch.object(dm_mailchimp_client.client.campaigns, 'create', autospec=True) as create:
        create.return_value = {"id": "100"}
        res = dm_mailchimp_client.create_campaign({"example": "data"})

        assert res == "100"
        create.assert_called_once_with({"example": "data"})


def test_log_error_message_if_error_creating_campaign():
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(dm_mailchimp_client.client.campaigns, 'create', autospec=True) as create:
        create.side_effect = RequestException("error message")
        with mock.patch.object(dm_mailchimp_client.logger, 'error', autospec=True) as error:
            res = dm_mailchimp_client.create_campaign({"example": "data", 'settings': {'title': 'Foo'}})

            assert res is False
            error.assert_called_once_with(
                "Mailchimp failed to create campaign for 'campaign title'", extra={"error": "error message"}
            )


def test_set_campaign_content():
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', 'logger')
    with mock.patch.object(dm_mailchimp_client.client.campaigns.content, 'update', autospec=True) as update:
        campaign_id = '1'
        html_content = {'html': '<p>One or two words</p>'}
        update.return_value = html_content
        res = dm_mailchimp_client.set_campaign_content(campaign_id, html_content)

        assert res == html_content
        dm_mailchimp_client.client.campaigns.content.update.assert_called_once_with(campaign_id, html_content)


def test_log_error_message_if_error_setting_campaign_content():
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(dm_mailchimp_client.client.campaigns.content, 'update', autospec=True) as update:
        update.side_effect = RequestException("error message")

        with mock.patch.object(dm_mailchimp_client.logger, 'error', autospec=True) as error:
            res = dm_mailchimp_client.set_campaign_content('1', {"html": "some html"})

            assert res is False
            error.assert_called_once_with(
                "Mailchimp failed to set content for campaign id '1'", extra={"error": "error message"}
            )


def test_send_campaign():
    campaign_id = "1"
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(dm_mailchimp_client.client.campaigns.actions, 'send', autospec=True) as send:
        res = dm_mailchimp_client.send_campaign(campaign_id)

        assert res is True
        send.assert_called_once_with(campaign_id)


def test_log_error_message_if_error_sending_campaign():
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(dm_mailchimp_client.client.campaigns.actions, 'send',  autospec=True) as send:
        send.side_effect = RequestException("error sending")
        with mock.patch.object(dm_mailchimp_client.logger, 'error', autospec=True) as error:
            res = dm_mailchimp_client.send_campaign("1")

            assert res is False
            error.assert_called_once_with(
                "Mailchimp failed to send campaign id '1'", extra={"error": "error sending"}
            )


@mock.patch("dmutils.email.dm_mailchimp.DMMailChimpClient.get_email_hash", return_value="foo")
def test_subscribe_email_to_list(get_email_hash):
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(
            dm_mailchimp_client.client.lists.members, 'create_or_update', autospec=True) as create_or_update:

        create_or_update.return_value = {"response": "data"}
        res = dm_mailchimp_client.subscribe_email_to_list('list_id', 'example@example.com')

        assert res == {"response": "data"}
        create_or_update.assert_called_once_with(
            'list_id',
            "foo",
            {
                "email_address": "example@example.com",
                "status_if_new": "subscribed"
            }
        )


@mock.patch("dmutils.email.dm_mailchimp.DMMailChimpClient.get_email_hash", return_value="foo")
def test_log_error_message_if_error_subscribing_email_to_list(get_email_hash):
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(
            dm_mailchimp_client.client.lists.members, 'create_or_update',  autospec=True) as create_or_update:
        create_or_update.side_effect = RequestException("error sending")
        with mock.patch.object(dm_mailchimp_client.logger, 'error', autospec=True) as error:
            res = dm_mailchimp_client.subscribe_email_to_list('list_id', 'example@example.com')

            assert res is False
            error.assert_called_once_with(
                "Mailchimp failed to add user ({}) to list ({})".format(
                    'foo',
                    'list_id'
                ),
                extra={"error": "error sending"}
            )


def test_subscribe_new_emails_to_list():
    dm_mailchimp_client = DMMailChimpClient('username', 'api key', mock.MagicMock())
    with mock.patch.object(dm_mailchimp_client, 'subscribe_email_to_list',  autospec=True):
        res = dm_mailchimp_client.subscribe_new_emails_to_list('list_id', ['email1@example.com', 'email2@example.com'])

        assert res is True
        calls = [mock.call('list_id', 'email1@example.com'), mock.call('list_id', 'email2@example.com')]
        dm_mailchimp_client.subscribe_email_to_list.assert_has_calls(calls)


def test_get_email_hash():
    assert DMMailChimpClient.get_email_hash("example@example.com") == '23463b99b62a72f26ed677cc556c44e8'


def test_get_email_hash_lowers():
    """Email must be lowercased before hashing as per api documentation."""
    DMMailChimpClient.get_email_hash("foo@EXAMPLE.com") == DMMailChimpClient.get_email_hash("foo@example.com")
