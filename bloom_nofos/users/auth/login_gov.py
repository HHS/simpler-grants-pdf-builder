import json
import jwt
import time
import uuid
from urllib.parse import urlencode
import requests
from django.conf import settings
from django.urls import reverse


class LoginGovClient:
    """Client for handling Login.gov OIDC authentication flow."""

    def __init__(self):
        self.client_id = settings.LOGIN_GOV["CLIENT_ID"]
        self.oidc_url = settings.LOGIN_GOV["OIDC_URL"].rstrip("/")
        self.private_key = settings.LOGIN_GOV["PRIVATE_KEY"]
        self.redirect_uri = settings.LOGIN_GOV["REDIRECT_URI"]
        self.acr_values = settings.LOGIN_GOV["ACR_VALUES"]

    def get_authorization_url(self, state=None):
        """Generate the Login.gov authorization URL for the initial redirect."""
        state = state or str(uuid.uuid4())
        nonce = str(uuid.uuid4())

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "acr_values": self.acr_values,
            "scope": "openid email",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "nonce": nonce,
        }

        return f"{self.oidc_url}/authorize?{urlencode(params)}", state, nonce

    def get_token(self, code):
        """Exchange authorization code for tokens."""
        now = int(time.time())

        # Create client assertion JWT
        assertion = jwt.encode(
            {
                "iss": self.client_id,
                "sub": self.client_id,
                "aud": f"{self.oidc_url}/token",
                "jti": str(uuid.uuid4()),
                "exp": now + 300,  # 5 minutes
                "iat": now,
            },
            self.private_key,
            algorithm="RS256",
        )

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        }

        response = requests.post(f"{self.oidc_url}/token", data=token_data)
        response.raise_for_status()

        return response.json()

    def validate_id_token(self, id_token, nonce):
        """Validate the ID token from Login.gov."""
        try:
            decoded = jwt.decode(
                id_token,
                self.private_key,
                algorithms=["RS256"],
                audience=self.client_id,
            )

            if decoded.get("nonce") != nonce:
                raise ValueError("Invalid nonce in ID token")

            return decoded

        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {str(e)}")
