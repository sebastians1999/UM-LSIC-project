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

class LoggedOutResponse(BaseModel):
    """Logout response data"""
    message: str
    status: str

class DecodedAccessToken(BaseModel):
    """
    Decoded access token data
        Args:
        - sub (str): User ID
        - name (str): User name
        - email (str): User email
        - role (str): User role
        - logged_in (bool): User logged in status
        - exp (int): Token expiration time
    """
    sub: str
    name: str
    email: str
    role: str
    logged_in: bool
    exp: int
    refresh_token_id: str

class DecodedRefreshToken(BaseModel):
    """
    Decoded refresh token data
        Args:
        - sub (str): User ID
        - exp (int): Token expiration time
        - token_id (str): Token ID
        - refresh (bool): Refresh token status
    """
    sub: str
    exp: int
    token_id: str
    refresh: bool