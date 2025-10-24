"""
Working Health Insurance Web Application
"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
import aiosqlite
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
try:
    from dotenv import load_dotenv
    # Load variables from .env if present (project root)
    load_dotenv()
except Exception:
    pass

# Optional Groq SDK (used if available and base URL is Groq)
try:
    from groq import Groq  # type: ignore
except Exception:
    Groq = None  # Fallback to HTTP path

app = FastAPI(title="Health Insurance AI Platform", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Database configuration
DATABASE_PATH = "insurance_platform.db"

# Simple in-memory rate limit store for chat (per IP)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 3
_rate_limiter: Dict[str, List[datetime]] = {}

# LLM provider configuration (Groq-first)
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GOQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

async def call_openai_chat(messages: List[Dict[str, str]]) -> str:
    """Call OpenAI Chat Completions API and return assistant text.

    Falls back with a helpful message if API key is not set or request fails.
    """
    # Re-read env each call so newly-set keys are picked up without restart
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GOQ_API_KEY") or GROQ_API_KEY
    base_url = os.getenv("GROQ_BASE_URL", GROQ_BASE_URL)
    model = os.getenv("GROQ_MODEL", GROQ_MODEL)

    if not api_key:
        return (
            "AI is not configured yet. Set GROQ_API_KEY in your environment/.env. "
            "Meanwhile, try using the search and filters above."
        )

    # If using Groq API and SDK is present, prefer SDK (more compatible)
    if "api.groq.com" in base_url and Groq is not None:
        try:
            # Groq SDK is sync; run in thread to avoid blocking loop
            from functools import partial
            loop = asyncio.get_event_loop()
            def _call_groq():
                client = Groq(api_key=api_key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2,
                )
                return resp
            resp = await loop.run_in_executor(None, _call_groq)
            try:
                return resp.choices[0].message.content or ""
            except Exception:
                return ""
        except Exception as e:
            print(f"Groq SDK call error: {e}")
            # fall through to HTTP path as backup

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"Provider error {resp.status}: {text}")
                    return "Sorry, I couldn't reach the AI service right now. Please try again."
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"Provider call error: {e}")
        return "Sorry, something went wrong contacting the AI service."

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with search interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/search")
async def search_insurance(request: Request):
    """Search for insurance plans"""
    
    try:
        # Get request data
        data = await request.json()
        query = data.get('query', '')
        max_premium = data.get('max_premium')
        coverage_type = data.get('coverage_type')
        # New filters
        benefits_filter: List[str] = data.get('benefits') or []
        max_deductible = data.get('max_deductible')
        
        print(f"Search query: {query}")
        print(f"Max premium: {max_premium}")
        print(f"Coverage type: {coverage_type}")
        if benefits_filter:
            print(f"Benefits filter: {benefits_filter}")
        
        # Search for plans
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Build search conditions
            conditions = []
            params = []
            
            if query:
                query_lower = query.lower()
                if any(term in query_lower for term in ['low cost', 'cheap', 'affordable', 'budget']):
                    conditions.append("p.premium <= 500")
                elif any(term in query_lower for term in ['family', 'family coverage']):
                    conditions.append("p.coverage_type = 'family'")
                elif any(term in query_lower for term in ['dental', 'dental insurance', 'dental care']):
                    conditions.append("p.benefits LIKE '%dental%'")
                elif any(term in query_lower for term in ['vision', 'vision insurance', 'vision care']):
                    conditions.append("p.benefits LIKE '%vision%'")
                elif any(term in query_lower for term in ['mental health', 'mental', 'therapy']):
                    conditions.append("p.benefits LIKE '%mental%'")
                elif any(term in query_lower for term in ['maternity', 'pregnancy', 'prenatal']):
                    conditions.append("p.benefits LIKE '%maternity%'")
                elif any(term in query_lower for term in ['preventive', 'prevention', 'checkup']):
                    conditions.append("p.benefits LIKE '%preventive%'")
                elif any(term in query_lower for term in ['emergency', 'emergency care', 'urgent']):
                    conditions.append("p.benefits LIKE '%emergency%'")
                elif any(term in query_lower for term in ['prescription', 'drugs', 'medication']):
                    conditions.append("p.benefits LIKE '%prescription%'")
                elif any(term in query_lower for term in ['high deductible', 'hdhp', 'hsa']):
                    conditions.append("p.deductible >= 3000")
                else:
                    conditions.append("(p.name LIKE ? OR c.name LIKE ?)")
                    params.extend([f"%{query}%", f"%{query}%"])
            
            if max_premium:
                conditions.append("p.premium <= ?")
                params.append(max_premium)
            if max_deductible:
                conditions.append("p.deductible <= ?")
                params.append(max_deductible)
            
            if coverage_type:
                conditions.append("p.coverage_type = ?")
                params.append(coverage_type)

            # Benefits filter (match all selected benefits)
            for b in benefits_filter:
                b = str(b).lower().strip()
                if not b:
                    continue
                conditions.append("LOWER(p.benefits) LIKE ?")
                params.append(f"%{b}%")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor = await db.execute(f"""
                SELECT p.id, p.name, p.carrier_id, p.premium, p.deductible, 
                       p.coverage_type, p.network_type, p.benefits, p.exclusions, 
                       p.rating, p.last_updated, c.name as carrier_name
                FROM insurance_plans p
                LEFT JOIN carriers c ON p.carrier_id = c.id
                WHERE {where_clause}
                ORDER BY p.rating DESC, p.premium ASC
                LIMIT 100
            """, params)
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            plans = []
            for row in rows:
                plan_dict = dict(zip(columns, row))
                plan_dict['benefits'] = json.loads(plan_dict.get('benefits', '[]'))
                plan_dict['exclusions'] = json.loads(plan_dict.get('exclusions', '[]'))
                plans.append(plan_dict)
            
            print(f"Found {len(plans)} plans")
            
            return {
                "plans": plans,
                "total_found": len(plans),
                "data_freshness": "Fresh",
                "query_time": datetime.now().isoformat(),
                "recommendations": []  # Add empty recommendations to prevent errors
            }
            
    except Exception as e:
        print(f"Search error: {e}")
        return {
            "plans": [],
            "total_found": 0,
            "error": str(e),
            "data_freshness": "Error",
            "query_time": datetime.now().isoformat(),
            "recommendations": []  # Add empty recommendations to prevent errors
        }

@app.get("/api/plans/{plan_id}")
async def get_plan_details(plan_id: str):
    """Get detailed information about a specific plan"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, p.carrier_id, p.premium, p.deductible, 
                       p.coverage_type, p.network_type, p.benefits, p.exclusions, 
                       p.rating, p.last_updated, c.name as carrier_name
                FROM insurance_plans p
                LEFT JOIN carriers c ON p.carrier_id = c.id
                WHERE p.id = ?
            """, (plan_id,))
            
            row = await cursor.fetchone()
            if not row:
                return {"error": "Plan not found", "plan": None}
            
            columns = [description[0] for description in cursor.description]
            plan_data = dict(zip(columns, row))
            plan_data['benefits'] = json.loads(plan_data.get('benefits', '[]'))
            plan_data['exclusions'] = json.loads(plan_data.get('exclusions', '[]'))
            
            return {
                "success": True,
                "plan": plan_data
            }
            
    except Exception as e:
        return {"error": str(e), "plan": None}

@app.post("/api/compare")
async def compare_plans(request: Request):
    """Compare multiple plans side by side"""
    try:
        data = await request.json()
        plan_ids = data.get('plan_ids', [])
        
        if len(plan_ids) < 2:
            return {"error": "At least 2 plans required for comparison", "plans": []}
        
        if len(plan_ids) > 3:
            return {"error": "Maximum 3 plans allowed for comparison", "plans": []}
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            placeholders = ','.join(['?' for _ in plan_ids])
            cursor = await db.execute(f"""
                SELECT p.id, p.name, p.carrier_id, p.premium, p.deductible, 
                       p.coverage_type, p.network_type, p.benefits, p.exclusions, 
                       p.rating, p.last_updated, c.name as carrier_name
                FROM insurance_plans p
                LEFT JOIN carriers c ON p.carrier_id = c.id
                WHERE p.id IN ({placeholders})
            """, plan_ids)
            
            rows = await cursor.fetchall()
            if not rows:
                return {"error": "No plans found", "plans": []}
            
            columns = [description[0] for description in cursor.description]
            plans = []
            
            for row in rows:
                plan_data = dict(zip(columns, row))
                plan_data['benefits'] = json.loads(plan_data.get('benefits', '[]'))
                plan_data['exclusions'] = json.loads(plan_data.get('exclusions', '[]'))
                plans.append(plan_data)
            
            return {
                "success": True,
                "plans": plans,
                "comparison_summary": {
                    "total_plans": len(plans),
                    "price_range": {
                        "min_premium": min(p['premium'] for p in plans),
                        "max_premium": max(p['premium'] for p in plans),
                        "min_deductible": min(p['deductible'] for p in plans),
                        "max_deductible": max(p['deductible'] for p in plans)
                    }
                }
            }
            
    except Exception as e:
        return {"error": str(e), "plans": []}

@app.post("/api/calculate-cost")
async def calculate_total_cost(request: Request):
    """Calculate total annual cost for a plan"""
    try:
        data = await request.json()
        plan_id = data.get('plan_id')
        usage_scenario = data.get('usage_scenario', 'moderate')  # low, moderate, high
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                SELECT p.id, p.name, p.premium, p.deductible, p.coverage_type, 
                       p.network_type, c.name as carrier_name
                FROM insurance_plans p
                LEFT JOIN carriers c ON p.carrier_id = c.id
                WHERE p.id = ?
            """, (plan_id,))
            
            row = await cursor.fetchone()
            if not row:
                return {"error": "Plan not found", "cost_breakdown": None}
            
            columns = [description[0] for description in cursor.description]
            plan_data = dict(zip(columns, row))
            
            # Calculate costs based on usage scenario
            monthly_premium = plan_data['premium']
            annual_premium = monthly_premium * 12
            deductible = plan_data['deductible']
            
            # Estimate out-of-pocket costs based on usage
            usage_scenarios = {
                'low': {'copays': 200, 'coinsurance': 500},
                'moderate': {'copays': 800, 'coinsurance': 2000},
                'high': {'copays': 1500, 'coinsurance': 5000}
            }
            
            scenario = usage_scenarios.get(usage_scenario, usage_scenarios['moderate'])
            estimated_copays = scenario['copays']
            estimated_coinsurance = scenario['coinsurance']
            
            # Calculate total costs
            total_annual_cost = annual_premium + deductible + estimated_copays + estimated_coinsurance
            potential_savings = max(0, deductible - estimated_copays - estimated_coinsurance)
            
            cost_breakdown = {
                "plan_name": plan_data['name'],
                "carrier": plan_data['carrier_name'],
                "monthly_premium": monthly_premium,
                "annual_premium": annual_premium,
                "deductible": deductible,
                "estimated_copays": estimated_copays,
                "estimated_coinsurance": estimated_coinsurance,
                "total_annual_cost": total_annual_cost,
                "potential_savings": potential_savings,
                "usage_scenario": usage_scenario,
                "cost_per_month": round(total_annual_cost / 12, 2)
            }
            
            return {
                "success": True,
                "cost_breakdown": cost_breakdown
            }
            
    except Exception as e:
        return {"error": str(e), "cost_breakdown": None}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Chat endpoint that optionally uses recent search context.

    Body:
    {
      "messages": [{"role": "user"|"assistant"|"system", "content": str}],
      "search_context": {"query": str, "location": str, "max_premium": number}?,
      "top_plans": [{"id": str, "name": str, "carrier_name": str, "premium": number, "benefits": list}]?
    }
    """
    try:
        # Basic rate limiting by client IP
        client_ip = request.client.host if request.client else "anonymous"
        now = datetime.utcnow()
        history = _rate_limiter.get(client_ip, [])
        history = [t for t in history if (now - t).total_seconds() < RATE_LIMIT_WINDOW_SECONDS]
        if len(history) >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse({"error": "Too many requests. Please wait a moment."}, status_code=429)
        history.append(now)
        _rate_limiter[client_ip] = history

        body = await request.json()
        user_messages = body.get("messages", [])
        search_context = body.get("search_context")
        top_plans = body.get("top_plans", [])[:5]

        # Build system prompt and optional context
        system_prompt = (
            "You are Health Insurance Assistant. Answer clearly and concisely. "
            "If recommendations are requested, suggest filters (benefits, max premium, location). "
            "Do not invent plan details; only summarize from provided context."
        )

        context_sections: List[str] = []
        if search_context:
            context_sections.append(
                f"Search Context: query={search_context.get('query')}, "
                f"location={search_context.get('location')}, "
                f"max_premium={search_context.get('max_premium')}"
            )
        if top_plans:
            plan_lines = []
            for p in top_plans:
                benefits = ", ".join(p.get("benefits", [])[:4])
                plan_lines.append(
                    f"- {p.get('name')} ({p.get('carrier_name')}) • ${p.get('premium')}/mo • {benefits}"
                )
            context_sections.append("Top Plans:\n" + "\n".join(plan_lines))

        if context_sections:
            user_messages = user_messages[:]
            user_messages.insert(0, {"role": "system", "content": system_prompt + "\n\n" + "\n".join(context_sections)})
        else:
            user_messages = user_messages[:]
            user_messages.insert(0, {"role": "system", "content": system_prompt})

        assistant_text = await call_openai_chat(user_messages)
        return {"assistant_message": assistant_text}
    except Exception as e:
        print(f"Chat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    print("=" * 60)
    print("HEALTH INSURANCE AI PLATFORM - WORKING VERSION")
    print("=" * 60)
    print("Starting web application...")
    print("Open your browser and go to: http://localhost:8000")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
