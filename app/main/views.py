
from __future__ import print_function
import os.path
import random
import requests
import threading
import logging
from queue import Queue
from urllib.parse import urlparse
from httplib2 import Http
from timeit import default_timer as timer
from concurrent import futures
from flask import render_template, url_for, send_from_directory, request, make_response, session, redirect, jsonify, Markup
from app import app
from app.models import Post, PostType
from . import main
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import build_http 
import google_auth_oauthlib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

mail_req_q = Queue()
mailbox_mails = list()

@main.route("/", methods=["GET", "POST"])
def index():
    app.logger.info('Hello tactification.com')
    posts = (
        Post.query.order_by(Post.timestamp.desc())
        .filter_by(post_type=PostType.POSTER)
        .all()
    )
    if post is None:
        return render_template("error.html", "Posters not present")

    return render_template("index.html", posts=posts)


@main.route("/post/<int:id>/<string:header>", methods=["GET", "POST"])
def post(id, header):
    if id < 0:
        return render_template("error.html", "Post not present")

    page = Post.query.get_or_404(id)
    if page is None:
        return render_template("error.html", "Post {:s} not present".format(id))

    #Making body markup safe using Markup class from flask.
    markup = Markup(page.body)
    return render_template("post.html", post=page, markup=markup)

@main.route("/download_file/<int:id>/<filename>", methods=["GET"])
def download_file(id, filename):
    directory = "{:s}".format(app.config["UPLOAD_FOLDER"])
    logging.info('path: {:s} filename: {:s}'.format(directory, filename))
    return send_from_directory(directory, filename)


@main.route("/sitemap")
@main.route("/sitemap/")
@main.route("/sitemap.xml")
def sitemap():
    """
    Route to dynamically generate a sitemap of your website/application.
    lastmod and priority tags omitted on static pages.
    lastmod included on dynamic content such as blog posts.
    """
    host_components = urlparse(request.host_url)
    host_base = host_components.scheme + "://" + host_components.netloc

    static_url_list = {"home": "main.index"}
    # Static routes with static content
    static_urls = list()
    for key, value in static_url_list.items():
        print("rule:", key, value)
        url = {"loc": "{}/{}".format(host_base, url_for(value))}
        static_urls.append(url)

    # Dynamic routes with dynamic content
    dynamic_urls = list()
    blog_posts = Post.query.all()
    for post in blog_posts:
        url_ext = url_for("main.post", id=post.id, header=post.header)

        url = {
            "loc": "{}/{}".format(host_base, url_ext),
            "lastmod": post.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        dynamic_urls.append(url)

    xml_sitemap = render_template(
        "sitemap.xml",
        static_urls=static_urls,
        dynamic_urls=dynamic_urls,
        host_base=host_base,
    )
    response = make_response(xml_sitemap)
    response.headers["Content-Type"] = "application/xml"

    return response

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
CLIENT_SECRETS_FILE = "/var/www/gmail/client_secret.json"

# If modifying these scopes, delete the file token.json.
SCOPES = {
          'readonly':'https://www.googleapis.com/auth/gmail.readonly',
          'labels':'https://www.googleapis.com/auth/gmail.labels',
          'send':'https://www.googleapis.com/auth/gmail.send',
          'compose':'https://www.googleapis.com/auth/gmail.compose',
          'insert':'https://www.googleapis.com/auth/gmail.insert',
          'modify':'https://www.googleapis.com/auth/gmail.modify',
          'metadata':'https://www.googleapis.com/auth/gmail.metadata',
          'basic':'https://www.googleapis.com/auth/gmail.settings.basic',
          'sharing':'https://www.googleapis.com/auth/gmail.settings.sharing',
          'full':'https://mail.google.com/'
         }

@main.route("/print_index_table")
def print_index_table():
  return ('<table>' +
          '<tr><td><a href="/test">Test an API request</a></td>' +
          '<td>Submit an API request and see a formatted JSON response. ' +
          '    Go through the authorization flow if there are no stored ' +
          '    credentials for the user.</td></tr>' +
          '<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
          '<td>Go directly to the authorization flow. If there are stored ' +
          '    credentials, you still might not be prompted to reauthorize ' +
          '    the application.</td></tr>' +
          '<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
          '<td>Revoke the access token associated with the current user ' +
          '    session. After revoking credentials, if you go to the test ' +
          '    page, you should see an <code>invalid_grant</code> error.' +
          '</td></tr>' +
          '<tr><td><a href="/getprofile">get current profile</a></td>' +
          '<td>Get the users current profile</td>' +
          '</td></tr>' +
          '<tr><td><a href="/listmessages">get list of all messages</a></td>' +
          '<td>Dump list of all messages</td>' +
          '</td></tr>' +
          '<tr><td><a href="/listheaders">get list of all message headers</a></td>' +
          '<td>Dump list of all messages</td>' +
          '</td></tr>' +
          '<tr><td><a href="/getmessage">get contents of a message</a></td>' +
          '<td>Dump details of a messages</td>' +
          '</td></tr>' +
          '<tr><td><a href="/getimap">get account imap details</a></td>' +
          '<td>Imap details of account</td>' +
          '</td></tr>' +
          '<tr><td><a href="/getpop">get account pop details</a></td>' +
          '<td>Pop details of account</td>' +
          '</td></tr>' +
          '<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
          '<td>Clear the access token currently stored in the user session. ' +
          '    After clearing the token, if you <a href="/test">test the ' +
          '    API request</a> again, you should go back to the auth flow.' +
          '</td></tr></table>')

@main.route("/test")
def test_api_request():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        service = build('gmail', 'v1', credentials=credentials)
        app.logger.info(dir(service))
        app.logger.info(dir(service.users().getProfile))

        results=service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            app.logger.info('No labels found')
            return 'No labels found'

        app.logger.info('Labels')
        for label in labels:
            app.logger.info(label['name'])

        session['credentials'] = credentials_to_dict(credentials)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error) 

    return jsonify(labels)

