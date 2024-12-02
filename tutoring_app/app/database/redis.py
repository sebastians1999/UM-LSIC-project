from config import get_settings
import redis
import os

class RedisClient:
    """
    Redis client wrapper for caching and token management.
    
    This class provides a simplified interface for Redis operations used in the application,
    primarily for managing refresh tokens and general-purpose caching.
    
    Attributes:
        redis_host (str): Redis server hostname/IP
        redis_port (int): Redis server port
        redis_password (str): Redis server password
        client (redis.StrictRedis): Redis client instance
    """

    def __init__(self):
        # Get the hostname or IP address of the Redis instance.
        self.redis_host = get_settings().redis_host

        # Get the port number of the Redis instance. 
        self.redis_port = get_settings().redis_port

        # Get the password for the Redis instance.
        self.redis_password = get_settings().redis_password

        # Create a Redis client object. The parameters are:
        # - host: the hostname or IP address of the Redis instance, as determined
        #         above.
        # - port: the port number of the Redis instance, as determined above.
        # - password: the password for the Redis instance, as determined above.
        # - decode_responses: whether to decode all responses from Redis as
        #                    strings (True) or not (False). We set this to True
        #                    so that we don't have to manually decode all the
        #                    responses.
        self.client = redis.StrictRedis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            decode_responses=True
        )

    def set_refresh_token(self, token: str, token_id: str, expiration: int):
        """
        Store a refresh token in Redis with an expiration time.

        Args:
            token (str): The refresh token to store
            token_id (str): Unique identifier for the token
            expiration (int): Time in seconds until the token expires
        """
        self.client.setex(token_id, expiration, token)

    def get_refresh_token(self, token_id: str) -> str:
        """
        Retrieve a refresh token from Redis.

        Args:
            token_id (str): Unique identifier for the token

        Returns:
            str: The refresh token if found, None otherwise
        """
        return self.client.get(token_id)

    def delete_refresh_token(self, token_id: str):
        """
        Delete a refresh token from Redis.

        Args:
            token_id (str): Unique identifier for the token to delete
        """
        self.client.delete(token_id)

    def set_cache(self, key: str, value: str, expiration: int):
        """
        Set a cached value with expiration time.

        Args:
            key (str): Cache key
            value (str): Value to cache
            expiration (int): Time in seconds until the cache expires
        """
        self.client.setex(key, expiration, value)

    def get_cache(self, key: str) -> str:
        """
        Retrieve a cached value.

        Args:
            key (str): Cache key to retrieve

        Returns:
            str: The cached value if found, None otherwise
        """
        return self.client.get(key)

    def delete_cache(self, key: str):
        """
        Delete a cached value.

        Args:
            key (str): Cache key to delete
        """
        self.client.delete(key)

# Global Redis client instance
redis_client = RedisClient()