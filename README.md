# Commodity Market Agent Simulator

A 100-day economic simulation testing information asymmetry hypothesis using LangGraph and LLM agents.

## Features

- **Multi-agent simulation**: Wholesaler and 2 Sellers with different information access
- **Multi-round negotiations**: Up to 10 rounds of offers/counteroffers
- **Agent memory**: Persistent scratchpads for strategic learning
- **Configurable parameters**: Customize costs, inventory, demand, and agent behavior
- **Web UI**: Run simulations and analyze results through a browser interface
- **Comprehensive logging**: All simulation data saved for analysis

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

### 3. Initialize Database

```bash
python -m src.database.init_db
```

### 4. Run the Application

```bash
python app.py
```

Open your browser to `http://localhost:5000`

## Project Structure

```
commodity-market-agent-simulator/
├── src/
│   ├── models/          # Data models and TypedDicts
│   ├── agents/          # Agent tools and LLM wrappers
│   ├── graph/           # LangGraph nodes and workflow
│   ├── simulation/      # Simulation runner and configuration
│   ├── database/        # Database models and operations
│   └── web/             # Flask application and UI
├── templates/           # HTML templates
├── static/              # CSS, JS, and static assets
├── logs/                # Simulation logs
├── documentation.md     # Detailed simulation specification
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── app.py              # Main application entry point
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

Configure via the web UI or programmatically:

- **Seller 1**: Cost range, inventory range
- **Seller 2**: Cost range, inventory range
- **Shoppers**: Total demand, long-term vs short-term ratio, price ranges, urgency factors
- **Simulation**: Number of days, negotiation frequency

## Usage

### Web Interface

1. Navigate to `http://localhost:5000`
2. Click "New Simulation"
3. Configure parameters
4. Click "Run Simulation"
5. View results and analysis

### Programmatic Usage

```python
from src.simulation.runner import SimulationRunner
from src.simulation.config import SimulationConfig

config = SimulationConfig(
    s1_cost_min=58,
    s1_cost_max=62,
    s1_inv_min=7800,
    s1_inv_max=8200,
    # ... other parameters
)

runner = SimulationRunner(config)
result = runner.run()
```

## Analysis

Simulation results include:

- Market clearing prices and quantities over time
- Agent profitability and inventory levels
- Negotiation transcripts and outcomes
- Information leakage analysis
- Agent scratchpad evolution

## License

MIT License

