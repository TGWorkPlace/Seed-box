import os
from pathlib import Path

# ---- Auth ----
AUTH_USER = os.environ.get("AUTH_USER", "admin")
AUTH_PASS = os.environ.get("AUTH_PASS", "changeme")

# ---- Mongo ----
MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME = os.environ.get("DB_NAME", "seedbox")

# ---- Storage ----
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/app/downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---- libtorrent session settings ----
LISTEN_INTERFACES = os.environ.get("LISTEN_INTERFACES", "0.0.0.0:6881")
ENABLE_DHT = os.environ.get("ENABLE_DHT", "true").lower() == "true"
ENABLE_LSD = os.environ.get("ENABLE_LSD", "true").lower() == "true"

DOWNLOAD_RATE_LIMIT = int(os.environ.get("DOWNLOAD_RATE_LIMIT_KB", "0")) * 1024      # 0 = unlimited
UPLOAD_RATE_LIMIT = int(os.environ.get("UPLOAD_RATE_LIMIT_KB", "100")) * 1024        # cap upload, saves egress
ACTIVE_DOWNLOADS = int(os.environ.get("ACTIVE_DOWNLOADS", "3"))
ACTIVE_SEEDS = int(os.environ.get("ACTIVE_SEEDS", "2"))
CONNECTIONS_LIMIT = int(os.environ.get("CONNECTIONS_LIMIT", "150"))
CACHE_SIZE = int(os.environ.get("CACHE_SIZE", "256"))                                # in 16KB blocks

LT_SETTINGS = {
    'listen_interfaces': LISTEN_INTERFACES,
    'enable_upnp': False,
    'enable_natpmp': False,
    'download_rate_limit': DOWNLOAD_RATE_LIMIT,
    'upload_rate_limit': UPLOAD_RATE_LIMIT,
    'active_downloads': ACTIVE_DOWNLOADS,
    'active_seeds': ACTIVE_SEEDS,
    'connections_limit': CONNECTIONS_LIMIT,
    'cache_size': CACHE_SIZE,
}

# ---- App behaviour ----
BANDWIDTH_TRACK_INTERVAL_SEC = int(os.environ.get("BANDWIDTH_TRACK_INTERVAL_SEC", "15"))
MAX_TORRENT_UPLOAD_MB = int(os.environ.get("MAX_TORRENT_UPLOAD_MB", "10"))            # guard on .torrent file size
