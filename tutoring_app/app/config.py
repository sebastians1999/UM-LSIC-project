from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import base64
import secrets

class Settings(BaseSettings):
    """
    Settings for the Tutoring App.

    Please do not modify this file directly.
    Instead, create a .env file in the root directory of the project
    and specify the settings you would like to change there.
    For example, if you would like to use a redis server, add the following
    line to the .env file: 
    - USE_REDIS=True.

    Some settings are required to be set in the .env file, such as:
    - SECRET_KEY
    - GITLAB_CLIENT_ID
    - GITLAB_CLIENT_SECRET

    The above values are sentitive and should never be pushed to GitHub so
    that is why they need to be set as environment variables. 

    SUMMARY:
    - Override settings (if needed) using a .env file
    - Never push the .env file to GitHub (it should be in .gitignore)
    - Required .env settings are SECRET_KEY, GITLAB_CLIENT_ID, and GITLAB_CLIENT_SECRET (ask a team member for these values)
    """

    # Application settings
    app_name: str = "Tutoring App"
    app_version: str = "0.1.0"
    app_host: str = "localhost"
    app_port: int = 8000

    # Local vs production settings
    local: bool = True # Default to local development

    # Token settings
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    secret_key: Optional[str] = secrets.token_hex(20)
    hash_algorithm: str = "HS256"

    # Logs settings
    logs_dir: str = "logs"

    # Gitlab OAuth settings
    gitlab_client_id: Optional[str] = None
    gitlab_client_secret: Optional[str] = None
    gitlab_redirect_uri: str = "http://localhost:8000/auth/callback" 
    gitlab_base_url: str = "https://gitlab.com"
    gitlab_api_url: str = "https://gitlab.com/oauth/userinfo"

    # Database settings
    db_url: str = "sqlite:///new_db.db" # Default, for local development
    db_password: Optional[str] = None # Optional, required for cloud databases
    db_user: Optional[str] = None # Optional, required for cloud databases
    db_name: Optional[str] = None # Optional, required for cloud databases
    db_port: Optional[int] = None # Optional, required for cloud databases
    db_host: Optional[str] = None # Optional, required for cloud databases
    
    # Redis settings
    use_redis: bool = False # Default to not using Redis, change this to True if you have a Redis server set up
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    # Session settings
    session_expire_minutes: int = 60
    https_enabled: bool = True

    # Temporary admin account settings
    admin_name: str = "Admin"
    admin_email: str = "admin@example.com"


    # Load settings from .env file
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache() # Cache settings to avoid reading .env file multiple times
def get_settings():
    """ 
    Use this function as a dependency to get the settings object.
    Dependency injection will make it easier to test endpoints with different settings, simply inject a different settings object.
    """
    return Settings()