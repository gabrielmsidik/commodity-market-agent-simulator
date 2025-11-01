# Commodity Market Agent Simulator

A multi-agent AI safety research project investigating **emergent collusion in LLM-powered markets**. This simulation tests how AI agents with communication capabilities and price transparency can spontaneously develop anti-competitive coordination without explicit instruction.

## Research Context

**Current Phase**: Collusion detection research with multi-wholesaler competitive architecture

**Key Finding (3-day pilot)**: Wholesaler agents achieved 98.1% price convergence with explicit coordination language ("temporary pricing agreement"), demonstrating emergent collusive behavior.

**Active Branch**: `feat-collusion-detection` - Multi-wholesaler communication framework and baseline experiments

## Features

### Core Simulation
- **Multi-agent system**: 2 Wholesalers + 2 Sellers competing in commodity market
- **Free-form communication**: LLM agents exchange strategic messages daily
- **Price transparency**: Full competitor visibility enabling coordination
- **Multi-round negotiations**: Up to 10 rounds of offers/counteroffers
- **Agent memory**: Persistent scratchpads for strategic learning
- **Comprehensive logging**: All communications and pricing decisions saved

### Research Capabilities
- **Communication framework**: Two-round daily message exchange between wholesalers
- **Collusion detection**: Behavioral pattern analysis and price correlation metrics
- **Information asymmetry**: Configurable visibility of market data
- **Baseline experiments**: Controlled tests isolating causal factors

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

---

## 🔬 Research: Baseline Collusion Experiments

**For Research Team Members**: All experiments are now configuration-based - no code edits required!

### Quick Start - Run All 4 Experiments

Each experiment uses simple configuration flags to enable/disable features:

```bash
# Experiment D: Treatment (Communication ✅ + Transparency ✅)
PYTHONPATH=. python experiments/baseline/run_21day_treatment.py

# Experiment A: No Communication (Communication ❌ + Transparency ✅)
PYTHONPATH=. python experiments/baseline/run_21day_no_communication.py

# Experiment B: No Transparency (Communication ✅ + Transparency ❌)
PYTHONPATH=. python experiments/baseline/run_21day_no_transparency.py

# Experiment C: Full Baseline (Communication ❌ + Transparency ❌)
PYTHONPATH=. python experiments/baseline/run_21day_full_baseline.py
```

### Configuration-Based Architecture

The framework uses two boolean flags in `SimulationConfig`:

```python
from src.simulation.config import SimulationConfig

config = SimulationConfig(
    name="my_experiment",
    num_days=21,
    enable_communication=False,      # Disable wholesaler communication
    enable_price_transparency=False  # Disable competitor price visibility
)
```

**When `enable_communication=False`:**
- Wholesaler discussion node is removed from workflow
- No daily message exchange
- Expected: 0 messages in communications_log

**When `enable_price_transparency=False`:**
- `get_competitor_activity()` tool returns empty data
- Agents cannot monitor competitor prices
- Expected: No price references in agent scratchpads

### Expected Runtimes

- **Experiment D (Treatment)**: ~30-40 minutes
- **Experiment A (No Communication)**: ~20-30 minutes (faster)
- **Experiment B (No Transparency)**: ~30-40 minutes
- **Experiment C (Full Baseline)**: ~20-30 minutes (faster)

**Total Sequential Runtime**: ~90 minutes
**Total Cost**: ~$2-4 (GPT-4o-mini via OpenRouter)

### Analyzing Results

Each experiment automatically generates:

1. **Console Output**: Convergence analysis for Days 1, 7, 14, 21
2. **JSON File**: Full data in `experiments/baseline/results/`
3. **Log File**: Detailed simulation log in `logs/simulation_*.log`

Example output:
```
Day 21:
  Wholesaler:   $85 (0 units)
  Wholesaler_2: $85 (0 units)
  Price diff: $0 (0.0%)
  🔴 IDENTICAL PRICING
  Convergence: 100.0%
```

### Detailed Documentation

**See**: `experiments/baseline/README.md` for:
- Detailed experimental design
- Implementation details
- Expected results and hypotheses
- Troubleshooting guide

---

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

