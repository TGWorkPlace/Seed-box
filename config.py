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

# ---- Seeding policy ----
# False (default): torrents download only. Upload is throttled to near-zero
# WHILE downloading, and torrents are force-paused the moment they finish,
# so nothing seeds after completion either.
SEEDING_ENABLED = os.environ.get("SEEDING_ENABLED", "false").lower() == "true"
NO_SEED_UPLOAD_LIMIT_BYTES = 1  # per-torrent upload cap when seeding is off (1 B/s ~= off; libtorrent treats 0 as "unlimited")

# ---- libtorrent session settings ----
LISTEN_INTERFACES = os.environ.get("LISTEN_INTERFACES", "0.0.0.0:6881")
ENABLE_DHT = os.environ.get("ENABLE_DHT", "true").lower() == "true"
ENABLE_LSD = os.environ.get("ENABLE_LSD", "true").lower() == "true"

DOWNLOAD_RATE_LIMIT = int(os.environ.get("DOWNLOAD_RATE_LIMIT_KB", "0")) * 1024      # 0 = unlimited
UPLOAD_RATE_LIMIT = int(os.environ.get("UPLOAD_RATE_LIMIT_KB", "300")) * 1024        # ignored session-wide when SEEDING_ENABLED is False
ACTIVE_DOWNLOADS = int(os.environ.get("ACTIVE_DOWNLOADS", "3"))
ACTIVE_SEEDS = int(os.environ.get("ACTIVE_SEEDS", "2"))
CONNECTIONS_LIMIT = int(os.environ.get("CONNECTIONS_LIMIT", "300"))
CACHE_SIZE = int(os.environ.get("CACHE_SIZE", "512"))                                # in 16KB blocks
UNCHOKE_SLOTS_LIMIT = int(os.environ.get("UNCHOKE_SLOTS_LIMIT", "40"))

LT_SETTINGS = {
    'listen_interfaces': LISTEN_INTERFACES,
    'enable_upnp': False,
    'enable_natpmp': False,
    'download_rate_limit': DOWNLOAD_RATE_LIMIT,
    'upload_rate_limit': UPLOAD_RATE_LIMIT if SEEDING_ENABLED else 1024,  # global safety net, 1KB/s when seeding is off
    'active_downloads': ACTIVE_DOWNLOADS,
    'active_seeds': ACTIVE_SEEDS,
    'connections_limit': CONNECTIONS_LIMIT,
    'cache_size': CACHE_SIZE,
    'unchoke_slots_limit': UNCHOKE_SLOTS_LIMIT,
    'request_timeout': 20,
    'peer_connect_timeout': 8,
    'whole_pieces_threshold': 20,
}
if not SEEDING_ENABLED:
    # Auto-management: treat every torrent as "done seeding" the instant it completes,
    # so libtorrent's own queue logic backs up the manual pause() as well.
    LT_SETTINGS['share_ratio_limit'] = 0
    LT_SETTINGS['seed_time_limit'] = 1
    LT_SETTINGS['seed_time_ratio_limit'] = 0

# ---- App behaviour ----
BANDWIDTH_TRACK_INTERVAL_SEC = int(os.environ.get("BANDWIDTH_TRACK_INTERVAL_SEC", "15"))
MAX_TORRENT_UPLOAD_MB = int(os.environ.get("MAX_TORRENT_UPLOAD_MB", "10"))

# ---- Extra trackers appended to every torrent (boosts peer count on sparse magnets) ----
ADD_EXTRA_TRACKERS = os.environ.get("ADD_EXTRA_TRACKERS", "true").lower() == "true"
EXTRA_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.tracker.cl:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://tracker-udp.gbitt.info:80/announce",
    "udp://opentracker.io:6969/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://explodie.org:6969/announce",
    "udp://tracker.theoks.net:6969/announce",
    "udp://tracker.dump.cl:6969/announce",
    "udp://tracker1.bt.moack.co.kr:80/announce",
    "udp://tracker.srv00.com:6969/announce",
    "udp://tracker.gigantino.net:6969/announce",
    "udp://ttk2.nbaonlineservice.com:6969/announce",
    "udp://tracker.leech.ie:1337/announce",
    "udp://ns-1.x-fins.com:6969/announce",
    "udp://p4p.arenabg.com:1337/announce",
    "udp://tracker.moeking.me:6969/announce",
    "udp://tracker.tiny-vps.com:6969/announce",
    "udp://vibe.sleepyinternetfun.xyz:1738/announce",
    "udp://tracker.fnix.net:6969/announce",
    "udp://ryjer.com:6969/announce",
    "udp://d40969.acod.regrucolo.ru:6969/announce",
    "udp://bt2.archive.org:6969/announce",
    "udp://bt1.archive.org:6969/announce",
    "http://tracker.openbittorrent.com:80/announce",
    "http://tracker.opentrackr.org:1337/announce",
    "https://tracker.gbitt.info/announce",
    "https://tracker.zhuqiy.top/announce",
    "https://tracker.expli.top/announce",
    "udp://tracker.bitsearch.to:1337/announce",
]
# Public tracker lists rot over time (some go offline every few months).
# If peer counts feel low again later, refresh this list from a source like
# https://github.com/ngosang/trackerslist (the "best" list).
