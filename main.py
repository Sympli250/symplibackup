from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Union, List, Dict, Any
import urbackup_api
import sys
import platform
import logging

URBACKUP_URL = "http://127.0.0.1:55414/x"
URBACKUP_USER = "admin"
URBACKUP_PASS = "Sherpa2025!"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="UrBackup REST API Proxy")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error("HTTPException: %s", exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.middleware("http")
async def catch_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unhandled exception: %s", exc)
        raise HTTPException(status_code=500, detail="Internal Server Error")


def get_server():
    try:
        return urbackup_api.urbackup_server(URBACKUP_URL, URBACKUP_USER, URBACKUP_PASS)
    except Exception as exc:
        logger.error("Failed to connect to UrBackup server: %s", exc)
        raise HTTPException(status_code=503, detail="Unable to connect to UrBackup server")

def resolve_client(server, identifier: Union[str, int]) -> Dict[str, Any]:
    """
    Résout un client UrBackup à partir de son nom ou id.
    Retourne le dict client ou lève HTTPException 404 si inconnu.
    """
    # Récupère la liste des clients via get_status (compatible avec ce wrapper)
    status = server.get_status()
    clients = status["clients"] if "clients" in status else status
    try:
        int_id = int(identifier)
        for c in clients:
            if c.get("id") == int_id:
                return c
    except (ValueError, TypeError):
        identifier = str(identifier)
        for c in clients:
            if c.get("name") == identifier:
                return c
    logger.error("Client '%s' not found", identifier)
    raise HTTPException(status_code=404, detail=f"Client '{identifier}' not found")

# ===== Pydantic Models =====

# --- Request Models ---

class ClientIdentifier(BaseModel):
    client: Union[str, int]


class BackupDeleteRequest(ClientIdentifier):
    backup_id: int


class ClientCreateRequest(BaseModel):
    client: str


class ClientDeleteRequest(ClientIdentifier):
    pass


class ClientRenameRequest(BaseModel):
    old: Union[str, int]
    new: str


class ClientSettingChangeRequest(ClientIdentifier):
    key: str
    new_value: str


class QuotaRequest(ClientIdentifier):
    quota_bytes: int


class BackupRequest(ClientIdentifier):
    pass


# --- Response Models ---

class ClientSummary(BaseModel):
    name: str
    id: int


class BackupResult(BaseModel):
    success: bool


class QuotaInfo(BaseModel):
    client: str
    quota_bytes: Optional[int] = None


class UsedSpaceInfo(BaseModel):
    client: str
    used_bytes: int


class AuthKeyInfo(BaseModel):
    authkey: str

# ===== ROUTES =====

@app.get("/status", response_model=Dict[str, Any])
def get_status(server=Depends(get_server)):
    """Return overall UrBackup server status."""
    logger.info("Fetching server status")
    return server.get_status()


@app.get("/clients", response_model=List[ClientSummary])
def get_clients(server=Depends(get_server)):
    """List all configured clients with their identifiers."""
    logger.info("Listing clients")
    status = server.get_status()
    clients = status["clients"] if "clients" in status else status
    return [ClientSummary(name=c["name"], id=c["id"]) for c in clients]


@app.get("/client/{client_identifier}", response_model=Dict[str, Any])
def get_client_detail(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """Retrieve detailed information for a specific client."""
    logger.info("Retrieving client detail for %s", client_identifier)
    return resolve_client(server, client_identifier)

@app.post("/backup/full", response_model=BackupResult)
def launch_full_backup(req: BackupRequest, server=Depends(get_server)):
    """Start a full file backup for the specified client."""
    logger.info("Starting full file backup for %s", req.client)
    client = resolve_client(server, req.client)
    ok = bool(server.start_full_file_backup(client["id"]))
    return BackupResult(success=ok)


@app.post("/backup/image", response_model=BackupResult)
def launch_image_backup(req: BackupRequest, server=Depends(get_server)):
    """Start a full image backup for the specified client."""
    logger.info("Starting full image backup for %s", req.client)
    client = resolve_client(server, req.client)
    ok = bool(server.start_full_image_backup(client["id"]))
    return BackupResult(success=ok)


@app.post("/backup/incremental", response_model=BackupResult)
def launch_incremental_backup(req: BackupRequest, server=Depends(get_server)):
    """Start an incremental file backup for the specified client."""
    logger.info("Starting incremental file backup for %s", req.client)
    client = resolve_client(server, req.client)
    ok = bool(server.start_incremental_file_backup(client["id"]))
    return BackupResult(success=ok)


@app.get("/backups/{client_identifier}", response_model=List[Dict[str, Any]])
def get_client_backups(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """List backups available for a client."""
    logger.info("Listing backups for %s", client_identifier)
    client = resolve_client(server, client_identifier)
    return server.get_client_backups(client["id"])


@app.post("/backup/delete", response_model=BackupResult)
def delete_backup(req: BackupDeleteRequest, server=Depends(get_server)):
    """Delete a specific backup belonging to a client."""
    logger.info("Deleting backup %s for client %s", req.backup_id, req.client)
    client = resolve_client(server, req.client)
    ok = bool(server.delete_backup(client["id"], req.backup_id))
    return BackupResult(success=ok)


@app.post("/client/create", response_model=BackupResult)
def create_client(req: ClientCreateRequest, server=Depends(get_server)):
    """Create a new client on the UrBackup server."""
    logger.info("Creating client %s", req.client)
    ok = bool(server.add_client(req.client))
    return BackupResult(success=ok)


@app.post("/client/delete", response_model=BackupResult)
def delete_client(req: ClientDeleteRequest, server=Depends(get_server)):
    """Remove an existing client from the server."""
    logger.info("Deleting client %s", req.client)
    client = resolve_client(server, req.client)
    ok = bool(server.remove_client(client["id"]))
    return BackupResult(success=ok)


@app.post("/client/rename", response_model=BackupResult)
def rename_client(req: ClientRenameRequest, server=Depends(get_server)):
    """Rename an existing client."""
    logger.info("Renaming client %s to %s", req.old, req.new)
    client = resolve_client(server, req.old)
    ok = bool(server.rename_client(client["id"], req.new))
    return BackupResult(success=ok)

@app.get("/client/settings/{client_identifier}", response_model=Dict[str, Any])
def get_client_settings(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """Retrieve settings for a given client."""
    logger.info("Getting settings for client %s", client_identifier)
    client = resolve_client(server, client_identifier)
    return server.get_client_settings(client["id"])


@app.post("/client/settings/change", response_model=BackupResult)
def set_client_setting(req: ClientSettingChangeRequest, server=Depends(get_server)):
    """Update a specific client setting."""
    logger.info("Changing setting %s for client %s", req.key, req.client)
    client = resolve_client(server, req.client)
    ok = bool(server.change_client_setting(client["id"], req.key, req.new_value))
    return BackupResult(success=ok)


@app.get("/client/authkey/{client_identifier}", response_model=AuthKeyInfo)
def get_client_authkey(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """Get the authentication key for a client."""
    logger.info("Getting authkey for client %s", client_identifier)
    client = resolve_client(server, client_identifier)
    return AuthKeyInfo(authkey=server.get_client_authkey(client["id"]))


@app.get("/logs/{client_identifier}", response_model=List[Dict[str, Any]])
def get_client_logs(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """Retrieve logs for a client."""
    logger.info("Getting logs for client %s", client_identifier)
    client = resolve_client(server, client_identifier)
    return server.get_client_logs(client["id"])

@app.get("/client/{client_identifier}/quota", response_model=QuotaInfo)
def get_client_quota(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """Get the configured quota for a client."""
    logger.info("Getting quota for client %s", client_identifier)
    client = resolve_client(server, client_identifier)
    settings = server.get_client_settings(client["id"])
    quota = settings.get("quota", {}).get("value")
    return QuotaInfo(client=client["name"], quota_bytes=int(quota) if quota is not None else None)

@app.post("/client/quota", response_model=BackupResult)
def set_client_quota(req: QuotaRequest, server=Depends(get_server)):
    """Set the quota for a client."""
    logger.info("Setting quota for client %s to %s", req.client, req.quota_bytes)
    client = resolve_client(server, req.client)
    ok = bool(server.change_client_setting(client["id"], "quota", str(req.quota_bytes)))
    return BackupResult(success=ok)

@app.get("/client/{client_identifier}/used_space", response_model=UsedSpaceInfo)
def get_client_used_space(
    client_identifier: Union[str, int] = Path(...),
    server=Depends(get_server),
):
    """Compute total space used by a client's backups."""
    logger.info("Calculating used space for client %s", client_identifier)
    client = resolve_client(server, client_identifier)
    backups = server.get_client_backups(client["id"])
    total_bytes = sum(
        b.get("total_bytes", 0) for b in backups if b.get("total_bytes") is not None
    )
    return UsedSpaceInfo(client=client["name"], used_bytes=total_bytes)

@app.get("/debug", response_model=Dict[str, Any])
def debug_info(server=Depends(get_server)):
    """Return various runtime and server diagnostics."""
    logger.info("Gathering debug information")
    debug = {}
    # Versions & Python env
    debug["python_version"] = sys.version
    debug["platform"] = platform.platform()
    try:
        debug["fastapi_version"] = getattr(FastAPI, "__version__", "?")
    except Exception as e:
        logger.error("Error retrieving FastAPI version: %s", e)
        debug["fastapi_version"] = "?"
    try:
        debug["urbackup_api_version"] = getattr(urbackup_api, '__version__', '?')
    except Exception as e:
        logger.error("Error retrieving urbackup_api version: %s", e)
        debug["urbackup_api_version"] = "?"
    # UrBackup config (mask password)
    debug["urbackup_config"] = {
        "url": URBACKUP_URL,
        "user": URBACKUP_USER,
        "pass": "***"
    }
    # Connection/server info
    try:
        status = server.get_status()
        debug["urbackup_status"] = status
    except Exception as e:
        logger.error("Error retrieving UrBackup status: %s", e)
        debug["urbackup_status"] = f"Erreur: {e}"

    try:
        clients = status["clients"] if "clients" in status else status
        debug["urbackup_clients"] = clients[:10]
    except Exception as e:
        logger.error("Error retrieving UrBackup clients: %s", e)
        debug["urbackup_clients"] = f"Erreur: {e}"

    return debug
