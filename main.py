from fastapi import FastAPI, HTTPException, Path, Request
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


def get_urbackup_server():
    return urbackup_api.urbackup_server(URBACKUP_URL, URBACKUP_USER, URBACKUP_PASS)

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
def get_status():
    """Return overall UrBackup server status."""
    try:
        logger.info("Fetching server status")
        server = get_urbackup_server()
        return server.get_status()
    except Exception as e:
        logger.error("Error in get_status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/clients", response_model=List[ClientSummary])
def get_clients():
    """List all configured clients with their identifiers."""
    try:
        logger.info("Listing clients")
        server = get_urbackup_server()
        status = server.get_status()
        clients = status["clients"] if "clients" in status else status
        return [ClientSummary(name=c["name"], id=c["id"]) for c in clients]
    except Exception as e:
        logger.error("Error in get_clients: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/client/{client_identifier}", response_model=Dict[str, Any])
def get_client_detail(client_identifier: Union[str, int] = Path(...)):
    """Retrieve detailed information for a specific client."""
    try:
        logger.info("Retrieving client detail for %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return client
    except Exception as e:
        logger.error("Error in get_client_detail: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/full", response_model=BackupResult)
def launch_full_backup(req: BackupRequest):
    """Start a full file backup for the specified client."""
    try:
        logger.info("Starting full file backup for %s", req.client)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.start_full_file_backup(client["id"]))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in launch_full_backup: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backup/image", response_model=BackupResult)
def launch_image_backup(req: BackupRequest):
    """Start a full image backup for the specified client."""
    try:
        logger.info("Starting full image backup for %s", req.client)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.start_full_image_backup(client["id"]))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in launch_image_backup: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backup/incremental", response_model=BackupResult)
def launch_incremental_backup(req: BackupRequest):
    """Start an incremental file backup for the specified client."""
    try:
        logger.info("Starting incremental file backup for %s", req.client)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.start_incremental_file_backup(client["id"]))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in launch_incremental_backup: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backups/{client_identifier}", response_model=List[Dict[str, Any]])
def get_client_backups(client_identifier: Union[str, int] = Path(...)):
    """List backups available for a client."""
    try:
        logger.info("Listing backups for %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_backups(client["id"])
    except Exception as e:
        logger.error("Error in get_client_backups: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backup/delete", response_model=BackupResult)
def delete_backup(req: BackupDeleteRequest):
    """Delete a specific backup belonging to a client."""
    try:
        logger.info("Deleting backup %s for client %s", req.backup_id, req.client)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.delete_backup(client["id"], req.backup_id))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in delete_backup: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/client/create", response_model=BackupResult)
def create_client(req: ClientCreateRequest):
    """Create a new client on the UrBackup server."""
    try:
        logger.info("Creating client %s", req.client)
        server = get_urbackup_server()
        ok = bool(server.add_client(req.client))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in create_client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/client/delete", response_model=BackupResult)
def delete_client(req: ClientDeleteRequest):
    """Remove an existing client from the server."""
    try:
        logger.info("Deleting client %s", req.client)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.remove_client(client["id"]))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in delete_client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/client/rename", response_model=BackupResult)
def rename_client(req: ClientRenameRequest):
    """Rename an existing client."""
    try:
        logger.info("Renaming client %s to %s", req.old, req.new)
        server = get_urbackup_server()
        client = resolve_client(server, req.old)
        ok = bool(server.rename_client(client["id"], req.new))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in rename_client: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/settings/{client_identifier}", response_model=Dict[str, Any])
def get_client_settings(client_identifier: Union[str, int] = Path(...)):
    """Retrieve settings for a given client."""
    try:
        logger.info("Getting settings for client %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_settings(client["id"])
    except Exception as e:
        logger.error("Error in get_client_settings: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/client/settings/change", response_model=BackupResult)
def set_client_setting(req: ClientSettingChangeRequest):
    """Update a specific client setting."""
    try:
        logger.info("Changing setting %s for client %s", req.key, req.client)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.change_client_setting(client["id"], req.key, req.new_value))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in set_client_setting: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/client/authkey/{client_identifier}", response_model=AuthKeyInfo)
def get_client_authkey(client_identifier: Union[str, int] = Path(...)):
    """Get the authentication key for a client."""
    try:
        logger.info("Getting authkey for client %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return AuthKeyInfo(authkey=server.get_client_authkey(client["id"]))
    except Exception as e:
        logger.error("Error in get_client_authkey: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/{client_identifier}", response_model=List[Dict[str, Any]])
def get_client_logs(client_identifier: Union[str, int] = Path(...)):
    """Retrieve logs for a client."""
    try:
        logger.info("Getting logs for client %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_logs(client["id"])
    except Exception as e:
        logger.error("Error in get_client_logs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/quota", response_model=QuotaInfo)
def get_client_quota(client_identifier: Union[str, int] = Path(...)):
    """Get the configured quota for a client."""
    try:
        logger.info("Getting quota for client %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        settings = server.get_client_settings(client["id"])
        quota = settings.get("quota", {}).get("value")
        return QuotaInfo(client=client["name"], quota_bytes=int(quota) if quota is not None else None)
    except Exception as e:
        logger.error("Error in get_client_quota: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/quota", response_model=BackupResult)
def set_client_quota(req: QuotaRequest):
    """Set the quota for a client."""
    try:
        logger.info("Setting quota for client %s to %s", req.client, req.quota_bytes)
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        ok = bool(server.change_client_setting(client["id"], "quota", str(req.quota_bytes)))
        return BackupResult(success=ok)
    except Exception as e:
        logger.error("Error in set_client_quota: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/used_space", response_model=UsedSpaceInfo)
def get_client_used_space(client_identifier: Union[str, int] = Path(...)):
    """Compute total space used by a client's backups."""
    try:
        logger.info("Calculating used space for client %s", client_identifier)
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        backups = server.get_client_backups(client["id"])
        total_bytes = sum(b.get("total_bytes", 0) for b in backups if b.get("total_bytes") is not None)
        return UsedSpaceInfo(client=client["name"], used_bytes=total_bytes)
    except Exception as e:
        logger.error("Error in get_client_used_space: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug", response_model=Dict[str, Any])
def debug_info():
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
        server = get_urbackup_server()
        # Ping API (status)
        try:
            status = server.get_status()
            debug["urbackup_status"] = status
        except Exception as e:
            logger.error("Error retrieving UrBackup status: %s", e)
            debug["urbackup_status"] = f"Erreur: {e}"

        # Liste (partielle) des clients
        try:
            clients = status["clients"] if "clients" in status else status
            debug["urbackup_clients"] = clients[:10]
        except Exception as e:
            logger.error("Error retrieving UrBackup clients: %s", e)
            debug["urbackup_clients"] = f"Erreur: {e}"
    except Exception as e:
        logger.error("Error connecting to UrBackup server: %s", e)
        debug["urbackup_server_connection"] = f"Erreur: {e}"

    return debug
