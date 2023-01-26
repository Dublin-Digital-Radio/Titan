from config import config
from flask_limiter import Limiter
from titanembeds.cache_keys import get_client_ipaddr

# Default limit by ip address
rate_limiter = Limiter(key_func=get_client_ipaddr, storage_uri=config["redis-uri"])
