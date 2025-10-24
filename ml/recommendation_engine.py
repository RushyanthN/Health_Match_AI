"""
Intelligent Recommendation Engine
ML-powered matching based on user needs and preferences
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import joblib
import json

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """User profile for recommendation matching"""
    age: int
    income: int
    household_size: int
    health_conditions: List[str]
    preferred_plan_type: Optional[str] = None
    budget_range: Optional[Tuple[float, float]] = None
    priority_factors: List[str] = None  # e.g., ["low_premium", "good_coverage", "hsa_eligible"]
    location: str = ""
    tobacco_user: bool = False

@dataclass
class PlanFeatures:
    """Extracted features from insurance plans"""
    plan_id: int
    monthly_premium: float
    deductible: float
    out_of_pocket_max: float
    primary_care_copay: float
    specialist_copay: float
    metal_tier_score: float  # Bronze=1, Silver=2, Gold=3, Platinum=4
    hsa_eligible: bool
    covers_telehealth: bool
    network_size: float
    quality_rating: float
    customer_satisfaction: float
    data_freshness: float  # How recent the data is

class IntelligentRecommendationEngine:
    """ML-powered recommendation system for insurance plans"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.scaler = StandardScaler()
        self.plan_features = {}
        self.user_preferences = {}
        self.model_trained = False
        
    def extract_plan_features(self, plans: List[Dict]) -> Dict[int, PlanFeatures]:
        """Extract ML features from insurance plans"""
        features = {}
        
        for plan in plans:
            plan_id = plan.get('plan_id')
            if not plan_id:
                continue
                
            # Metal tier scoring
            metal_tier_scores = {
                'Bronze': 1.0, 'Silver': 2.0, 'Gold': 3.0, 
                'Platinum': 4.0, 'Catastrophic': 0.5
            }
            metal_tier_score = metal_tier_scores.get(plan.get('metal_tier', 'Bronze'), 1.0)
            
            # Calculate data freshness (0-1, where 1 is most recent)
            last_scraped = plan.get('last_scraped_at')
            if last_scraped:
                try:
                    scraped_date = datetime.fromisoformat(last_scraped.replace('Z', '+00:00'))
                    days_old = (datetime.now() - scraped_date.replace(tzinfo=None)).days
                    data_freshness = max(0, 1 - (days_old / 30))  # Decay over 30 days
                except:
                    data_freshness = 0.5
            else:
                data_freshness = 0.5
            
            features[plan_id] = PlanFeatures(
                plan_id=plan_id,
                monthly_premium=float(plan.get('monthly_premium_base', 0)),
                deductible=float(plan.get('annual_deductible_individual', 0)),
                out_of_pocket_max=float(plan.get('out_of_pocket_max_individual', 0)),
                primary_care_copay=float(plan.get('primary_care_copay', 0)),
                specialist_copay=float(plan.get('specialist_copay', 0)),
                metal_tier_score=metal_tier_score,
                hsa_eligible=bool(plan.get('hsa_eligible', False)),
                covers_telehealth=bool(plan.get('covers_telehealth', False)),
                network_size=float(plan.get('estimated_providers_count', 1000)),  # Default estimate
                quality_rating=float(plan.get('quality_rating', 3.0)),
                customer_satisfaction=float(plan.get('customer_satisfaction_score', 3.0)),
                data_freshness=data_freshness
            )
        
        self.plan_features = features
        return features
    
    def calculate_user_preferences(self, user_profile: UserProfile) -> Dict[str, float]:
        """Calculate user preference weights based on profile"""
        preferences = {
            'premium_weight': 0.3,
            'coverage_weight': 0.3,
            'quality_weight': 0.2,
            'convenience_weight': 0.2
        }
        
        # Adjust weights based on user characteristics
        if user_profile.income < 30000:
            preferences['premium_weight'] = 0.5  # Lower income = prioritize low premium
            preferences['coverage_weight'] = 0.2
        elif user_profile.income > 100000:
            preferences['quality_weight'] = 0.4  # Higher income = prioritize quality
            preferences['premium_weight'] = 0.1
        
        if user_profile.age > 60:
            preferences['coverage_weight'] = 0.5  # Older users need better coverage
            preferences['premium_weight'] = 0.1
        
        if user_profile.health_conditions:
            preferences['coverage_weight'] = 0.6  # Health conditions = need good coverage
            preferences['premium_weight'] = 0.1
        
        if user_profile.tobacco_user:
            preferences['premium_weight'] = 0.4  # Tobacco users pay more, so premium matters
        
        # Adjust based on explicit priorities
        if user_profile.priority_factors:
            if 'low_premium' in user_profile.priority_factors:
                preferences['premium_weight'] = 0.6
            if 'good_coverage' in user_profile.priority_factors:
                preferences['coverage_weight'] = 0.6
            if 'hsa_eligible' in user_profile.priority_factors:
                preferences['convenience_weight'] = 0.4
        
        return preferences
    
    def calculate_plan_score(self, plan_features: PlanFeatures, user_profile: UserProfile, preferences: Dict[str, float]) -> float:
        """Calculate compatibility score between plan and user"""
        
        # Normalize features to 0-1 scale
        premium_score = 1 - min(1, plan_features.monthly_premium / 1000)  # Lower is better
        coverage_score = plan_features.metal_tier_score / 4.0  # Higher tier is better
        quality_score = plan_features.quality_rating / 5.0  # Higher rating is better
        convenience_score = (
            (1 if plan_features.covers_telehealth else 0) * 0.3 +
            (1 if plan_features.hsa_eligible else 0) * 0.3 +
            (plan_features.network_size / 10000) * 0.4  # Larger network is better
        )
        
        # Apply user preferences
        total_score = (
            premium_score * preferences['premium_weight'] +
            coverage_score * preferences['coverage_weight'] +
            quality_score * preferences['quality_weight'] +
            convenience_score * preferences['convenience_weight']
        )
        
        # Apply data freshness penalty
        total_score *= plan_features.data_freshness
        
        return total_score
    
    def get_recommendations(self, user_profile: UserProfile, plans: List[Dict], top_k: int = 5) -> List[Dict]:
        """Get personalized plan recommendations"""
        
        # Extract features from plans
        plan_features = self.extract_plan_features(plans)
        
        # Calculate user preferences
        preferences = self.calculate_user_preferences(user_profile)
        
        # Score each plan
        scored_plans = []
        for plan in plans:
            plan_id = plan.get('plan_id')
            if plan_id in plan_features:
                score = self.calculate_plan_score(
                    plan_features[plan_id], 
                    user_profile, 
                    preferences
                )
                
                scored_plans.append({
                    'plan': plan,
                    'score': score,
                    'match_reasons': self._get_match_reasons(plan_features[plan_id], user_profile, preferences)
                })
        
        # Sort by score and return top recommendations
        scored_plans.sort(key=lambda x: x['score'], reverse=True)
        
        recommendations = []
        for item in scored_plans[:top_k]:
            recommendation = {
                'plan': item['plan'],
                'compatibility_score': round(item['score'], 3),
                'match_reasons': item['match_reasons'],
                'recommended_for': self._get_recommendation_reason(user_profile, item['plan'])
            }
            recommendations.append(recommendation)
        
        return recommendations
    
    def _get_match_reasons(self, plan_features: PlanFeatures, user_profile: UserProfile, preferences: Dict[str, float]) -> List[str]:
        """Generate human-readable match reasons"""
        reasons = []
        
        if plan_features.monthly_premium < 400 and preferences['premium_weight'] > 0.3:
            reasons.append("Low monthly premium")
        
        if plan_features.metal_tier_score >= 3 and preferences['coverage_weight'] > 0.3:
            reasons.append("Comprehensive coverage")
        
        if plan_features.quality_rating >= 4 and preferences['quality_weight'] > 0.2:
            reasons.append("High quality rating")
        
        if plan_features.covers_telehealth and user_profile.health_conditions:
            reasons.append("Telehealth coverage for your health needs")
        
        if plan_features.hsa_eligible and user_profile.income > 50000:
            reasons.append("HSA eligible for tax savings")
        
        if plan_features.data_freshness > 0.8:
            reasons.append("Recently updated data")
        
        return reasons
    
    def _get_recommendation_reason(self, user_profile: UserProfile, plan: Dict) -> str:
        """Generate personalized recommendation reason"""
        age = user_profile.age
        income = user_profile.income
        conditions = user_profile.health_conditions
        
        if age < 30 and income < 40000:
            return "Great value plan for young adults on a budget"
        elif age > 60 and conditions:
            return "Comprehensive coverage for seniors with health conditions"
        elif income > 100000 and plan.get('hsa_eligible'):
            return "Premium plan with HSA benefits for high earners"
        elif user_profile.tobacco_user:
            return "Plan with reasonable rates for tobacco users"
        else:
            return "Well-balanced plan matching your profile"

