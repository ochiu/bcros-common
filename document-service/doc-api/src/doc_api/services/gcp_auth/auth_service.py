# Copyright © 2019 Province of British Columbia
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
"""This maintains access tokens for API calls."""
import base64
import json

import google.auth.transport.requests
import google.oauth2.id_token
from flask import current_app
from google.oauth2 import service_account

from doc_api.services.abstract_auth_service import AuthService


class GoogleAuthService(AuthService):  # pylint: disable=too-few-public-methods
    """Google Auth Service implementation.

    Maintains a wrapper to get a service account access token and credentials for Google API calls.
    """

    # Google APIs and cloud storage os.getenv('GCP
    gcp_auth_key = None
    # https://developers.google.com/identity/protocols/oauth2/scopes
    gcp_sa_scopes = None

    service_account_info = None
    credentials = None
    # Use service account env var if available.
    if gcp_auth_key:
        sa_bytes = bytes(gcp_auth_key, "utf-8")
        service_account_info = json.loads(base64.b64decode(sa_bytes.decode("utf-8")))
    # Otherwise leave as none and use the service account attached to the Cloud service.

    @staticmethod
    def init_app(app):
        """Set up the service"""
        GoogleAuthService.gcp_auth_key = app.config.get("GCP_AUTH_KEY")
        GoogleAuthService.gcp_sa_scopes = [app.config.get("GCP_CS_SA_SCOPES")]
        if GoogleAuthService.gcp_auth_key:
            sa_bytes = bytes(GoogleAuthService.gcp_auth_key, "utf-8")
            GoogleAuthService.service_account_info = json.loads(base64.b64decode(sa_bytes.decode("utf-8")))

    @classmethod
    def get_token(cls):
        """Generate an OAuth access token with cloud storage access."""
        if cls.credentials is None:
            cls.credentials = service_account.Credentials.from_service_account_info(
                cls.service_account_info, scopes=cls.gcp_sa_scopes
            )
        request = google.auth.transport.requests.Request()
        cls.credentials.refresh(request)
        current_app.logger.info("Call successful: obtained token.")
        return cls.credentials.token

    @classmethod
    def get_report_api_token(cls):
        """Generate an OAuth access token with IAM configured auth mhr api container to report api container."""
        audience = current_app.config.get("REPORT_API_AUDIENCE")
        if not audience:
            return None
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
        current_app.logger.info("Call successful: obtained token.")
        return token

    @classmethod
    def get_credentials(cls):
        """Generate GCP auth credentials to pass to a GCP client."""
        if cls.credentials is None:
            cls.credentials = service_account.Credentials.from_service_account_info(
                cls.service_account_info, scopes=cls.gcp_sa_scopes
            )
        current_app.logger.info("Call successful: obtained credentials.")
        return cls.credentials
