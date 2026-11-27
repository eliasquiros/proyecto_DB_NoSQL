import redis
from pymongo import MongoClient

from .config import config

mongo_client = MongoClient(
    config.mongo_uri,
    serverSelectionTimeoutMS=config.mongo_timeout_ms,
)
mongo_db = mongo_client[config.mongo_db_name]
col_promociones = mongo_db["promociones"]
col_cupones = mongo_db["cupones"]

redis_client = redis.Redis(
    host=config.redis_host,
    port=config.redis_port,
    db=config.redis_db,
    decode_responses=True,
    socket_connect_timeout=config.redis_timeout_seg,
)
