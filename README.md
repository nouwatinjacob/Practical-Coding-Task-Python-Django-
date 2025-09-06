# Subscription Management API

A Django REST Framework API for managing user subscriptions with plan switching capabilities.

## Features

- **Subscription Management**: Create, list, and deactivate user subscriptions
- **Plan Switching**: Switch between different plans with frequency upgrade rules
- **Nested Data**: Retrieve subscriptions with complete plan and feature information
- **User Isolation**: Users can only access their own subscriptions
- **Atomic Operations**: Plan switching is handled atomically to prevent data inconsistencies
- **Optimized Queries**: Uses `select_related` + `prefetch_related` to minimize queries.

## Models

### Feature
- `name`: Unique feature name
- Used to define what's included in each plan

### Plan
- `name`: Plan name (e.g., "Basic", "Premium")
- `price`: Monthly base price
- `features`: Many-to-many relationship with Feature
- `is_active`: Whether plan is available for new subscriptions

### Subscription
- `user`: Foreign key to User
- `plan`: Foreign key to Plan
- `frequency`: Choice field (weekly, monthly, yearly)
- `amount`: Calculated based on plan price and frequency
- `is_active`: Only one active subscription per user allowed
- Auto-calculated `start_date` and `end_date`

## API Endpoints

### List/Create Subscriptions
```
GET /subscriptions/
POST /subscriptions/
```

**Create Subscription:**
```json
{
  "plan_id": 1,
  "frequency": "monthly"
}
```

**Response includes nested data:**
```json
{
  "id": 1,
  "frequency": "monthly",
  "amount": "10.00",
  "is_active": true,
  "start_date": "2025-01-15T10:30:00Z",
  "end_date": "2025-02-14T10:30:00Z",
  "plan": {
    "id": 1,
    "name": "Basic Plan",
    "price": "10.00",
    "features": [
      {
        "id": 1,
        "name": "Feature 1"
      }
    ]
  }
}
```

### Switch Plan
```
POST /subscriptions/switch-plan/
```

**Request:**
```json
{
  "plan_id": 2,
  "frequency": "yearly"
}
```

**Rules:**
- Can switch to any different plan
- For same plan, can only upgrade to longer frequency (weekly → monthly → yearly)
- Deactivates current subscription and creates new one atomically

### Retrieve Single Subscription
```
GET /subscriptions/{id}/
```

### Deactivate Subscription
```
POST /subscriptions/{id}/deactivate/
```

## Frequency & Pricing

- **Weekly**: Base price ÷ 4
- **Monthly**: Base price × 1
- **Yearly**: Base price × 12

## Business Rules

1. **One Active Subscription**: Users can only have one active subscription at a time
2. **Frequency Upgrades**: Can only switch to longer frequencies on the same plan
3. **Plan Switching**: Can switch to any different plan with any frequency
4. **Auto-calculation**: Amount and end dates are automatically calculated

## Authentication

All endpoints require authentication. Users can only access their own subscriptions.

## Database Optimization

- Uses `select_related()` for plan data
- Uses `prefetch_related()` for feature data
- Composite indexes for common query patterns

## Running Tests

```bash
python manage.py test
```

## Test Coverage

- ✅ Subscription creation with validation
- ✅ Plan switching with business rules
- ✅ List retrieval with nested data
- ✅ User isolation and security
- ✅ Database query optimization

## Usage Example

```python
# Create a subscription
data = {
    "plan_id": 1,
    "frequency": "monthly"
}
response = client.post('/subscriptions/', data)

# Switch to yearly billing
switch_data = {
    "plan_id": 1,
    "frequency": "yearly"
}
response = client.post('/subscriptions/switch-plan/', switch_data)

# List all subscriptions (with nested plan/feature data)
response = client.get('/subscriptions/')
```