@main.route('/getimap')
def getimap():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])
    
    try:
        service = build('gmail', 'v1', credentials=credentials)
        results = service.users().settings().getImap(userId='me').execute()
        app.logger.info(dir(results))
        app.logger.info(type(results))
        app.logger.info(results)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    return jsonify(results)

@main.route('/getpop')
def getpop():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])
    
    try:
        service = build('gmail', 'v1', credentials=credentials)
        results = service.users().settings().getPop(userId='me').execute()
        app.logger.info(dir(results))
        app.logger.info(type(results))
        app.logger.info(results)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    return jsonify(results)

@main.route('/getprofile')
def getprofile():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        service = build('gmail', 'v1', credentials=credentials)

        results=service.users().getProfile(userId='me').execute()
    
        app.logger.info(dir(service.users()))
        app.logger.info(dir(results))
        if not results:
            app.logger.info('No results found')
            return 'No results found'

        session['credentials'] = credentials_to_dict(credentials)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error) 

    return jsonify(results)

@main.route('/getmessage')
def getmessage():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        message_list = list()
        i = 0
        service = build('gmail', 'v1', credentials=credentials)

        results=service.users().messages().list(userId='me').execute()
        message_list.append(results['messages'])
        app.logger.info(results['nextPageToken'])

        while results['nextPageToken'] and i < 10:
            results=service.users().messages().list(userId='me', pageToken=results['nextPageToken']).execute()
            app.logger.info(results['nextPageToken'])
            message_list.append(results['messages'])
            i = i+1

        session['credentials'] = credentials_to_dict(credentials)

    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error) 

    message_id = random.randrange(0, len(message_list))
    app.logger.info(message_id)
    app.logger.info(message_list[0][message_id])
    try:
        result=service.users().messages().get(userId='me', id=message_list[0][message_id]['id'], format='full').execute()
        app.logger.info(type(result))
        app.logger.info(result)

    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    return jsonify(result)

@main.route('/get_a_message/<message_id>')
def get_a_message(message_id):
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        service = build('gmail', 'v1', credentials=credentials)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    try:
        request=service.users().messages().get(userId='me', id=message_id, format='full')
        app.logger.info(request.to_json())
        result=service.users().messages().get(userId='me', id=message_id, format='full').execute()

    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    return jsonify(result)

@main.route('/delete_a_message/<message_id>')
def delete_a_message(message_id):
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect(url_for('main.authorize', _external=True))

    if session['scope'] != 'full':
        session['scope'] = 'full'
        return redirect(url_for('main.authorize', _external=True))

    credentials = Credentials(**session['credentials'])

    try:
        service = build('gmail', 'v1', credentials=credentials)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    try:
        result=service.users().messages().delete(userId='me', id=message_id).execute()
        app.logger.info(type(result))
        app.logger.info(result)
    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error)

    return jsonify(result)

def get_mail_blocks(credentials):
    t0 = timer()
    message_list = list()
    count = 0
    try:
        service = build('gmail', 'v1', credentials=credentials)
        results = service.users().messages().list(userId='me').execute()

        count += 1
        while results['nextPageToken']:
            results = service.users().messages().list(userId='me', 
                                                      pageToken=results['nextPageToken']).execute()
            message_list.append(results['messages'])
            count += 1
            if count == 50:
                break

    except HttpError as error:
        app.logger.error('An error occured:', error)
        return
    except KeyError as error:
        app.logger.error('nextPageToken KeyError:')
        pass 

    elapsed = timer() - t0
    app.logger.info('count {} elapsed time {:.2f}s'.format(count, elapsed))
    t0 = timer()
    results = download_mail(message_list, credentials)
    elapsed = timer() - t0
    app.logger.info('full mails count {} elapsed time {:.2f}s'.format(results, elapsed))
    return

@main.route('/listmessages')
def listmessages():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        message_list = list()
        i = 0
        service = build('gmail', 'v1', credentials=credentials)

        results=service.users().messages().list(userId='me').execute()
        message_list.append(results['messages'])
        app.logger.info(results['nextPageToken'])

        while results['nextPageToken'] and i < 10:
            results=service.users().messages().list(userId='me', pageToken=results['nextPageToken']).execute()
            app.logger.info(results['nextPageToken'])
            app.logger.info(len(results['messages']))
            message_list.append(results['messages'])
            i = i+1

        session['credentials'] = credentials_to_dict(credentials)

    except HttpError as error:
        app.logger.error('An error occured: {:s}'.format(error))
        return 'An error occured: {:s}'.format(error) 

    return jsonify(message_list)

