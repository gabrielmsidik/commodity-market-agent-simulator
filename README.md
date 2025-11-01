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
- **Configurable parameters**: Customize costs, inventory, demand, and agent behavior
- **Comprehensive logging**: All communications, pricing decisions, and simulation data saved

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

### 3. Run a Simulation

```bash
python run_simulation.py
```

Results will be saved to the `logs/` directory.

---

## 🔬 Research: Baseline Collusion Experiments

**For Research Team Members**: All experiments are now configuration-based - no code edits required!

### Quick Start - Run All 4 Experiments

Use the simplified experiment runner to run any of the 4 baseline experiments:

```bash
# Experiment A: No Communication, No Transparency (Full Baseline)
python run_baseline_exp.py --experiment A --days 21 --output-dir outputs/baseline_exp_A

# Experiment B: No Communication, With Transparency
python run_baseline_exp.py --experiment B --days 21 --output-dir outputs/baseline_exp_B

# Experiment C: With Communication, No Transparency
python run_baseline_exp.py --experiment C --days 21 --output-dir outputs/baseline_exp_C

# Experiment D: Full Treatment (Communication + Transparency)
python run_baseline_exp.py --experiment D --days 21 --output-dir outputs/baseline_exp_D
```

**Run all 4 in parallel** (in separate terminal windows):
```bash
# Terminal 1
python run_baseline_exp.py --experiment A --days 21 --output-dir outputs/baseline_exp_A

# Terminal 2
python run_baseline_exp.py --experiment B --days 21 --output-dir outputs/baseline_exp_B

# Terminal 3
python run_baseline_exp.py --experiment C --days 21 --output-dir outputs/baseline_exp_C

# Terminal 4
python run_baseline_exp.py --experiment D --days 21 --output-dir outputs/baseline_exp_D
```

### Experiment Configurations

| Experiment | Communication | Price Transparency | Purpose |
|------------|--------------|-------------------|----------|
| A | ❌ | ❌ | Full baseline (no coordination possible) |
| B | ❌ | ✅ | Test transparency alone |
| C | ✅ | ❌ | Test communication alone |
| D | ✅ | ✅ | Full treatment (both enabled) |

### Configuration-Based Architecture

The framework uses two boolean flags in `SimulationConfig`:

```python
from src.simulation.config import SimulationConfig

config = SimulationConfig(
    name="my_experiment",
    num_days=21,
    enable_communication=True,       # Enable wholesaler daily communication
    enable_price_transparency=True   # Enable competitor price visibility
)
```

**When `enable_communication=False`:**
- Wholesaler discussion node is skipped in workflow
- No daily message exchange between wholesalers
- Expected: 0 messages in communications_log

**When `enable_price_transparency=False`:**
- `get_competitor_activity()` tool returns empty data
- Agents cannot monitor competitor prices
- Expected: No price references in agent scratchpads

### Expected Runtimes

- **Experiment A (No features)**: ~15-20 minutes (fastest)
- **Experiment B (Transparency only)**: ~15-20 minutes
- **Experiment C (Communication only)**: ~25-35 minutes
- **Experiment D (Full treatment)**: ~25-35 minutes

**Total Sequential Runtime**: ~80-110 minutes
**Total Parallel Runtime**: ~25-35 minutes (if run in parallel)
**Total Cost**: ~$2-4 (using GPT-4o-mini via OpenRouter)

### Analyzing Results

Each experiment saves results to the specified output directory:

1. **Console Output**: Real-time simulation progress with daily summaries
2. **Log File**: Detailed simulation log in `logs/simulation_*.log`
3. **Communications Log**: All wholesaler messages (if communication enabled)
4. **Market Offers Log**: Price history (if transparency enabled)
5. **Agent Scratchpads**: Strategic notes and learnings

Check the log files for:
- Wholesaler communication patterns (Experiment C & D)
- Price convergence over time
- Negotiation outcomes
- Final agent performance metrics

---

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

