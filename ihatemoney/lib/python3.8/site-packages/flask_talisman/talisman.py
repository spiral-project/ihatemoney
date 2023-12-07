# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from collections import OrderedDict

import flask


DENY = 'DENY'
SAMEORIGIN = 'SAMEORIGIN'
ALLOW_FROM = 'ALLOW-FROM'
ONE_YEAR_IN_SECS = 31556926

DEFAULT_REFERRER_POLICY = 'strict-origin-when-cross-origin'

DEFAULT_CSP_POLICY = {
    'default-src': '\'self\'',
    'object-src': '\'none\'',
}

DEFAULT_SESSION_COOKIE_SAMESITE = "Lax"

GOOGLE_CSP_POLICY = {
    # Fonts from fonts.google.com
    'font-src': '\'self\' themes.googleusercontent.com *.gstatic.com',
    # <iframe> based embedding for Maps and Youtube.
    'frame-src': '\'self\' www.google.com www.youtube.com',
    # Assorted Google-hosted Libraries/APIs.
    'script-src': '\'self\' ajax.googleapis.com *.googleanalytics.com '
                  '*.google-analytics.com',
    # Used by generated code from http://www.google.com/fonts
    'style-src': '\'self\' ajax.googleapis.com fonts.googleapis.com '
                 '*.gstatic.com',
    'object-src': '\'none\'',
    'default-src': '\'self\' *.gstatic.com',
}

DEFAULT_PERMISSIONS_POLICY = {
    # Disable Topics API
    'browsing-topics': '()'
}

DEFAULT_DOCUMENT_POLICY = {
}

DEFAULT_FEATURE_POLICY = {
}

NONCE_LENGTH = 32


