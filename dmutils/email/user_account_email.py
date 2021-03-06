from flask import current_app, session, abort, url_for
from . import DMNotifyClient, generate_token, EmailError
from .helpers import hash_string


def send_user_account_email(role, email_address, template_id, extra_token_data={}, personalisation={}):
    notify_client = DMNotifyClient(current_app.config['DM_NOTIFY_API_KEY'])

    token_data = {
        'role': role,
        'email_address': email_address
    }
    token_data.update(extra_token_data)

    token = generate_token(
        token_data,
        current_app.config['SHARED_EMAIL_KEY'],
        current_app.config['INVITE_EMAIL_SALT']
    )

    link_url = url_for('external.create_user', encoded_token=token, _external=True)

    personalisation_with_link = personalisation.copy()
    personalisation_with_link.update({'url': link_url})

    try:
        notify_client.send_email(
            email_address,
            template_id=template_id,
            personalisation=personalisation_with_link,
            reference='create-user-account-{}'.format(hash_string(email_address))
        )
        session['email_sent_to'] = email_address
    except EmailError as e:
        current_app.logger.error(
            "{code}: Create user email for email_hash {email_hash} failed to send. Error: {error}",
            extra={
                'error': str(e),
                'email_hash': hash_string(email_address),
                'code': '{}create.fail'.format(role)
            })
        abort(503, response="Failed to send user creation email.")
