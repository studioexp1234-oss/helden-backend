"""
Unified LLM Client voor Anthropic, OpenAI en Ollama.
Gebruikt httpx.AsyncClient voor async HTTP calls.
"""
import httpx
from typing import Optional
from app.agents.prompts import AGENT_PROMPTS


async def chat_completion(
    provider: str,
    model: str,
    messages: list,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    agent_id: Optional[str] = None
) -> str:
    """
    Unified chat completion voor alle LLM providers.
    
    Args:
        provider: "anthropic", "openai", of "ollama"
        model: model naam
        messages: lijst van messages [{"role": "user", "content": "..."}]
        api_key: API key voor de provider
        base_url: basis URL (nodig voor Ollama)
        agent_id: agent ID voor system prompt
    
    Returns:
        Response text string
    """
    if provider == "anthropic":
        return await _anthropic_chat(model, messages, api_key, agent_id)
    elif provider == "openai":
        return await _openai_chat(model, messages, api_key, agent_id)
    elif provider == "ollama":
        return await _ollama_chat(model, messages, base_url, agent_id)
    else:
        return f"Unknown provider: {provider}"


async def _anthropic_chat(model: str, messages: list, api_key: str, agent_id: Optional[str]) -> str:
    """Anthropic Claude API."""
    if not api_key:
        return "Anthropic API key not configured"
    
    system_prompt = AGENT_PROMPTS.get(agent_id, "") if agent_id else ""
    
    # Filter messages en voeg system prompt toe
    anthropic_messages = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") != "system"]
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": anthropic_messages
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["content"][0]["text"]
            else:
                return f"Anthropic API error: {resp.status_code} - {resp.text}"
    except httpx.ConnectError:
        return "Anthropic API unreachable"
    except Exception as e:
        return f"Anthropic error: {str(e)}"


async def _openai_chat(model: str, messages: list, api_key: str, agent_id: Optional[str]) -> str:
    """OpenAI ChatGPT API."""
    if not api_key:
        return "OpenAI API key not configured"
    
    system_prompt = AGENT_PROMPTS.get(agent_id, "") if agent_id else ""
    
    # Bouw messages met system prompt
    openai_messages = []
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})
    openai_messages.extend([{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") != "system"])
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "content-type": "application/json"
                },
                json={
                    "model": model,
                    "messages": openai_messages,
                    "max_tokens": 1024
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"OpenAI API error: {resp.status_code} - {resp.text}"
    except httpx.ConnectError:
        return "OpenAI API unreachable"
    except Exception as e:
        return f"OpenAI error: {str(e)}"


async def _ollama_chat(model: str, messages: list, base_url: Optional[str], agent_id: Optional[str]) -> str:
    """Ollama lokale API."""
    ollama_url = base_url or "http://ollama:11434"
    
    system_prompt = AGENT_PROMPTS.get(agent_id, "") if agent_id else ""
    
    # Bouw messages met system prompt
    ollama_messages = []
    if system_prompt:
        ollama_messages.append({"role": "system", "content": system_prompt})
    ollama_messages.extend([{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") != "system"])
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "stream": False
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["message"]["content"]
            else:
                return f"Ollama error: {resp.status_code} - {resp.text}"
    except httpx.ConnectError:
        return f"Ollama unreachable at {ollama_url}"
    except Exception as e:
        return f"Ollama error: {str(e)}"
