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