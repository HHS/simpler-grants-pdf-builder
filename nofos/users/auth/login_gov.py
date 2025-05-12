import json
import time
import uuid
from urllib.parse import urlencode

import jwt
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.conf import settings
from jwt.algorithms import RSAAlgorithm


class LoginGovClient:
    """Client for handling Login.gov OIDC authentication flow."""

    def __init__(self):
        self.client_id = settings.LOGIN_GOV["CLIENT_ID"]
        base_url = settings.LOGIN_GOV["OIDC_URL"].strip().rstrip("/")
        if not base_url.endswith("/openid_connect"):
            base_url = f"{base_url}/openid_connect"
        self.oidc_url = base_url
        self.token_url = base_url.replace("/openid_connect", "/api/openid_connect")

        # Get private key from settings
        private_key_pem = settings.LOGIN_GOV.get("PRIVATE_KEY")
        if not private_key_pem:
            raise Exception(
                "Private key not configured in settings.LOGIN_GOV['PRIVATE_KEY']"
            )

        try:
            self.private_key_pem = private_key_pem.encode("utf-8")
            self.private_key = load_pem_private_key(
                self.private_key_pem, password=None, backend=default_backend()
            )
        except Exception as e:
            raise Exception(f"Error loading private key: {str(e)}")

        self.redirect_uri = settings.LOGIN_GOV["REDIRECT_URI"].strip()
        self.acr_values = settings.LOGIN_GOV["ACR_VALUES"]

    def _get_login_gov_public_key(self, kid=None):
        """Fetch Login.gov's public key configuration.

        Args:
            kid: Optional key ID to fetch a specific key
        """
        try:
            certs_url = f"{self.token_url}/certs"
            response = requests.get(certs_url)
            response.raise_for_status()

            keys = response.json()
            if not keys or "keys" not in keys or not keys["keys"]:
                raise ValueError("No keys found in Login.gov certs response")

            if kid:
                jwk = next((key for key in keys["keys"] if key.get("kid") == kid), None)
                if not jwk:
                    raise ValueError(f"No key found with ID: {kid}")
            else:
                jwk = next(
                    (key for key in keys["keys"] if key.get("kty") == "RSA"), None
                )
                if not jwk:
                    raise ValueError("No RSA key found in Login.gov certs")

            return RSAAlgorithm.from_jwk(json.dumps(jwk))

        except Exception as e:
            raise ValueError(f"Error fetching Login.gov public key: {str(e)}")

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

        auth_url = f"{self.oidc_url}/authorize?{urlencode(params)}"
        return auth_url, state, nonce

    def get_token(self, code):
        """Exchange authorization code for tokens."""
        if not self.private_key:
            raise Exception(
                "Private key not configured. Cannot create client assertion."
            )

        now = int(time.time())

        try:
            assertion = jwt.encode(
                {
                    "iss": self.client_id,
                    "sub": self.client_id,
                    "aud": f"{self.token_url}/token",
                    "jti": str(uuid.uuid4()),
                    "exp": now + 300,  # 5 minutes
                    "iat": now,
                },
                self.private_key,
                algorithm="RS256",
            )
        except Exception as e:
            raise Exception(f"Error creating client assertion: {str(e)}")

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
        }

        response = requests.post(f"{self.token_url}/token", data=token_data)
        response.raise_for_status()
        return response.json()

    def validate_id_token(self, id_token, nonce):
        """Validate the ID token from Login.gov."""
        try:
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")

            public_key = self._get_login_gov_public_key(kid)
            if not public_key:
                raise ValueError("Could not get Login.gov public key")

            decoded = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.oidc_url.replace("/openid_connect", "") + "/",
            )

            if decoded.get("nonce") != nonce:
                raise ValueError("Invalid nonce in ID token")

            return decoded

        except Exception as e:
            raise ValueError(f"Invalid ID token: {str(e)}")
