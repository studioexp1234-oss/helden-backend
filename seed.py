"""
Seed script om de 19 automations in te laden in de database.
Draai met: python seed.py
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import async_session_maker, init_db
from app.models import Automation


# De 19 automations
AUTOMATIONS = [
    # INBOUND (6)
    {
        "slug": "inbound-whatsapp-quote",
        "name": "WhatsApp → Auto Quote",
        "category": "INBOUND",
        "channel": "WhatsApp",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Quote",
        "trigger_desc": "New WhatsApp message received",
        "description": "Qualification questions via bot → lead scored → auto quote PDF generated → deal created in HubSpot"
    },
    {
        "slug": "inbound-chat-meeting",
        "name": "Website Chat → Meeting",
        "category": "INBOUND",
        "channel": "Chat",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Appointment",
        "trigger_desc": "Visitor starts chat on website",
        "description": "Qualification bot → warm lead detected → meeting planner link sent → appointment synced to sales calendar"
    },
    {
        "slug": "inbound-chat-whatsapp-handoff",
        "name": "Chat → WhatsApp Handoff",
        "category": "INBOUND",
        "channel": "Chat",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "WhatsApp Lead",
        "trigger_desc": "Visitor starts chat on website",
        "description": "Qualification bot → redirect to WhatsApp for deeper intake → WhatsApp flow continues"
    },
    {
        "slug": "inbound-mail-soap-opera",
        "name": "Mail Soap Opera → Demo",
        "category": "INBOUND",
        "channel": "Mail",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Appointment",
        "trigger_desc": "Website form submission",
        "description": "5-part soap opera email sequence → demo CTA in email 4 → HubSpot pipeline updated on click → reminder if no action"
    },
    {
        "slug": "inbound-mail-followup",
        "name": "Mail Actions → Follow-up",
        "category": "INBOUND",
        "channel": "Mail",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Appointment",
        "trigger_desc": "Lead opens email but does not book",
        "description": "Behavior-based follow-up triggered → personalized follow-up mail → meeting planner CTA → reminder"
    },
    {
        "slug": "inbound-auto-quote",
        "name": "Auto Quote Generator",
        "category": "INBOUND",
        "channel": "All",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Quote",
        "trigger_desc": "Lead completes qualification flow",
        "description": "Data collected → quote template populated → PDF generated → sent via email and/or WhatsApp → deal created in HubSpot"
    },
    
    # OUTBOUND (6)
    {
        "slug": "outbound-mail-cold",
        "name": "Cold Mail → Demo",
        "category": "OUTBOUND",
        "channel": "Mail",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Appointment",
        "trigger_desc": "Contact list uploaded",
        "description": "Cold email → follow-up → breakup email → demo CTA → HubSpot deal on response"
    },
    {
        "slug": "outbound-linkedin-cold",
        "name": "LinkedIn Cold → Appointment",
        "category": "OUTBOUND",
        "channel": "LinkedIn",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Appointment",
        "trigger_desc": "New LinkedIn connection accepted",
        "description": "Automated 3-message sequence → meeting planner link in message 3 → appointment synced to Google Calendar"
    },
    {
        "slug": "outbound-whatsapp-cold",
        "name": "WhatsApp Cold → Appointment",
        "category": "OUTBOUND",
        "channel": "WhatsApp",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Appointment",
        "trigger_desc": "Manual start on contact segment",
        "description": "Cold WhatsApp message → qualification question → meeting planner link → calendar sync"
    },
    {
        "slug": "outbound-mining-phones",
        "name": "Contact Mining → Phones",
        "category": "OUTBOUND",
        "channel": "Actions",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Enriched contact list",
        "trigger_desc": "Manual start on target segment",
        "description": "Scrape phone numbers → enrich contact data → load into WhatsApp or call outreach flow"
    },
    {
        "slug": "outbound-mining-emails",
        "name": "Contact Mining → Emails",
        "category": "OUTBOUND",
        "channel": "Mail",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Verified email list",
        "trigger_desc": "Manual start on target segment",
        "description": "Scrape email addresses → verify and enrich → load into cold mail sequence"
    },
    {
        "slug": "outbound-mining-linkedin",
        "name": "Contact Mining → LinkedIn",
        "category": "OUTBOUND",
        "channel": "LinkedIn",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "LinkedIn connections",
        "trigger_desc": "Manual start on target segment",
        "description": "Scrape LinkedIn profiles → import to outreach tool → cold messaging sequence"
    },
    
    # AFTERSALES (7)
    {
        "slug": "aftersales-chat-feedback",
        "name": "Chat Feedback Collection",
        "category": "AFTERSALES",
        "channel": "WhatsApp",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Feedback score",
        "trigger_desc": "Deal closed (Won) in HubSpot",
        "description": "Automated WhatsApp message → feedback question → score logged → if score ≥4 trigger upsell flow"
    },
    {
        "slug": "aftersales-chat-upsell",
        "name": "Chat Up/Cross-sell Flow",
        "category": "AFTERSALES",
        "channel": "WhatsApp",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "New deal",
        "trigger_desc": "Feedback score ≥4 via chat",
        "description": "Upsell message sent → relevant offer presented → meeting planner or quote triggered"
    },
    {
        "slug": "aftersales-mail-feedback",
        "name": "Mail Feedback → Upsell",
        "category": "AFTERSALES",
        "channel": "Mail",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Upsell deal",
        "trigger_desc": "Deal closed (Won) in HubSpot",
        "description": "Feedback email → form completed → if score ≥4 upsell email triggered → new HubSpot deal created"
    },
    {
        "slug": "aftersales-mail-upsell",
        "name": "Mail Up/Cross-sell Campaign",
        "category": "AFTERSALES",
        "channel": "Mail",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "New deal",
        "trigger_desc": "Score ≥4 or manual segment",
        "description": "Personalized upsell email → offer → meeting planner CTA → HubSpot deal on response"
    },
    {
        "slug": "aftersales-partner-network",
        "name": "Partner Network Activation",
        "category": "AFTERSALES",
        "channel": "Actions",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Referral deal",
        "trigger_desc": "Game Day participant completes session",
        "description": "Automated follow-up → partner proposition → intake flow if interested → referral deal in HubSpot"
    },
    {
        "slug": "aftersales-gamedays",
        "name": "Game Days Follow-up",
        "category": "AFTERSALES",
        "channel": "Actions",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Repeat booking",
        "trigger_desc": "Game Day completed",
        "description": "Post-event follow-up → feedback collected → next Game Day invitation or upsell sent"
    },
    {
        "slug": "aftersales-gameplan",
        "name": "Gameplan Delivery",
        "category": "AFTERSALES",
        "channel": "Actions",
        "status": "idea",
        "runs": 0,
        "conversions": 0,
        "last_run": "—",
        "output": "Gameplan + Appointment",
        "trigger_desc": "Client reaches milestone",
        "description": "Automated gameplan document sent → follow-up call scheduled → progress tracked in HubSpot"
    },
]


async def seed_automations():
    """Seed de automations in de database."""
    await init_db()
    
    async with async_session_maker() as session:
        # Check al bestaande automations
        from sqlalchemy import select
        result = await session.execute(select(Automation))
        existing = result.scalars().all()
        
        if existing:
            print(f"⚠️  Er zijn al {len(existing)} automations in de database.")
            print("   Wil je doorgaan? ( Alle bestaande worden overschreven met status 'idea')")
            # Update bestaande naar idea status
            for a in existing:
                a.status = "idea"
                a.runs = 0
                a.conversions = 0
                a.last_run = "—"
            await session.commit()
            print("   Alle bestaande automations gereset naar 'idea'.")
        
        # Voeg nieuwe toe of update bestaande
        for auto_data in AUTOMATIONS:
            result = await session.execute(
                select(Automation).where(Automation.slug == auto_data["slug"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update bestaande
                for key, value in auto_data.items():
                    setattr(existing, key, value)
            else:
                # Nieuwe toevoegen
                automation = Automation(**auto_data)
                session.add(automation)
        
        await session.commit()
        
        # Tel aantal
        result = await session.execute(select(Automation))
        all_automations = result.scalars().all()
        
        print(f"\n✅ Klaar! {len(all_automations)} automations in database.")
        print("\nVerdeling:")
        categories = {}
        for a in all_automations:
            categories[a.category] = categories.get(a.category, 0) + 1
        for cat, count in categories.items():
            print(f"  - {cat}: {count}")


if __name__ == "__main__":
    print("🌱 Seeding automations...")
    asyncio.run(seed_automations())
