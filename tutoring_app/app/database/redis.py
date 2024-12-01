import redis
import os
import json

class RedisClient:

    def __init__(self):
        # Get Redis configuration from environment variables
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)

        # Initialize the Redis client
        self.client = redis.StrictRedis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            decode_responses=True  # Automatically decode Redis responses as strings
        )

    # Existing methods for refresh tokens
    def set_refresh_token(self, token: str, token_id: str, expiration: int):
        """
        Store the refresh token in Redis with an expiration time.
        """
        self.client.setex(token_id, expiration, token)

    def get_refresh_token(self, token_id: str):
        """
        Retrieve the refresh token associated with the refresh token id.
        """
        return self.client.get(token_id)

    def delete_refresh_token(self, token_id: str):
        """
        Delete the refresh token from Redis.
        """
        self.client.delete(token_id)

    # New generic caching methods
    def set_cache(self, key: str, value, expiration: int = 600):
        """
        Store a value in Redis with an optional expiration time.
        The value is automatically serialized to JSON.
        """
        serialized_value = json.dumps(value)
        self.client.setex(key, expiration, serialized_value)

    def get_cache(self, key: str):
        """
        Retrieve a cached value from Redis by key.
        The value is automatically deserialized from JSON.
        """
        cached_value = self.client.get(key)
        return json.loads(cached_value) if cached_value else None

    def delete_cache(self, key: str):
        """
        Delete a cached value from Redis by key.
        """
        self.client.delete(key)


# Instantiate the Redis client
redis_client = RedisClient()
