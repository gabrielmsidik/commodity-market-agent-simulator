# Baseline Experiments - 21-Day Comparison Study

## Overview

This directory contains ready-to-run scripts for 4 baseline experiments testing the causal impact of communication and price transparency on collusion.

**All experiments now use configuration flags - no manual code edits required!** ✅

## Experimental Design

| Experiment | Communication | Price Transparency | Purpose |
|------------|--------------|-------------------|---------|
| **A: No Communication** | ❌ Disabled | ✅ Enabled | Test if communication causes collusion |
| **B: No Transparency** | ✅ Enabled | ❌ Disabled | Test if price visibility enables coordination |
| **C: Full Baseline** | ❌ Disabled | ❌ Disabled | Pure competitive baseline |
| **D: Treatment** | ✅ Enabled | ✅ Enabled | Current system (full features) |

---

## Quick Start - Run All Experiments

Each experiment is a single command with no setup required:

### Experiment D: Treatment ✅

```bash
PYTHONPATH=. python experiments/baseline/run_21day_treatment.py
```

**Configuration**: Communication ✅ + Transparency ✅
**Runtime**: ~30-40 minutes
**Output**: `experiments/baseline/results/experiment_D_treatment_*.json`

---

### Experiment A: No Communication ✅

```bash
PYTHONPATH=. python experiments/baseline/run_21day_no_communication.py
```

**Configuration**: Communication ❌ + Transparency ✅
**Runtime**: ~20-30 minutes (faster without communication)
**Output**: `experiments/baseline/results/experiment_A_no_communication_*.json`

**Hypothesis**: Transparency alone is insufficient for sustained collusion

---

### Experiment B: No Transparency ✅

```bash
PYTHONPATH=. python experiments/baseline/run_21day_no_transparency.py
```

**Configuration**: Communication ✅ + Transparency ❌
**Runtime**: ~30-40 minutes
**Output**: `experiments/baseline/results/experiment_B_no_transparency_*.json`

**Hypothesis**: Communication alone is insufficient without price monitoring

---

### Experiment C: Full Baseline ✅

```bash
PYTHONPATH=. python experiments/baseline/run_21day_full_baseline.py
```

**Configuration**: Communication ❌ + Transparency ❌
**Runtime**: ~20-30 minutes
**Output**: `experiments/baseline/results/experiment_C_full_baseline_*.json`

**Hypothesis**: Without coordination mechanisms, Bertrand competition emerges

---

## How It Works

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

### What Gets Disabled

**When `enable_communication=False`:**
- The `wholesaler_discussion` node is removed from the workflow
- Agents cannot exchange messages
- No coordination channel available
- Expected: ~0 messages in `communications_log`

**When `enable_price_transparency=False`:**
- The `get_competitor_activity()` tool returns empty data
- Agents cannot see competitor prices
- No monitoring capability
- Tool returns: `{"message": "Price transparency disabled for this experiment"}`

### Implementation Details

**Workflow routing** (src/graph/workflow.py:127-260):
```python
def create_simulation_graph(
    enable_communication: bool = True,
    enable_price_transparency: bool = True
) -> StateGraph:
    # Conditionally adds wholesaler_discussion node
    if enable_communication:
        graph.add_node("wholesaler_discussion", nodes.wholesaler_discussion)
```

**Transparency control** (src/agents/tools.py:115-160):
```python
def get_competitor_activity(self) -> Dict[str, Any]:
    if not self.state.get("enable_price_transparency", True):
        return {
            "competitor_name": None,
            "recent_prices": [],
            "message": "Price transparency disabled"
        }
```

---

## Expected Results

Based on 3-day pilot test and economic theory:

### Experiment D (Treatment)
- **Predicted**: High collusion (98%+ convergence)
- **Mechanism**: Communication + transparency enables stable coordination
- **Pilot Result**: 98.1% convergence, explicit coordination language

### Experiment A (No Communication)
- **Predicted**: Moderate collusion (70-80% convergence?)
- **Hypothesis**: Tacit coordination possible but unstable without communication
- **Key Test**: Can transparency alone sustain price alignment?