class Talisman(object):
    """
    Talisman is a Flask extension for HTTP security headers.
    """

    def __init__(self, app=None, **kwargs):
        if app is not None:
            self.init_app(app, **kwargs)

    def init_app(
            self,
            app,
            feature_policy=DEFAULT_FEATURE_POLICY,
            permissions_policy=DEFAULT_PERMISSIONS_POLICY,
            document_policy=DEFAULT_DOCUMENT_POLICY,
            force_https=True,
            force_https_permanent=False,
            force_file_save=False,
            frame_options=SAMEORIGIN,
            frame_options_allow_from=None,
            strict_transport_security=True,
            strict_transport_security_preload=False,
            strict_transport_security_max_age=ONE_YEAR_IN_SECS,
            strict_transport_security_include_subdomains=True,
            content_security_policy=DEFAULT_CSP_POLICY,
            content_security_policy_report_uri=None,
            content_security_policy_report_only=False,
            content_security_policy_nonce_in=None,
            referrer_policy=DEFAULT_REFERRER_POLICY,
            session_cookie_secure=True,
            session_cookie_http_only=True,
            session_cookie_samesite=DEFAULT_SESSION_COOKIE_SAMESITE,
            x_content_type_options=True,
            x_xss_protection=False):
        """
        Initialization.

        Args:
            app: A Flask application.
            feature_policy: A string or dictionary describing the
                feature policy for the response.
            permissions_policy: A string or dictionary describing the
                permissions policy for the response.
            document_policy: A string or dictionary describing the
                document policy for the response.
            force_https: Redirects non-http requests to https, disabled in
                debug mode.
            force_https_permanent: Uses 301 instead of 302 redirects.
            frame_options: Sets the X-Frame-Options header, defaults to
                SAMEORIGIN.
            frame_options_allow_from: Used when frame_options is set to
                ALLOW_FROM and is a string of domains to allow frame embedding.
            strict_transport_security: Sets HSTS headers.
            strict_transport_security_preload: Enables HSTS preload. See
                https://hstspreload.org.
            strict_transport_security_max_age: How long HSTS headers are
                honored by the browser.
            strict_transport_security_include_subdomains: Whether to include
                all subdomains when setting HSTS.
            content_security_policy: A string or dictionary describing the
                content security policy for the response.
            content_security_policy_report_uri: A string indicating the report
                URI used for CSP violation reports
            content_security_policy_report_only: Whether to set the CSP header
                as "report-only", which disables the enforcement by the browser
                and requires a "report-uri" parameter with a backend to receive
                the POST data
            content_security_policy_nonce_in: A list of csp sections to include
                a per-request nonce value in
            referrer_policy: A string describing the referrer policy for the
                response.
            session_cookie_secure: Forces the session cookie to only be sent
                over https. Disabled in debug mode.
            session_cookie_http_only: Prevents JavaScript from reading the
                session cookie.
            session_cookie_samesite: Sets samesite parameter on session cookie
            force_file_save: Prevents the user from opening a file download
                directly on >= IE 8
            x_content_type_options: Prevents MIME type sniffing
            x_xss_protection: Prevents the page from loading when the browser
                detects reflected cross-site scripting attacks

        See README.rst for a detailed description of each option.
        """
        if isinstance(feature_policy, dict):
            self.feature_policy = OrderedDict(feature_policy)
        else:
            self.feature_policy = feature_policy

        if isinstance(permissions_policy, dict):
            self.permissions_policy = OrderedDict(permissions_policy)
        else:
            self.permissions_policy = permissions_policy

        if isinstance(document_policy, dict):
            self.document_policy = OrderedDict(document_policy)
        else:
            self.document_policy = document_policy

        self.force_https = force_https
        self.force_https_permanent = force_https_permanent

        self.frame_options = frame_options
        self.frame_options_allow_from = frame_options_allow_from

        self.strict_transport_security = strict_transport_security
        self.strict_transport_security_preload = \
            strict_transport_security_preload
        self.strict_transport_security_max_age = \
            strict_transport_security_max_age
        self.strict_transport_security_include_subdomains = \
            strict_transport_security_include_subdomains

        if isinstance(content_security_policy, dict):
            self.content_security_policy = OrderedDict(content_security_policy)
        else:
            self.content_security_policy = content_security_policy
        self.content_security_policy_report_uri = \
            content_security_policy_report_uri
        self.content_security_policy_report_only = \
            content_security_policy_report_only
        if self.content_security_policy_report_only and \
                self.content_security_policy_report_uri is None:
            raise ValueError(
                'Setting content_security_policy_report_only to True also '
                'requires a URI to be specified in '
                'content_security_policy_report_uri')
        self.content_security_policy_nonce_in = (
            content_security_policy_nonce_in or []
        )

        app.jinja_env.globals['csp_nonce'] = self._get_nonce

        self.referrer_policy = referrer_policy

        self.session_cookie_secure = session_cookie_secure

        app.config['SESSION_COOKIE_SAMESITE'] = session_cookie_samesite

        if session_cookie_http_only:
            app.config['SESSION_COOKIE_HTTPONLY'] = True

        self.force_file_save = force_file_save

        self.x_content_type_options = x_content_type_options

        self.x_xss_protection = x_xss_protection

        self.app = app

        app.before_request(self._force_https)
        app.before_request(self._make_nonce)
        app.after_request(self._set_response_headers)

    def _get_local_options(self):
        view_function = flask.current_app.view_functions.get(
            flask.request.endpoint)
        view_options = getattr(
            view_function, 'talisman_view_options', {})

        view_options.setdefault('force_https', self.force_https)
        view_options.setdefault('frame_options', self.frame_options)
        view_options.setdefault(
            'frame_options_allow_from', self.frame_options_allow_from)
        view_options.setdefault(
            'content_security_policy', self.content_security_policy)
        view_options.setdefault(
            'content_security_policy_nonce_in',
            self.content_security_policy_nonce_in)
        view_options.setdefault(
            'permissions_policy', self.permissions_policy)
        view_options.setdefault(
            'document_policy', self.document_policy)
        view_options.setdefault(
            'feature_policy', self.feature_policy
        )

        return view_options

    def _force_https(self):
        """Redirect any non-https requests to https.

        Based largely on flask-sslify.
        """

        if self.session_cookie_secure:
            if not self.app.debug:
                self.app.config['SESSION_COOKIE_SECURE'] = True

        criteria = [
            self.app.debug,
            flask.request.is_secure,
            flask.request.headers.get('X-Forwarded-Proto', 'http') == 'https',
        ]

        local_options = self._get_local_options()

        if local_options['force_https'] and not any(criteria):
            if flask.request.url.startswith('http://'):
                url = flask.request.url.replace('http://', 'https://', 1)
                code = 302
                if self.force_https_permanent:
                    code = 301
                r = flask.redirect(url, code=code)
                return r

    def _set_response_headers(self, response):
        """Applies all configured headers to the given response."""
        options = self._get_local_options()
        self._set_feature_policy_headers(response.headers, options)
        self._set_permissions_policy_headers(response.headers, options)
        self._set_document_policy_headers(response.headers, options)
        self._set_frame_options_headers(response.headers, options)
        self._set_content_security_policy_headers(response.headers, options)
        self._set_hsts_headers(response.headers)
        self._set_referrer_policy_headers(response.headers)
        return response

    def _make_nonce(self):
        local_options = self._get_local_options()
        if (
                local_options['content_security_policy'] and
                local_options['content_security_policy_nonce_in'] and
                not getattr(flask.request, 'csp_nonce', None)):
            flask.request.csp_nonce = get_random_string(NONCE_LENGTH)

    def _get_nonce(self):
        return getattr(flask.request, 'csp_nonce', '')

    def _parse_structured_header_policy(self, policy):
        if isinstance(policy, str):
            return policy

        policies = []
        for section, content in policy.items():
            policy_part = '{}={}'.format(section, content)

            policies.append(policy_part)

        policy = ', '.join(policies)

        return policy

    def _parse_policy(self, policy):
        local_options = self._get_local_options()
        if isinstance(policy, str):
            # parse the string into a policy dict
            policy_string = policy
            policy = OrderedDict()

            for policy_part in policy_string.split(';'):
                policy_parts = policy_part.strip().split(' ')
                policy[policy_parts[0]] = " ".join(policy_parts[1:])

        policies = []
        for section, content in policy.items():
            if not isinstance(content, str):
                content = ' '.join(content)
            policy_part = '{} {}'.format(section, content)

            if (
                    hasattr(flask.request, 'csp_nonce') and
                    section in local_options['content_security_policy_nonce_in']):
                policy_part += " 'nonce-{}'".format(flask.request.csp_nonce)

            policies.append(policy_part)

        policy = '; '.join(policies)

        return policy

    def _set_feature_policy_headers(self, headers, options):
        if not options['feature_policy']:
            return

        policy = options['feature_policy']
        policy = self._parse_policy(policy)

        headers['Feature-Policy'] = policy

    def _set_permissions_policy_headers(self, headers, options):
        if not options['permissions_policy']:
            return

        policy = options['permissions_policy']
        policy = self._parse_structured_header_policy(policy)

        headers['Permissions-Policy'] = policy

    def _set_document_policy_headers(self, headers, options):
        if not options['document_policy']:
            return

        policy = options['document_policy']
        policy = self._parse_structured_header_policy(policy)

        headers['Document-Policy'] = policy

    def _set_frame_options_headers(self, headers, options):
        if not options['frame_options']:
            return
        headers['X-Frame-Options'] = options['frame_options']

        if options['frame_options'] == ALLOW_FROM:
            headers['X-Frame-Options'] += " {}".format(
                options['frame_options_allow_from'])

    def _set_content_security_policy_headers(self, headers, options):
        if self.x_xss_protection:
            headers['X-XSS-Protection'] = '1; mode=block'

        if self.x_content_type_options:
            headers['X-Content-Type-Options'] = 'nosniff'

        if self.force_file_save:
            headers['X-Download-Options'] = 'noopen'

        if not options['content_security_policy']:
            return

        policy = options['content_security_policy']
        policy = self._parse_policy(policy)

        if self.content_security_policy_report_uri and \
                'report-uri' not in policy:
            policy += '; report-uri ' + self.content_security_policy_report_uri

        csp_header = 'Content-Security-Policy'
        if self.content_security_policy_report_only:
            csp_header += '-Report-Only'

        headers[csp_header] = policy

    def _set_hsts_headers(self, headers):
        criteria = [
            flask.request.is_secure,
            flask.request.headers.get('X-Forwarded-Proto', 'http') == 'https',
        ]
        if not self.strict_transport_security or not any(criteria):
            return

        value = 'max-age={}'.format(self.strict_transport_security_max_age)

        if self.strict_transport_security_include_subdomains:
            value += '; includeSubDomains'

        if self.strict_transport_security_preload:
            value += '; preload'

        headers['Strict-Transport-Security'] = value

    def _set_referrer_policy_headers(self, headers):
        headers['Referrer-Policy'] = self.referrer_policy

    def __call__(self, **kwargs):
        """Use talisman as a decorator to configure options for a particular
        view.

        Only force_https, frame_options, frame_options_allow_from,
        content_security_policy, content_security_policy_nonce_in
        and feature_policy can be set on a per-view basis.

        Example:

            app = Flask(__name__)
            talisman = Talisman(app)

            @app.route('/normal')
            def normal():
                return 'Normal'

            @app.route('/embeddable')
            @talisman(frame_options=ALLOW_FROM, frame_options_allow_from='*')
            def embeddable():
                return 'Embeddable'
        """
        def decorator(f):
            setattr(f, 'talisman_view_options', kwargs)
            return f
        return decorator


try:
    import secrets

    def get_random_string(length):  # pragma: no cover
        # Note token_urlsafe returns a 'length'-byte string which is then
        # base64 encoded so is longer than length, so only return last
        # 'length' characters.
        return secrets.token_urlsafe(length)[:length]

except ImportError:  # pragma: no cover
    import random
    import string
    rnd = random.SystemRandom()

    def get_random_string(length):
        allowed_chars = (
            string.ascii_lowercase +
            string.ascii_uppercase +
            string.digits)
        return ''.join(
            rnd.choice(allowed_chars)
            for _ in range(length))
