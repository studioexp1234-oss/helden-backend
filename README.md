# Helden Automation Backend

FastAPI backend voor Helden Automation Control Center.

## Structuur

```
helden-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLAlchemy setup
│   ├── models.py            # Database modellen
│   ├── routers/             # API endpoints
│   │   ├── automations.py
│   │   ├── agents.py
│   │   ├── activity.py
│   │   └── settings.py
│   ├── agents/
│   │   ├── config.py        # Agent → LLM mapping
│   │   ├── prompts.py       # System prompts
│   │   └── llm_client.py    # Unified LLM client
│   └── services/
│       └── n8n_client.py    # n8n webhook client
├── seed.py                  # Seed script voor automations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Installatie

```bash
# Installeer dependencies
pip install -r requirements.txt

# Initialiseer database en seed
python seed.py

# Start de server
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
# Start met Docker
docker-compose up -d

# Logs bekijken
docker-compose logs -f helden-backend

# Stoppen
docker-compose down
```

## API Endpoints

| Endpoint | Method | Functie |
|----------|--------|---------|
| `/api/automations` | GET | Lijst van automations |
| `/api/automations/{slug}` | GET | Eén automation |
| `/api/automations` | POST | Nieuwe automation |
| `/api/automations/{slug}` | PUT | Update automation |
| `/api/automations/{slug}` | DELETE | Verwijder automation |
| `/api/automations/{slug}/trigger` | POST | Trigger naar n8n |
| `/api/agents/{agent_id}/chat` | POST | Chat met agent |
| `/api/agents/{agent_id}/chat` | GET | Chat history |
| `/api/activity` | GET | Activity feed |
| `/api/activity` | POST | Log activity (voor n8n) |
| `/api/settings` | GET | Alle settings |
| `/api/settings` | PUT | Bulk update settings |

## Agents

- **intake** → Anthropic Claude (inbound leads, quotes)
- **outreach** → OpenAI GPT-4 (cold outreach)
- **aftersales** → Anthropic Claude (feedback, upsell)
- **mining** → Ollama (contact scraping)

## Environment Variabels

Kopieer `.env.example` naar `.env` en vul in:

```
ANTHROPIC_API_KEY=sk-ant-xxxx
OPENAI_API_KEY=sk-xxxx
OLLAMA_BASE_URL=http://ollama:11434
N8N_BASE_URL=http://n8n:5678
```

## Docs

OpenAPI docs zijn beschikbaar op: http://localhost:8000/docs
