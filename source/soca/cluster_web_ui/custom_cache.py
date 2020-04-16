import datetime
import config

# Cache folder permissions, group membership for the web UI (5 minutes default)
CACHED_VALUES = {}


class CustomSOCACache:
    def __init__(self, key):
        self.key = key
        self.cache_time = config.Config.DEFAULT_CACHE_TIME
        self.cached_values = CACHED_VALUES

    def write_to_cache(self, value):
        print("Write to cache " + str(value))
        print("Caching " + str(self.key) + ": " + str(value) + " for " + str(self.cache_time)+ " seconds ")
        self.cached_values[self.key] = {"value": value,
                                        "valid_until": datetime.datetime.utcnow() + datetime.timedelta(seconds=self.cache_time)}

    def is_cached(self):
        if self.key not in self.cached_values:
            return False
        else:
            if datetime.datetime.utcnow() > self.cached_values[self.key]["valid_until"]:
                del self.cached_values[self.key]
                return False

        return self.cached_values[self.key]