@main.route('/listheaders')
def listheaders():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        message_list = list()
        service = build('gmail', 'v1', credentials=credentials)

        results=service.users().messages().list(userId='me').execute()
        message_list.append(results['messages'])
        app.logger.info(results['nextPageToken'])

        while results['nextPageToken']:
            results=service.users().messages().list(userId='me', pageToken=results['nextPageToken']).execute()
            app.logger.info(results['nextPageToken'])
            message_list.append(results['messages'])

        session['credentials'] = credentials_to_dict(credentials)

    except HttpError as error:
        app.logger.error('An error occured: ',error)
        return 'An error occured: '

    except KeyError as error:
        app.logger.error('An error occured: ',error)
        return 'An error occured: '

    return jsonify(message_list)

def download_mail_block(*args, **kwargs):
    count = 0
    t0 = timer()

    mail_block = args[0]
    credentials = args[1]
    mail_id_list = list()

    try:
        service = build('gmail', 'v1', credentials=credentials)
    except HttpError as error:
        app.logger.error('build error {!r}'.format(error))
        return

    batch = service.new_batch_http_request()
    headers = ['List-Unsubscribe','Subject','Date', 'Return-Path']
    for mail in mail_block:
        batch.add(service.users().messages().get(userId='me', id=mail['id'], format='metadata',
                                                 metadataHeaders=headers), 
                  callback=download_mail_batch_cb)
        mail_id_list.append(mail['id'])

    app.logger.info('service dict:', service.__dict__)
    batch.execute(http=service._http)

    elapsed = timer() - t0
    app.logger.info('mail block count {} elapsed time {:.2f}s'.format(count, elapsed))
    return

def download_mail(mail_block_list, credentials):
    with futures.ThreadPoolExecutor(max_workers=1) as executor:
        mail_list_futures = []
        for count, mail in enumerate(mail_block_list):
            f = executor.submit(download_mail_block, mail, credentials)
            mail_list_futures.append(f)
            msg = 'Scheduled for list number {}'
            app.logger.info(msg.format(count))

        results = []
        for future in futures.as_completed(mail_list_futures):
            res = future.result()
            msg = '{} result: {!r}'
            app.logger.info(msg.format(future, res))
            results.append(res)

    return len(results)

def download_mail_batch_cb(request_id, response, exception):
    if exception is not None:
        app.logger.info('request_id: {}',exception)
        return
    else:
        app.logger.info('request_id: {}'.format(request_id))
        if isinstance(response, dict):
            for message in response.items():
                if len(message) == 0 or isinstance(message, tuple) is False:
                    continue

                if message[0] != 'payload':
                    continue

                metadata = message[1].get('headers', 'None')
                for data in metadata:
                    if data['name'] == 'List-Unsubscribe':
                        app.logger.info(data['value']) 
    return

def mail_q_handler():
    while True:
        app.logger.info('working started')
        item = mail_req_q.get()
        get_mail_blocks(item)

@main.route('/get_inbox')
def get_inbox():
    if 'credentials' not in session:
        session['scope'] = 'readonly'
        return redirect('authorize')

    credentials = Credentials(**session['credentials'])

    try:
        service = build('gmail', 'v1', credentials=credentials)
        results = service.users().getProfile(userId='me').execute()

        app.logger.info('Threading started')
        threading.Thread(target=mail_q_handler, daemon=True).start()

        app.logger.info('inserting to queue')
        mail_req_q.put(credentials, block=False)
    except HttpError as error:
        app.logger.error('An error occured:', error)
        return 'An error occured in getting profile'

    return jsonify(results)

@main.route('/authorize')
def authorize():
    scope = session['scope']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES[scope]) 
   
    flow.redirect_uri = url_for('main.oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(access_type='offline',
                                                      include_granted_scopes='true')

    session['state'] = state
    app.logger.info('state: {:s} url: {:s}'.format(state, authorization_url))

    return redirect(authorization_url)

@main.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    scope = session['scope']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, 
                                                                   scopes=SCOPES[scope], state=state)
    flow.redirect_uri = url_for('main.oauth2callback', _external=True)

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('main.test_api_request'))

@main.route('/revoke')
def revoke():
    if 'credentials' not in session:
        return ('you need to <a href="/authorize">authorize</a> before ' +
                'testing the code to revoke credentials.')

    credentials = Credentials(**session['credentials'])

    revoke = requests.post('https://oauth2.googleapis.com/revoke',
                           params={'token': credentials.token},
                           headers = {'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        return ('Credentials successfully revoked.' + url_for('main.print_index_table', _external=True))
    else:
        return ('An error occured.' + url_for('main.print_index_table', _external=True))

@main.route('/clear')
def clear_credentials():
    if 'credentials' in session:
        del session['credentials']
        del session['scope']
    return ('Credentials have been cleared.<br><br>' + url_for('main.print_index_table', _external=True))

def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}
