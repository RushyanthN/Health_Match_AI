# Healthcare.gov API Setup Guide

## Overview
The Healthcare.gov API provides official access to health insurance plan data from the federal marketplace. This is the most reliable source for insurance plan information.

## API Key Registration

### Step 1: Register for API Access
1. Visit: https://marketplace.cms.gov/developers/
2. Click "Get Started" or "Request API Access"
3. Fill out the registration form with:
   - Organization name
   - Contact information
   - Use case description
   - Expected API usage

### Step 2: Wait for Approval
- API key approval typically takes 1-3 business days
- You'll receive an email with your API key
- Save the API key securely

### Step 3: Configure API Key
Once you have your API key, add it to your environment:

```bash
# Windows
set HEALTHCARE_GOV_API_KEY=your_api_key_here

# Linux/Mac
export HEALTHCARE_GOV_API_KEY=your_api_key_here
```

Or create a `.env` file:
```
HEALTHCARE_GOV_API_KEY=your_api_key_here
```

## API Endpoints

### Base URL
```
https://marketplace.api.healthcare.gov/api/v1
```

### Available Endpoints

#### 1. Search Plans
```
GET /plans/search
```

Parameters:
- `state` (required): State code (e.g., "CA")
- `zip` (required): ZIP code
- `year` (optional): Plan year (default: current year)
- `household_size` (optional): Number of people in household
- `household_income` (optional): Annual household income
- `age` (optional): Age of primary applicant

#### 2. Get Plan Details
```
GET /plans/{plan_id}
```

#### 3. Get Issuers
```
GET /issuers?state={state_code}
```

## Rate Limits
- Free tier: 1,000 requests per day
- Paid tiers available for higher usage
- Rate limit headers included in responses

## Data Structure

### Plan Object
```json
{
  "id": "plan_id",
  "name": "Plan Name",
  "issuer": {
    "name": "Insurance Company"
  },
  "plan_type": "HMO|PPO|EPO|POS",
  "metal_level": "Bronze|Silver|Gold|Platinum|Catastrophic",
  "plan_year": 2025,
  "premium_adult_individual": 450.00,
  "deductible_individual": 3000.00,
  "out_of_pocket_individual": 6000.00,
  "primary_care_copay": 25.00,
  "specialist_copay": 50.00,
  "emergency_room_copay": 300.00,
  "covers_telehealth": true,
  "hsa_eligible": false
}
```

## Usage Examples

### Python Client
```python
from scrapers.healthcare_gov_client import HealthcareGovClient
import asyncio

async def get_plans():
    async with HealthcareGovClient(api_key="your_key") as client:
        plans = await client.get_plans(
            state="CA",
            zip_code="94102",
            year=2025,
            household_size=1,
            household_income=50000,
            age=30
        )
        return plans

# Run the async function
plans = asyncio.run(get_plans())
```

### cURL Example
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://marketplace.api.healthcare.gov/api/v1/plans/search?state=CA&zip=94102&year=2025"
```

## Error Handling

### Common Error Codes
- `401`: Unauthorized (invalid or missing API key)
- `403`: Forbidden (API key doesn't have permission)
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error

### Error Response Format
```json
{
  "message": "Error description",
  "request_id": "unique_request_id"
}
```

## Best Practices

1. **Cache Results**: Plan data doesn't change frequently, cache for 24 hours
2. **Handle Rate Limits**: Implement exponential backoff for 429 errors
3. **Validate Input**: Always validate state codes and ZIP codes
4. **Error Logging**: Log all API errors with request IDs
5. **Data Validation**: Verify plan data structure before processing

## Alternative Data Sources

If you can't get API access immediately, consider:

1. **State Marketplace APIs**: Many states have their own APIs
2. **Insurance Company APIs**: Direct carrier APIs
3. **Third-Party Aggregators**: QuoteWizard, eHealth, etc.
4. **Mock Data Generator**: Use our `insurance_data_generator.py` for testing

## Support

- API Documentation: https://marketplace.cms.gov/developers/
- Support Email: marketplace-support@cms.hhs.gov
- Status Page: https://status.healthcare.gov/
