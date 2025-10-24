"""
Working Healthcare.gov API Integration
Successfully retrieves real insurance data using your API key
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json
from datetime import datetime
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

class HealthcareGovWorking:
    """Working Healthcare.gov API client that successfully retrieves data"""
    
    def __init__(self):
        self.api_key = os.getenv('healthcareAPI')
        self.base_url = "https://marketplace.api.healthcare.gov/api/v1"
        self.session = None
        
        if not self.api_key:
            print("WARNING: No API key found. Set 'healthcareAPI' in .env file")
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def get_issuers(self, state: str = "CA") -> List[Dict]:
        """Get insurance issuers (carriers) - This endpoint works!"""
        try:
            endpoint = f"{self.base_url}/issuers"
            params = {"state": state}
            headers = {"apikey": self.api_key} if self.api_key else {}
            
            async with self.session.get(endpoint, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    issuers = data.get("issuers", [])
                    print(f"[SUCCESS] Retrieved {len(issuers)} issuers from Healthcare.gov for {state}")
                    return issuers
                else:
                    error_text = await response.text()
                    print(f"[ERROR] Issuers API error: {response.status} - {error_text}")
                    return []
                    
        except Exception as e:
            print(f"[ERROR] Error fetching issuers: {e}")
            return []
    
    async def get_articles(self) -> List[Dict]:
        """Get Healthcare.gov articles - Public API, no auth required"""
        try:
            endpoint = "https://www.healthcare.gov/api/articles.json"
            
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    print(f"[SUCCESS] Retrieved {len(articles)} articles from Healthcare.gov")
                    return articles
                else:
                    print(f"[ERROR] Articles API error: {response.status}")
                    return []
                    
        except Exception as e:
            print(f"[ERROR] Error fetching articles: {e}")
            return []
    
    async def get_glossary(self) -> List[Dict]:
        """Get Healthcare.gov glossary - Public API, no auth required"""
        try:
            endpoint = "https://www.healthcare.gov/api/glossary.json"
            
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    glossary = data.get("glossary", [])
                    print(f"[SUCCESS] Retrieved {len(glossary)} glossary terms from Healthcare.gov")
                    return glossary
                else:
                    print(f"[ERROR] Glossary API error: {response.status}")
                    return []
                    
        except Exception as e:
            print(f"[ERROR] Error fetching glossary: {e}")
            return []
    
    async def get_plans_by_issuer(self, issuer_id: str) -> List[Dict]:
        """Get plans for a specific issuer - Try different approaches"""
        try:
            # Try different endpoint formats
            endpoints = [
                f"{self.base_url}/plans/issuer/{issuer_id}",
                f"{self.base_url}/issuers/{issuer_id}/plans",
                f"{self.base_url}/plans?issuer_id={issuer_id}"
            ]
            
            headers = {"apikey": self.api_key} if self.api_key else {}
            
            for endpoint in endpoints:
                try:
                    async with self.session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            plans = data.get("plans", [])
                            print(f"[SUCCESS] Retrieved {len(plans)} plans for issuer {issuer_id}")
                            return plans
                        elif response.status != 404:
                            print(f"  Endpoint {endpoint}: Status {response.status}")
                            
                except Exception as e:
                    print(f"  Endpoint {endpoint}: Error {e}")
            
            return []
                    
        except Exception as e:
            print(f"[ERROR] Error fetching plans for issuer {issuer_id}: {e}")
            return []
    
    async def get_comprehensive_data(self, states: List[str] = None) -> Dict:
        """Get comprehensive data from Healthcare.gov"""
        if states is None:
            states = ["CA", "NY", "TX", "FL", "IL"]
        
        all_data = {
            "timestamp": datetime.now().isoformat(),
            "states": states,
            "issuers": {},
            "articles": [],
            "glossary": []
        }
        
        print("=" * 60)
        print("HEALTHCARE.GOV COMPREHENSIVE DATA COLLECTION")
        print("=" * 60)
        
        # Get articles and glossary (public data)
        print("\n1. Fetching public data...")
        all_data["articles"] = await self.get_articles()
        all_data["glossary"] = await self.get_glossary()
        
        # Get issuers for each state
        print("\n2. Fetching issuers by state...")
        for state in states:
            print(f"\n   State: {state}")
            issuers = await self.get_issuers(state)
            all_data["issuers"][state] = issuers
            
            # Try to get plans for each issuer
            for issuer in issuers[:3]:  # Limit to first 3 issuers per state
                issuer_id = issuer.get("id")
                issuer_name = issuer.get("name", "Unknown")
                
                if issuer_id:
                    print(f"     Getting plans for {issuer_name}...")
                    plans = await self.get_plans_by_issuer(issuer_id)
                    if plans:
                        issuer["plans"] = plans
                        print(f"       Found {len(plans)} plans")
                    else:
                        print(f"       No plans found")
        
        return all_data
    
    def save_data(self, data: Dict, filename: str = None) -> str:
        """Save data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"healthcare_gov_complete_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"[SUCCESS] Data saved to {filename}")
        return filename
    
    def analyze_data(self, data: Dict) -> Dict:
        """Analyze the collected data"""
        analysis = {
            "total_articles": len(data.get("articles", [])),
            "total_glossary_terms": len(data.get("glossary", [])),
            "states_analyzed": len(data.get("states", [])),
            "total_issuers": 0,
            "total_plans": 0,
            "issuers_by_state": {},
            "top_issuers": []
        }
        
        # Analyze issuers
        for state, issuers in data.get("issuers", {}).items():
            analysis["issuers_by_state"][state] = len(issuers)
            analysis["total_issuers"] += len(issuers)
            
            # Count plans
            for issuer in issuers:
                plans = issuer.get("plans", [])
                analysis["total_plans"] += len(plans)
        
        # Get top issuers
        issuer_counts = {}
        for state, issuers in data.get("issuers", {}).items():
            for issuer in issuers:
                name = issuer.get("name", "Unknown")
                issuer_counts[name] = issuer_counts.get(name, 0) + 1
        
        analysis["top_issuers"] = sorted(issuer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return analysis

async def main():
    """Main function to demonstrate the working API"""
    print("=" * 80)
    print("HEALTHCARE.GOV API - WORKING INTEGRATION")
    print("=" * 80)
    
    async with HealthcareGovWorking() as api:
        if not api.api_key:
            print("ERROR: No API key found. Please set 'healthcareAPI' in .env file")
            return
        
        print(f"API Key: {api.api_key[:10]}...{api.api_key[-5:]}")
        
        # Get comprehensive data
        data = await api.get_comprehensive_data()
        
        # Save data
        filename = api.save_data(data)
        
        # Analyze data
        analysis = api.analyze_data(data)
        
        print("\n" + "=" * 60)
        print("DATA ANALYSIS")
        print("=" * 60)
        print(f"Total Articles: {analysis['total_articles']}")
        print(f"Total Glossary Terms: {analysis['total_glossary_terms']}")
        print(f"States Analyzed: {analysis['states_analyzed']}")
        print(f"Total Issuers: {analysis['total_issuers']}")
        print(f"Total Plans: {analysis['total_plans']}")
        
        print(f"\nIssuers by State:")
        for state, count in analysis['issuers_by_state'].items():
            print(f"  {state}: {count} issuers")
        
        print(f"\nTop Issuers:")
        for issuer, count in analysis['top_issuers']:
            print(f"  {issuer}: {count} states")
        
        print(f"\nData saved to: {filename}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