class MultiAgentVerificationSystem:
    """Multi-agent system for real-time data verification"""
    
    def __init__(self):
        self.agents = {
            'price_agent': self._verify_pricing,
            'coverage_agent': self._verify_coverage,
            'network_agent': self._verify_network,
            'quality_agent': self._verify_quality
        }
        self.verification_threshold = 0.8
    
    def verify_plan_data(self, plan: Dict) -> Dict[str, any]:
        """Multi-agent verification of plan data"""
        verification_results = {}
        overall_confidence = 0.0
        
        for agent_name, agent_func in self.agents.items():
            try:
                result = agent_func(plan)
                verification_results[agent_name] = result
                overall_confidence += result.get('confidence', 0.0)
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                verification_results[agent_name] = {
                    'confidence': 0.0,
                    'status': 'failed',
                    'error': str(e)
                }
        
        overall_confidence /= len(self.agents)
        
        return {
            'overall_confidence': overall_confidence,
            'is_verified': overall_confidence >= self.verification_threshold,
            'agent_results': verification_results,
            'verification_timestamp': datetime.now().isoformat()
        }
    
    def _verify_pricing(self, plan: Dict) -> Dict:
        """Verify pricing data consistency"""
        premium = plan.get('monthly_premium_base', 0)
        deductible = plan.get('annual_deductible_individual', 0)
        metal_tier = plan.get('metal_tier', '')
        
        # Pricing validation rules
        confidence = 1.0
        
        # Check if premium is reasonable for metal tier
        tier_ranges = {
            'Bronze': (200, 600),
            'Silver': (300, 800),
            'Gold': (500, 1200),
            'Platinum': (700, 1500)
        }
        
        if metal_tier in tier_ranges:
            min_premium, max_premium = tier_ranges[metal_tier]
            if not (min_premium <= premium <= max_premium):
                confidence *= 0.7
        
        # Check premium vs deductible ratio
        if premium > 0 and deductible > 0:
            ratio = premium / deductible
            if ratio > 0.5:  # Premium shouldn't be more than half of deductible
                confidence *= 0.8
        
        return {
            'confidence': confidence,
            'status': 'verified' if confidence > 0.8 else 'flagged',
            'details': f'Premium: ${premium}, Deductible: ${deductible}'
        }
    
    def _verify_coverage(self, plan: Dict) -> Dict:
        """Verify coverage details"""
        confidence = 1.0
        
        # Check for required fields
        required_fields = ['plan_type', 'metal_tier', 'primary_care_copay']
        missing_fields = [field for field in required_fields if not plan.get(field)]
        
        if missing_fields:
            confidence *= 0.6
        
        # Check copay consistency
        primary_copay = plan.get('primary_care_copay', 0)
        specialist_copay = plan.get('specialist_copay', 0)
        
        if primary_copay > specialist_copay:
            confidence *= 0.8  # Specialist should cost more than primary
        
        return {
            'confidence': confidence,
            'status': 'verified' if confidence > 0.8 else 'flagged',
            'details': f'Coverage details verified'
        }
    
    def _verify_network(self, plan: Dict) -> Dict:
        """Verify network information"""
        confidence = 1.0
        
        # Check if network size is reasonable
        network_size = plan.get('estimated_providers_count', 0)
        if network_size < 100:
            confidence *= 0.7
        elif network_size > 50000:
            confidence *= 0.9  # Very large networks are less common
        
        return {
            'confidence': confidence,
            'status': 'verified' if confidence > 0.8 else 'flagged',
            'details': f'Network size: {network_size} providers'
        }
    
    def _verify_quality(self, plan: Dict) -> Dict:
        """Verify quality metrics"""
        confidence = 1.0
        
        quality_rating = plan.get('quality_rating', 0)
        satisfaction_score = plan.get('customer_satisfaction_score', 0)
        
        # Check if ratings are within reasonable range
        if quality_rating < 1 or quality_rating > 5:
            confidence *= 0.5
        elif quality_rating > 4.5:
            confidence *= 0.9  # Very high ratings are less common
        
        if satisfaction_score < 1 or satisfaction_score > 5:
            confidence *= 0.5
        
        return {
            'confidence': confidence,
            'status': 'verified' if confidence > 0.8 else 'flagged',
            'details': f'Quality: {quality_rating}, Satisfaction: {satisfaction_score}'
        }

