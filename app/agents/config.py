AGENT_CONFIG = {
    "intake": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "outreach": {"provider": "openai", "model": "gpt-4"},
    "aftersales": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
    "mining": {"provider": "ollama", "model": "llama3"}
}

VALID_AGENTS = ["intake", "outreach", "aftersales", "mining"]