### Experiment B (No Transparency)
- **Predicted**: Low collusion (50-60% convergence?)
- **Hypothesis**: Agreements cannot be monitored/enforced without price visibility
- **Key Test**: Do agents attempt coordination but fail to sustain it?

### Experiment C (Full Baseline)
- **Predicted**: Competitive pricing (30-50% convergence)
- **Hypothesis**: Bertrand competition emerges without coordination mechanisms
- **Key Test**: Baseline reference for statistical comparison

---

## Analysis

### Automated Analysis

Each experiment script includes built-in convergence analysis:

- **Price convergence percentage** per day
- **Identical pricing days** (Δ$0)
- **Near-identical pricing days** (Δ$1-2)
- **Average convergence** over 21 days
- **Sample day comparisons** (Days 1, 7, 14, 21)

### Output Format

Results are saved as JSON with:

```json
{
  "experiment": "A_no_communication",
  "configuration": {
    "communication_enabled": false,
    "transparency_enabled": true,
    "num_days": 21
  },
  "convergence_analysis": [
    {"day": 1, "w1_price": 85, "w2_price": 82, "diff": 3, "convergence_pct": 96.5},
    ...
  ],
  "communications": [...],
  "market_offers": [...]
}
```

### Statistical Comparison

After running all 4 experiments, use comparison analysis (future work):

```bash
PYTHONPATH=. python experiments/baseline/compare_results.py
```

This will generate:
- **T-tests** on price convergence across experiments
- **ANOVA** for overall effect significance
- **Visualization plots** (price trends, convergence over time)
- **Effect size calculations** (communication impact, transparency impact)

---

## Recommended Execution Order

1. ✅ **Run Experiment D first** (treatment baseline, already done if you followed previous instructions)
2. **Run A, B, C in parallel or sequence**
   - Sequential: Better for monitoring individual results (~90 mins total)
   - Parallel: Faster completion (requires sufficient API quota)

**Total Time**: ~90 minutes (sequential)
**Total Cost**: ~$2-4 (GPT-4o-mini via OpenRouter)

---

## Reproducibility

### Same Random Seed (Optional)

For exact reproducibility across runs, set random seed before import:

```python
import random
import numpy as np

random.seed(42)
np.random.seed(42)
```

### Configuration Persistence

All experiment parameters are saved in output JSON:

```json
"config": {
  "s1_cost_min": 58,
  "s1_cost_max": 62,
  "s1_inv_min": 7800,
  ...
  "enable_communication": false,
  "enable_price_transparency": true
}
```

This allows exact replication of any experiment.

---

## Troubleshooting

### Communication Not Disabled

**Check**: `communications_log` should be empty (`[]`) for Experiments A and C

**Verify**:
```python
communications = final_state.get("communications_log", [])
print(f"Messages: {len(communications)}")  # Should be 0
```

### Transparency Still Working

**Check**: Agents should not mention competitor prices in scratchpads for Experiments B and C

**Verify**:
```python
# In logs, look for:
"Price transparency disabled for this experiment"
```

### Import Errors

**Fix**: Always run with `PYTHONPATH=.` prefix:
```bash
PYTHONPATH=. python experiments/baseline/run_21day_treatment.py
```

---

## Files

### Experiment Scripts
- `run_21day_treatment.py` - Experiment D (✅ ready)
- `run_21day_no_communication.py` - Experiment A (✅ ready)
- `run_21day_no_transparency.py` - Experiment B (✅ ready)
- `run_21day_full_baseline.py` - Experiment C (✅ ready)

### Results Directory
- `results/` - JSON outputs from experiments (gitignored, created automatically)

### Analysis Scripts (Future Work)
- `compare_results.py` - Statistical comparison across experiments
- `visualize_convergence.py` - Plot price trends and convergence

---

## Contact

For questions or issues:
- Check simulation logs in `logs/simulation_*.log`
- Verify config in `.env` file
- Review experiment outputs in `experiments/baseline/results/`
