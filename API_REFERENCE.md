# API Reference

Simple REST API for running commodity market simulations.

## Base URL

```
http://localhost:5000
```

## Endpoints

### Health Check

**GET** `/api/health`

Check if the API server is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-30T14:30:22.123456"
}
```

---

### Get Default Configuration

**GET** `/api/config/default`

Get the default simulation configuration parameters.

**Response:**
```json
{
  "name": "Commodity Market Simulation",
  "description": "100-day simulation with information asymmetry",
  "num_days": 100,
  "s1_cost_min": 58,
  "s1_cost_max": 62,
  "s1_inv_min": 7800,
  "s1_inv_max": 8200,
  "s1_starting_cash": 10000,
  "s2_cost_min": 68,
  "s2_cost_max": 72,
  "s2_inv_min": 1900,
  "s2_inv_max": 2100,
  "s2_starting_cash": 10000,
  "w_starting_cash": 50000,
  "total_shoppers": 100,
  "long_term_ratio": 0.7,
  "lt_base_min": 80,
  "lt_base_max": 90,
  "lt_max_min": 110,
  "lt_max_max": 120,
  "lt_urgency_min": 0.8,
  "lt_urgency_max": 1.2,
  "st_base_min": 90,
  "st_base_max": 100,
  "st_max_min": 130,
  "st_max_max": 150,
  "st_urgency_min": 1.5,
  "st_urgency_max": 2.5
}
```

---

### Run Simulation

**POST** `/api/simulations/run`

Start a new simulation (runs asynchronously in background).

**Request Body:**
```json
{
  "name": "Test Simulation",
  "description": "Testing information asymmetry",
  "num_days": 10,
  "s1_cost_min": 58,
  "s1_cost_max": 62,
  "s1_inv_min": 7800,
  "s1_inv_max": 8200
  // ... other optional parameters
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Simulation started"
}
```

---

### Get Job Status

**GET** `/api/simulations/status/<job_id>`

Check the status of a running or completed simulation.

**Response (Running):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "created_at": "2025-01-30T14:30:00.000000",
  "started_at": "2025-01-30T14:30:01.000000"
}
```

**Response (Completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-01-30T14:30:00.000000",
  "started_at": "2025-01-30T14:30:01.000000",
  "completed_at": "2025-01-30T14:35:22.000000"
}
```

**Response (Failed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "created_at": "2025-01-30T14:30:00.000000",
  "started_at": "2025-01-30T14:30:01.000000",
  "completed_at": "2025-01-30T14:30:15.000000",
  "error": "Error message here"
}
```

**Status Values:**
- `pending` - Job created, waiting to start
- `running` - Simulation in progress
- `completed` - Simulation finished successfully
- `failed` - Simulation encountered an error

---

### Get Simulation Results

**GET** `/api/simulations/<job_id>`

Get the full results of a completed simulation.

**Response:**
```json
{
  "summary": {
    "total_market_trades": 4523,
    "total_market_volume": 8950,
    "average_market_price": 95.50,
    "total_unmet_demand": 150,
    "total_wholesale_trades": 10,
    "total_wholesale_volume": 9000,
    "average_wholesale_price": 60.25,
    "agent_performance": {
      "Wholesaler": {
        "profit": 36000.50,
        "revenue": 86000.00,
        "costs": 50000.00,
        "final_inventory": 50,
        "final_cash": 86000.50
      },
      "Seller_1": {
        "profit": 28000.00,
        "revenue": 76000.00,
        "costs": 48000.00,
        "final_inventory": 200,
        "final_cash": 38000.00
      },
      "Seller_2": {
        "profit": 12000.00,
        "revenue": 26000.00,
        "costs": 14000.00,
        "final_inventory": 100,
        "final_cash": 22000.00
      }
    }
  },
  "final_state": {
    "market_log": [...],
    "agent_scratchpads": {...},
    "negotiation_history": {...},
    "agent_ledgers": {...}
  }
}
```

---

### Get Simulation Summary

**GET** `/api/simulations/<job_id>/summary`

Get only the summary statistics of a completed simulation (lighter response).

**Response:**
```json
{
  "total_market_trades": 4523,
  "total_market_volume": 8950,
  "average_market_price": 95.50,
  "total_unmet_demand": 150,
  "agent_performance": {
    "Wholesaler": {
      "profit": 36000.50,
      "final_inventory": 50,
      "final_cash": 86000.50
    }
    // ... other agents
  }
}
```

---

### List All Simulations

**GET** `/api/simulations`

Get a list of all simulation jobs.

**Response:**
```json
{
  "total": 5,
  "jobs": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "completed",
      "created_at": "2025-01-30T14:30:00.000000",
      "name": "Test Simulation",
      "description": "Testing information asymmetry"
    },
    {
      "job_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "running",
      "created_at": "2025-01-30T14:25:00.000000",
      "name": "Another Simulation",
      "description": ""
    }
  ]
}
```

---

### Delete Simulation

**DELETE** `/api/simulations/<job_id>`

Delete a simulation job and its results from memory.

**Response:**
```json
{
  "message": "Simulation deleted"
}
```

---

## Example Usage

### Using cURL

```bash
# Start a simulation
curl -X POST http://localhost:5000/api/simulations/run \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "num_days": 10}'

# Check status
curl http://localhost:5000/api/simulations/status/<job_id>

# Get results
curl http://localhost:5000/api/simulations/<job_id>

# List all simulations
curl http://localhost:5000/api/simulations
```

### Using Python

```python
import requests
import time

# Start simulation
response = requests.post('http://localhost:5000/api/simulations/run', json={
    'name': 'Test Simulation',
    'num_days': 10
})
job_id = response.json()['job_id']
print(f"Started job: {job_id}")

# Poll for completion
while True:
    status_response = requests.get(f'http://localhost:5000/api/simulations/status/{job_id}')
    status = status_response.json()['status']
    print(f"Status: {status}")
    
    if status in ['completed', 'failed']:
        break
    
    time.sleep(5)

# Get results
if status == 'completed':
    results = requests.get(f'http://localhost:5000/api/simulations/{job_id}').json()
    print(f"Total trades: {results['summary']['total_market_trades']}")
```

---

## Notes

- **In-Memory Storage**: All jobs and results are stored in memory. They will be lost when the server restarts.
- **Async Execution**: Simulations run in background threads, so the API doesn't block.
- **No Authentication**: This is a simple API with no authentication. Add authentication if deploying publicly.
- **CORS Enabled**: Cross-origin requests are allowed from any domain.

