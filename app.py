import os
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
import secrets

import libtorrent as lt
import psutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from motor.motor_asyncio import AsyncIOMotorClient

import config

security = HTTPBasic()

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, config.AUTH_USER)
    ok_pass = secrets.compare_digest(credentials.password, config.AUTH_PASS)
    if not (ok_user and ok_pass):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})
    return True

app = FastAPI()

# ---- libtorrent session ----
lt_session = lt.session()
lt_session.apply_settings(config.LT_SETTINGS)
if config.ENABLE_DHT:
    lt_session.start_dht()
if config.ENABLE_LSD:
    lt_session.start_lsd()

handles = {}  # info_hash -> handle

# ---- mongo (bandwidth tracking, persists across restarts) ----
mongo_client = AsyncIOMotorClient(config.MONGO_URI) if config.MONGO_URI else None
db = mongo_client[config.DB_NAME] if mongo_client is not None else None
last_total_download = 0

async def background_loop():
    """Runs bandwidth accounting and, when seeding is disabled, force-pauses
    any torrent the instant it finishes so it stops uploading entirely."""
    global last_total_download
    while True:
        await asyncio.sleep(config.BANDWIDTH_TRACK_INTERVAL_SEC)

        if db is not None:
            current = lt_session.status().total_download
            delta = current - last_total_download
            if delta > 0:
                last_total_download = current
                month_key = datetime.utcnow().strftime("%Y-%m")
                await db.bandwidth.update_one({"_id": "total"}, {"$inc": {"bytes": delta}}, upsert=True)
                await db.bandwidth.update_one({"_id": month_key}, {"$inc": {"bytes": delta}}, upsert=True)

        if not config.SEEDING_ENABLED:
            for h in list(handles.values()):
                if not h.is_valid():
                    continue
                s = h.status()
                if s.is_finished and not s.paused:
                    h.pause()  # belt-and-braces: stop all network activity once done

@app.on_event("startup")
async def startup():
    asyncio.create_task(background_loop())

# ---- add torrents ----
def _post_add_setup(h):
    if config.ADD_EXTRA_TRACKERS:
        for url in config.EXTRA_TRACKERS:
            h.add_tracker({'url': url, 'tier': 1})
    if not config.SEEDING_ENABLED:
        h.set_upload_limit(config.NO_SEED_UPLOAD_LIMIT_BYTES)  # near-zero upload even while downloading

def add_magnet(uri: str):
    params = lt.parse_magnet_uri(uri)
    params.save_path = str(config.DOWNLOAD_DIR)
    params.storage_mode = lt.storage_mode_t.storage_mode_sparse
    h = lt_session.add_torrent(params)
    _post_add_setup(h)
    handles[str(h.info_hash())] = h
    return h

def add_torrent_file(path: str):
    info = lt.torrent_info(path)
    h = lt_session.add_torrent({
        'ti': info,
        'save_path': str(config.DOWNLOAD_DIR),
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,
    })
    _post_add_setup(h)
    handles[str(h.info_hash())] = h
    return h

@app.post("/api/add_magnet")
async def api_add_magnet(magnet: str = Form(...), auth: bool = Depends(check_auth)):
    try:
        h = add_magnet(magnet)
        return {"ok": True, "hash": str(h.info_hash())}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/add_torrent")
async def api_add_torrent(file: UploadFile = File(...), auth: bool = Depends(check_auth)):
    tmp_path = f"/tmp/{file.filename}"
    size = 0
    max_bytes = config.MAX_TORRENT_UPLOAD_MB * 1024 * 1024
    with open(tmp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                f.close()
                os.remove(tmp_path)
                raise HTTPException(400, f".torrent file exceeds {config.MAX_TORRENT_UPLOAD_MB}MB limit")
            f.write(chunk)
    try:
        h = add_torrent_file(tmp_path)
        return {"ok": True, "hash": str(h.info_hash())}
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/remove/{info_hash}")
async def api_remove(info_hash: str, delete_files: bool = False, auth: bool = Depends(check_auth)):
    h = handles.get(info_hash)
    if not h:
        raise HTTPException(404, "not found")
    lt_session.remove_torrent(h, 1 if delete_files else 0)
    del handles[info_hash]
    return {"ok": True}

@app.get("/api/status")
async def api_status(auth: bool = Depends(check_auth)):
    result = []
    for info_hash, h in list(handles.items()):
        if not h.is_valid():
            continue
        s = h.status()
        result.append({
            "hash": info_hash,
            "name": s.name or "fetching metadata...",
            "progress": round(s.progress * 100, 2),
            "download_rate": round(s.download_rate / 1024, 1),
            "upload_rate": round(s.upload_rate / 1024, 1),
            "num_peers": s.num_peers,
            "num_seeds": s.num_seeds,
            "num_leechers": max(s.num_peers - s.num_seeds, 0),
            "state": str(s.state).split(".")[-1],
            "total_size": s.total_wanted,
            "downloaded": s.total_wanted_done,
            "is_finished": s.is_finished,
            "paused": s.paused,
        })
    return result

@app.get("/api/system")
async def api_system(auth: bool = Depends(check_auth)):
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(config.DOWNLOAD_DIR))
    total_bw = monthly_bw = 0
    if db is not None:
        doc = await db.bandwidth.find_one({"_id": "total"})
        total_bw = doc["bytes"] if doc else 0
        mdoc = await db.bandwidth.find_one({"_id": datetime.utcnow().strftime("%Y-%m")})
        monthly_bw = mdoc["bytes"] if mdoc else 0
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "ram_used_mb": round(mem.used / 1024 / 1024, 1),
        "ram_total_mb": round(mem.total / 1024 / 1024, 1),
        "ram_percent": mem.percent,
        "disk_used_gb": round(disk.used / 1024**3, 2),
        "disk_total_gb": round(disk.total / 1024**3, 2),
        "total_bandwidth_gb": round(total_bw / 1024**3, 3),
        "monthly_bandwidth_gb": round(monthly_bw / 1024**3, 3),
        "seeding_enabled": config.SEEDING_ENABLED,
    }

@app.get("/api/files")
async def api_files(auth: bool = Depends(check_auth)):
    files = []
    for p in config.DOWNLOAD_DIR.rglob("*"):
        if p.is_file():
            files.append({
                "name": p.name,
                "path": str(p.relative_to(config.DOWNLOAD_DIR)),
                "size": p.stat().st_size,
            })
    return files

def _safe_resolve(file_path: str) -> Path:
    base = config.DOWNLOAD_DIR.resolve()
    full_path = (config.DOWNLOAD_DIR / file_path).resolve()
    if not str(full_path).startswith(str(base)):
        raise HTTPException(403, "forbidden")
    return full_path

@app.get("/download/{file_path:path}")
async def download_file(file_path: str, auth: bool = Depends(check_auth)):
    full_path = _safe_resolve(file_path)
    if not full_path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(full_path, filename=full_path.name)

@app.delete("/api/files/{file_path:path}")
async def delete_file(file_path: str, auth: bool = Depends(check_auth)):
    full_path = _safe_resolve(file_path)
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(404, "not found")
    full_path.unlink()
    # clean up now-empty parent directories back up to DOWNLOAD_DIR
    parent = full_path.parent
    base = config.DOWNLOAD_DIR.resolve()
    while parent != base and parent.exists() and not any(parent.iterdir()):
        empty_dir = parent
        parent = parent.parent
        empty_dir.rmdir()
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def index(auth: bool = Depends(check_auth)):
    return Path("static/index.html").read_text()
