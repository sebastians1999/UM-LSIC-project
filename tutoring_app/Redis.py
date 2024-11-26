import Redis
import os

import redis
import os

class RedisClient:

    def __init__(self):
        # Get the hostname or IP address of the Redis instance. If the environment
        # variable REDIS_HOST is not set, default to localhost.
        self.redis_host = os.getenv("REDIS_HOST", "localhost")

        # Get the port number of the Redis instance. If the environment variable
        # REDIS_PORT is not set, default to 6379.
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))

        # Get the password for the Redis instance. If the environment variable
        # REDIS_PASSWORD is not set, default to None.
        self.redis_password = os.getenv("REDIS_PASSWORD", None)

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


    def set_refresh_token(self, token: str, user_id: str, expiration: int):
        """
        Store the refresh token in Redis with an expiration time.
        """
        self.client.setex(token, expiration, user_id)

    def get_refresh_token(self, token: str):
        """
        Retrieve the user ID associated with the refresh token.
        """
        return self.client.get(token)

    def delete_refresh_token(self, token: str):
        """
        Delete the refresh token from Redis.
        """
        self.client.delete(token)

redis_client = RedisClient()
