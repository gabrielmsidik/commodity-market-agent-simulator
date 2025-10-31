# Commodity Market Agent Simulator

A 100-day economic simulation testing information asymmetry hypothesis using LangGraph and LLM agents.

## Features

- **Multi-agent simulation**: Wholesaler and 2 Sellers with different information access
- **Multi-round negotiations**: Up to 10 rounds of offers/counteroffers
- **Agent memory**: Persistent scratchpads for strategic learning
- **Configurable parameters**: Customize costs, inventory, demand, and agent behavior
- **Comprehensive logging**: All simulation data saved to log files for analysis

## Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and model configurations
```

### 3. Run a Simulation

```bash
python run_simulation.py
```

Results will be saved to the `logs/` directory.

## Project Structure

```
commodity-market-agent-simulator/
├── src/
│   ├── models/          # Data models and TypedDicts
│   ├── agents/          # Agent tools and LLM wrappers
│   ├── graph/           # LangGraph nodes and workflow
│   ├── simulation/      # Simulation runner and configuration
│   └── utils/           # Logging utilities
├── logs/                # Simulation logs (auto-generated)
├── documentation.md     # Detailed simulation specification
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
```

## Configuration

### Agent Configuration

Each agent (Wholesaler, Seller_1, Seller_2) can use different LLM models and providers:

```env
WHOLESALER_MODEL_NAME=gpt-4o-mini
WHOLESALER_BASE_URL=https://api.openai.com/v1
WHOLESALER_API_KEY=sk-...

SELLER1_MODEL_NAME=deepseek-chat
SELLER1_BASE_URL=https://api.deepseek.com/v1
SELLER1_API_KEY=sk-...

SELLER2_MODEL_NAME=grok-beta
SELLER2_BASE_URL=https://api.x.ai/v1
SELLER2_API_KEY=xai-...
```

### Simulation Parameters

Configure programmatically:

- **Seller 1**: Cost range, inventory range
- **Seller 2**: Cost range, inventory range
- **Shoppers**: Total demand, long-term vs short-term ratio, price ranges, urgency factors
- **Simulation**: Number of days, negotiation frequency

## Usage

### Option 1: Python Scripts

```bash
python run_simulation.py
```

Create your own:

```python
from src.simulation import SimulationRunner, SimulationConfig
import logging

# Create configuration
config = SimulationConfig(
    name="My Simulation",
    description="Testing information asymmetry",
    num_days=100,
    s1_cost_min=58,
    s1_cost_max=62,
    s1_inv_min=7800,
    s1_inv_max=8200,
    s2_cost_min=68,
    s2_cost_max=72,
    s2_inv_min=1900,
    s2_inv_max=2100,
    total_shoppers=100,
    long_term_ratio=0.7
)

# Run simulation
runner = SimulationRunner(config, log_level=logging.INFO)
results = runner.run()

# Access results
print(f"Total trades: {results['summary']['total_market_trades']}")
print(f"Average price: ${results['summary']['average_market_price']:.2f}")
```

### Option 2: REST API

Start the API server:

```bash
python app.py
```

Then use HTTP requests to run simulations:

```bash
# Start a simulation
curl -X POST http://localhost:5000/api/simulations/run \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "num_days": 10}'

# Check status
curl http://localhost:5000/api/simulations/status/<job_id>

# Get results
curl http://localhost:5000/api/simulations/<job_id>
```

See **API_REFERENCE.md** for complete API documentation.

## Analysis

Simulation results are available in:

- **Log files**: Detailed execution logs in `logs/simulation_*.log`
- **Return dictionary**: Complete simulation data including:
  - Market clearing prices and quantities over time
  - Agent profitability and inventory levels
  - Negotiation transcripts and outcomes
  - Information leakage analysis
  - Agent scratchpad evolution

