"""
n8n API Client.
Handles workflow creation, webhooks, and execution data.
"""
import httpx
import os
from typing import Optional


async def get_n8n_client():
    """Get N8N API client with auth from settings."""
    base_url = os.getenv("N8N_BASE_URL", "").replace("https://", "http://")
    api_key = os.getenv("N8N_API_KEY", "")
    
    if not base_url:
        return None, None
    
    headers = {}
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    
    return base_url, headers


async def create_workflow(name: str, trigger_webhook_url: str = "") -> dict:
    """
    Create a new workflow in N8N.
    
    Args:
        name: Workflow name
        trigger_webhook_url: Optional webhook URL for the trigger
    
    Returns:
        dict with workflow_id and status
    """
    base_url, headers = await get_n8n_client()
    
    if not base_url:
        return {"status": "error", "message": "N8N not configured"}
    
    # Default workflow with a Manual Trigger node
    workflow_data = {
        "name": name,
        "nodes": [
            {
                "id": "1",
                "name": "Manual Trigger",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [250, 300],
                "parameters": {}
            }
        ],
        "connections": {},
        "settings": {
            "executionOrder": "v1"
        },
        "staticData": None,
        "tags": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/rest/workflows",
                json=workflow_data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "status": "success",
                    "workflow_id": data.get("id"),
                    "workflow_url": f"{base_url}/workflow/{data.get('id')}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"N8N API returned {response.status_code}",
                    "details": response.text[:200]
                }
    except httpx.ConnectError:
        return {"status": "error", "message": f"N8N unreachable at {base_url}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_workflow(workflow_id: str) -> dict:
    """Get workflow details from N8N."""
    base_url, headers = await get_n8n_client()
    
    if not base_url:
        return {"status": "error", "message": "N8N not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/rest/workflows/{workflow_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return {"status": "success", "data": response.json()}
            else:
                return {"status": "error", "message": f"N8N returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_workflow_executions(workflow_id: str, limit: int = 10) -> dict:
    """Get execution history for a workflow."""
    base_url, headers = await get_n8n_client()
    
    if not base_url:
        return {"status": "error", "message": "N8N not configured"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}/rest/executions",
                params={"workflowId": workflow_id, "limit": limit},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "executions": data.get("data", [])
                }
            else:
                return {"status": "error", "message": f"N8N returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def trigger_webhook(base_url: str, slug: str, payload: Optional[dict] = None) -> dict:
    """
    Trigger an n8n webhook.
    
    Args:
        base_url: n8n basis URL (bv. http://n8n:5678)
        slug: automation slug (bv. "inbound-whatsapp-quote")
        payload: optionele payload voor de webhook
    
    Returns:
        dict met status en response
    """
    if not base_url:
        return {"status": "error", "message": "n8n base URL not configured"}
    
    webhook_url = f"{base_url}/webhook/{slug}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=payload or {})
            
            if response.status_code in [200, 201, 202]:
                try:
                    data = response.json()
                    return {"status": "success", "data": data}
                except:
                    return {"status": "success", "data": {"message": "Webhook triggered"}}
            else:
                return {
                    "status": "error", 
                    "message": f"n8n returned {response.status_code}",
                    "details": response.text[:200]
                }
    except httpx.ConnectError:
        return {"status": "error", "message": f"n8n unreachable at {base_url}"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "n8n request timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
