import requests
import json
import re

class vco_client():
    def __init__(self, hostname, verify_ssl=True):
        '''
        Initiate the Session object, the HTTP headers,
        the paths and all the associated parameters.
        '''
        self.session = requests.Session()
        self.hostname = self._hostname_https(hostname)
        self.headers = { 'Content-Type': 'application/json' }
        self.verify_ssl = verify_ssl
        self.seq = 0

    def _hostname_https(self, hostname):
        '''
        Change the scheme to HTTPS if it is not already by
        regular expression operation for a secure connection
        '''
        if hostname.startswith('http'):
            re.sub('http(s)?://', '', hostname)
        https = 'https://'

        return https + hostname

    def token_auth(self, token):
        '''
        Update the HTTP headers with the given API token
        '''
        self.headers.update( { 'Authorization': 'Token ' + token })

    def cookies_auth(self, username, password, is_operator=False):
        '''
        Authenticate with the given username and password, and
        store the cookies in the Session object authentication on success.
        '''
        self.seq += 1

        if is_operator:
            url = self.hostname + '/login/operatorLogin'
        else:
            url = self.hostname + '/login/enterpriseLogin'

        payload = { 'username': username, 'password': password }

        call = self.session.post(url, headers=self.headers,
            data=json.dumps(payload), allow_redirects=False,
            verify=self.verify_ssl)

        try:
            self.session.cookies.get_dict()['velocloud.session']
        except KeyError:
            # Raise a system exit on error authenticating
            try:
                message = str.replace(self.session.cookies.get_dict(
                    )['velocloud.message'], '%20', ' ')
            except KeyError:
                message = 'Error authenticating'
            finally:
                raise SystemExit(message)

    def call_api(self, path, parameters):
        '''
        Call the given path with the given parameters
        '''
        self.seq += 1
        path = path.strip('/')
        payload = { 'jsonrpc': '2.0',
                    'id': self.seq,
                    'method': path,
                    'params': parameters }

        if path in ('liveMode/readLiveData',
        'liveMode/requestLiveActions', 'liveMode/clientExitLiveMode'):
            # Use the livepull path instead should the call require live mode
            url = self.hostname + '/livepull/liveData/'
        else:
            # Otherwise use the portal path
            url = self.hostname + '/portal/'

        call = self.session.post(url, headers=self.headers,
            data=json.dumps(payload), verify=self.verify_ssl)

        response = call.json()

        if 'error' in response:
            # Raise a system exit on call error
            raise SystemExit(response['error']['message'])

        if response:
            return response['result']
        else:
            # Raise a system exit on empty response
            raise SystemExit('Call returns empty')
