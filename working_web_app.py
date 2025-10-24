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

app = FastAPI(title="Health Insurance AI Platform", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Database configuration
DATABASE_PATH = "insurance_platform.db"

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
        
        print(f"Search query: {query}")
        print(f"Max premium: {max_premium}")
        print(f"Coverage type: {coverage_type}")
        
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
            
            if coverage_type:
                conditions.append("p.coverage_type = ?")
                params.append(coverage_type)
            
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

if __name__ == "__main__":
    print("=" * 60)
    print("HEALTH INSURANCE AI PLATFORM - WORKING VERSION")
    print("=" * 60)
    print("Starting web application...")
    print("Open your browser and go to: http://localhost:8000")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