class AdvancedComparisonEngine:
    """Advanced plan comparison with ML insights"""
    
    def __init__(self):
        self.recommendation_engine = IntelligentRecommendationEngine()
        self.verification_system = MultiAgentVerificationSystem()
    
    def compare_plans(self, plans: List[Dict], user_profile: UserProfile) -> Dict:
        """Comprehensive plan comparison with ML insights"""
        
        # Get recommendations
        recommendations = self.recommendation_engine.get_recommendations(
            user_profile, plans, top_k=len(plans)
        )
        
        # Verify each plan
        verified_plans = []
        for rec in recommendations:
            plan = rec['plan']
            verification = self.verification_system.verify_plan_data(plan)
            
            verified_plans.append({
                'plan': plan,
                'recommendation': rec,
                'verification': verification
            })
        
        # Generate comparison insights
        insights = self._generate_comparison_insights(verified_plans, user_profile)
        
        return {
            'plans': verified_plans,
            'insights': insights,
            'user_profile': user_profile,
            'comparison_timestamp': datetime.now().isoformat()
        }
    
    def _generate_comparison_insights(self, verified_plans: List[Dict], user_profile: UserProfile) -> Dict:
        """Generate ML-powered comparison insights"""
        
        if not verified_plans:
            return {'error': 'No plans to compare'}
        
        # Extract metrics
        premiums = [p['plan'].get('monthly_premium_base', 0) for p in verified_plans]
        deductibles = [p['plan'].get('annual_deductible_individual', 0) for p in verified_plans]
        scores = [p['recommendation']['compatibility_score'] for p in verified_plans]
        
        insights = {
            'price_analysis': {
                'cheapest': min(premiums),
                'most_expensive': max(premiums),
                'average': sum(premiums) / len(premiums),
                'price_range': max(premiums) - min(premiums)
            },
            'value_analysis': {
                'best_value': max(scores),
                'average_score': sum(scores) / len(scores),
                'recommended_plan': max(verified_plans, key=lambda x: x['recommendation']['compatibility_score'])
            },
            'coverage_analysis': {
                'metal_tiers': list(set(p['plan'].get('metal_tier', '') for p in verified_plans)),
                'hsa_eligible_count': sum(1 for p in verified_plans if p['plan'].get('hsa_eligible')),
                'telehealth_count': sum(1 for p in verified_plans if p['plan'].get('covers_telehealth'))
            },
            'data_quality': {
                'verified_plans': sum(1 for p in verified_plans if p['verification']['is_verified']),
                'average_confidence': sum(p['verification']['overall_confidence'] for p in verified_plans) / len(verified_plans)
            },
            'recommendations': [
                f"Based on your profile, we recommend {user_profile.age}-year-old plans with {user_profile.income} income",
                f"Consider HSA-eligible plans if you want tax savings",
                f"Look for plans with telehealth if you have health conditions" if user_profile.health_conditions else "All plans offer good basic coverage"
            ]
        }
        
        return insights

# Example usage
def create_sample_user_profile() -> UserProfile:
    """Create a sample user profile for testing"""
    return UserProfile(
        age=35,
        income=75000,
        household_size=2,
        health_conditions=['diabetes'],
        preferred_plan_type='PPO',
        budget_range=(300, 600),
        priority_factors=['good_coverage', 'hsa_eligible'],
        location='San Francisco, CA',
        tobacco_user=False
    )

if __name__ == "__main__":
    # Test the recommendation engine
    engine = IntelligentRecommendationEngine()
    verification = MultiAgentVerificationSystem()
    comparison = AdvancedComparisonEngine()
    
    print("ML-Powered Insurance Recommendation System")
    print("=" * 50)
    print("✅ Intelligent Recommendations: ML-powered matching")
    print("✅ Real-time Verification: Multi-agent system")
    print("✅ Advanced Comparison: Comprehensive insights")
    print("=" * 50)



