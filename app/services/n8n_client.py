"""
n8n Webhook Client.
Triggered automations via n8n webhooks.
"""
import httpx
from typing import Optional


async def trigger_webhook(base_url: str, slug: str, payload: Optional[dict] = None) -> dict:
    """
    Trigger een n8n webhook.
    
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
