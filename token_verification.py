import jwt
import base64
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import json
from urllib.request import urlopen
import os
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("MSAL_TENANT_ID")
CLIENT_ID = os.getenv("MSAL_CLIENT_ID")

if not TENANT_ID or not CLIENT_ID:
    raise ValueError("MSAL_TENANT_ID and MSAL_CLIENT_ID must be set")

def verifyUser(token, filestorage_location):
    try:
        user = token_is_valid(TENANT_ID, CLIENT_ID, token)["unique_name"].lower()

        if isUserValid(user, filestorage_location):
            return user
        else:
            return None
        
    except Exception as e:
        print(f"JWT validation error: {e}")
        return None

def isUserValid(user, filestorage_location):
    with open(os.path.join(filestorage_location, "FILESERVER_PERMISSIONS.fsconfig"), "r") as f:
        permissions = json.load(f)

    if user in permissions:
        return True
    else:
        return False

def token_is_valid(tenant_id, client_id, token):
    jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    issuer_url = f"https://sts.windows.net/{tenant_id}/"
    audience = f"{client_id}"

    jwks = json.loads(urlopen(jwks_url).read())
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = find_rsa_key(jwks, unverified_header)
    public_key = rsa_pem_from_jwk(rsa_key)
    
    return jwt.decode(
      token,
      public_key,
      verify=True,
      algorithms=["RS256"],
      audience=audience,
      issuer=issuer_url
    )

def find_rsa_key(jwks, unverified_header):
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            return {
              "kty": key["kty"],
              "kid": key["kid"],
              "use": key["use"],
              "n": key["n"],
              "e": key["e"]
            }

def ensure_bytes(key):
    if isinstance(key, str):
        key = key.encode('utf-8')
    return key


def decode_value(val):
    decoded = base64.urlsafe_b64decode(ensure_bytes(val) + b'==')
    return int.from_bytes(decoded, 'big')


def rsa_pem_from_jwk(jwk):
    return RSAPublicNumbers(
        n=decode_value(jwk['n']),
        e=decode_value(jwk['e'])
    ).public_key(default_backend()).public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )