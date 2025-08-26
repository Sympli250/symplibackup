from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel
from typing import Optional, Union, List, Dict, Any
import urbackup_api
import sys
import platform

URBACKUP_URL = "http://127.0.0.1:55414/x"
URBACKUP_USER = "admin"
URBACKUP_PASS = "Sherpa2025!"

app = FastAPI(title="UrBackup REST API Proxy")

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
    raise HTTPException(status_code=404, detail=f"Client '{identifier}' not found")

# ===== Pydantic Models =====

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

# ===== ROUTES =====

@app.get("/status")
def get_status():
    try:
        server = get_urbackup_server()
        return server.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clients")
def get_clients():
    try:
        server = get_urbackup_server()
        status = server.get_status()
        clients = status["clients"] if "clients" in status else status
        return [{"name": c["name"], "id": c["id"]} for c in clients]
    except Exception as e:
        print("Erreur dans /clients:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}")
def get_client_detail(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/full")
def launch_full_backup(req: BackupRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_full_file_backup(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/image")
def launch_image_backup(req: BackupRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_full_image_backup(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/incremental")
def launch_incremental_backup(req: BackupRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.start_incremental_file_backup(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backups/{client_identifier}")
def get_client_backups(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_backups(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backup/delete")
def delete_backup(req: BackupDeleteRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.delete_backup(client["id"], req.backup_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/create")
def create_client(req: ClientCreateRequest):
    try:
        server = get_urbackup_server()
        return server.add_client(req.client)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/delete")
def delete_client(req: ClientDeleteRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.remove_client(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/rename")
def rename_client(req: ClientRenameRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.old)
        return server.rename_client(client["id"], req.new)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/settings/{client_identifier}")
def get_client_settings(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_settings(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/settings/change")
def set_client_setting(req: ClientSettingChangeRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        return server.change_client_setting(client["id"], req.key, req.new_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/authkey/{client_identifier}")
def get_client_authkey(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return {"authkey": server.get_client_authkey(client["id"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs/{client_identifier}")
def get_client_logs(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        return server.get_client_logs(client["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/quota")
def get_client_quota(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        settings = server.get_client_settings(client["id"])
        quota = settings.get("quota", {}).get("value")
        return {"client": client["name"], "quota_bytes": int(quota) if quota is not None else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/client/quota")
def set_client_quota(req: QuotaRequest):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, req.client)
        result = server.change_client_setting(client["id"], "quota", str(req.quota_bytes))
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/client/{client_identifier}/used_space")
def get_client_used_space(client_identifier: Union[str, int] = Path(...)):
    try:
        server = get_urbackup_server()
        client = resolve_client(server, client_identifier)
        backups = server.get_client_backups(client["id"])
        total_bytes = sum(b.get("total_bytes", 0) for b in backups if b.get("total_bytes") is not None)
        return {"client": client["name"], "used_bytes": total_bytes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug")
def debug_info():
    debug = {}
    # Versions & Python env
    debug["python_version"] = sys.version
    debug["platform"] = platform.platform()
    try:
        debug["fastapi_version"] = getattr(FastAPI, "__version__", "?")
    except Exception:
        debug["fastapi_version"] = "?"
    try:
        debug["urbackup_api_version"] = getattr(urbackup_api, '__version__', '?')
    except Exception:
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
            debug["urbackup_status"] = f"Erreur: {e}"

        # Liste (partielle) des clients
        try:
            clients = status["clients"] if "clients" in status else status
            debug["urbackup_clients"] = clients[:10]
        except Exception as e:
            debug["urbackup_clients"] = f"Erreur: {e}"
    except Exception as e:
        debug["urbackup_server_connection"] = f"Erreur: {e}"

    return debug