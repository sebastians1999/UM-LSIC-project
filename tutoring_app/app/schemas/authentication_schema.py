from pydantic import BaseModel

class LoggedInResponse(BaseModel):
    """Authentication response data"""
    access_token: str
    refresh_token: str
    token_type: str
    status: str

class SignUpResponse(BaseModel):
    """Sign-up response data"""
    message: str
    status: str
    redirect_to: str

class DecodedAccessToken(BaseModel):
    """
    Decoded access token data
        Args:
        - sub (int): User ID
        - name (str): User name
        - email (str): User email
        - role (str): User role
        - logged_in (bool): User logged in status
        - exp (int): Token expiration time
    """
    sub: int
    name: str
    email: str
    role: str
    logged_in: bool
    exp: int