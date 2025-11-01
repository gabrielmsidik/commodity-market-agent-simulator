# Baseline Experiments - 21-Day Comparison Study

## Overview

This directory contains scripts to run 4 baseline experiments testing the causal impact of communication and price transparency on collusion.

## Experimental Design

| Experiment | Communication | Price Transparency | Purpose |
|------------|--------------|-------------------|---------|
| **A: No Communication** | ❌ Disabled | ✅ Enabled | Test if communication causes collusion |
| **B: No Transparency** | ✅ Enabled | ❌ Disabled | Test if price visibility enables coordination |
| **C: Full Baseline** | ❌ Disabled | ❌ Disabled | Pure competitive baseline |
| **D: Treatment** | ✅ Enabled | ✅ Enabled | Current system (full features) |

## Quick Start

### Experiment D: Treatment (READY TO RUN ✅)

This experiment works out-of-the-box with the current codebase:

```bash
# Run 21-day treatment (communication + transparency)
PYTHONPATH=. python scratch/baseline_experiments/run_21day_treatment.py
```

**Runtime**: ~30-40 minutes
**Cost**: ~$0.50-1.00 (GPT-4o-mini)
**Output**: `scratch/baseline_experiments/results/experiment_D_treatment_*.json`

---

## Running Other Experiments

### Experiment A: No Communication

**Requires**: Temporarily disabling `wholesaler_discussion` node

**Option 1: Quick Manual Edit**
1. Edit `src/graph/workflow.py`
2. Comment out lines that reference `wholesaler_discussion`:
   ```python
   # graph.add_node("wholesaler_discussion", nodes.wholesaler_discussion)
   ```
3. Change routing to skip communication:
   ```python
   # In should_negotiate() router:
   return "set_market_offers"  # Instead of "wholesaler_discussion"
   ```
4. Run:
   ```bash
   PYTHONPATH=. python scratch/baseline_experiments/run_21day_no_communication.py
   ```
5. **Important**: Revert changes after experiment completes!

**Option 2: Configuration Flag (Recommended for Future)**
- Add `enable_communication` parameter to SimulationConfig
- Modify workflow.py to check flag before adding communication node
- More robust but requires refactoring

---

### Experiment B: No Transparency

**Requires**: Disabling `get_competitor_activity()` tool

**Implementation**:
1. Edit `src/agents/tools.py`
2. Modify `WholesalerTools.get_competitor_activity()` to return empty data:
   ```python
   def get_competitor_activity(self) -> Dict[str, Any]:
       """Return no competitor information (transparency disabled)."""
       return {
           "competitor_name": None,
           "recent_prices": [],
           "recent_quantities": [],
           "avg_price_last_5_days": None,
           "is_active": False,
           "message": "Price transparency disabled for this experiment"
       }
   ```
3. Run:
   ```bash
   PYTHONPATH=. python scratch/baseline_experiments/run_21day_no_transparency.py
   ```
4. Revert changes after experiment

---

### Experiment C: Full Baseline

**Requires**: Both modifications above (A + B)

1. Disable communication (Experiment A steps)
2. Disable transparency (Experiment B steps)
3. Run:
   ```bash
   PYTHONPATH=. python scratch/baseline_experiments/run_21day_full_baseline.py
   ```
4. Revert all changes

---

## Analysis

After running all experiments, use the comparison script:

```bash
PYTHONPATH=. python scratch/baseline_experiments/compare_results.py
```

This will generate:
- Statistical comparison (t-tests on price convergence)
- Visualization plots (price trends, convergence over time)
- Summary report (collusion metrics across experiments)

---

## Expected Results

Based on 3-day pilot test:

### Experiment D (Treatment)
- **Predicted**: High collusion (98%+ convergence)
- **Mechanism**: Communication + transparency enables coordination

### Experiment A (No Communication)
- **Predicted**: Lower collusion (70-80% convergence?)
- **Hypothesis**: Transparency alone insufficient without coordination channel

### Experiment B (No Transparency)
- **Predicted**: Minimal collusion (50-60% convergence?)
- **Hypothesis**: Cannot coordinate without monitoring capability

### Experiment C (Full Baseline)
- **Predicted**: Competitive pricing (30-40% convergence)
- **Hypothesis**: Bertrand competition emerges

---

## Files

### Experiment Scripts
- `run_21day_treatment.py` - Experiment D (ready to run)
- `run_21day_no_communication.py` - Experiment A (requires workflow edit)
- `run_21day_no_transparency.py` - Experiment B (requires tools edit)
- `run_21day_full_baseline.py` - Experiment C (requires both edits)

### Analysis Scripts
- `compare_results.py` - Statistical comparison across experiments
- `visualize_convergence.py` - Plot price trends and convergence

### Results
- `results/` - JSON outputs from each experiment
- `analysis/` - Comparative analysis reports and visualizations

---

## Recommended Execution Order

1. ✅ **Run Experiment D first** (current setup, no changes needed)
2. **While D runs, prepare scripts for A, B, C**
3. **Run A, B, C sequentially** (manual edits required)
4. **Run comparison analysis** after all 4 complete

**Total Time**: ~2.5-3 hours (4 experiments × 40 mins each)
**Total Cost**: ~$2-4 (GPT-4o-mini)

---

## Future Improvements

### Configuration-Based Approach
Instead of manual code edits, implement:

```python
# In SimulationConfig
@dataclass
class SimulationConfig:
    # ... existing fields ...
    enable_communication: bool = True
    enable_price_transparency: bool = True
```

Then modify:
- `workflow.py` to conditionally add communication node
- `tools.py` to check transparency flag

This would allow:
```python
# Experiment A
config = SimulationConfig(
    name="exp_A",
    enable_communication=False,  # Just toggle flags!
    enable_price_transparency=True
)
```

**Benefits**:
- No manual code edits
- Less error-prone
- Easier to run batches
- Reproducible

**Timeline**: ~4-6 hours to implement properly

---

## Troubleshooting

### Communication not disabled
- Check that `wholesaler_discussion` node is commented out in workflow.py
- Verify logs show 0 communications (not 42 messages)

### Transparency still working
- Check `WholesalerTools.get_competitor_activity()` returns empty data
- Verify agents' prompts don't mention competitor prices

### Simulation crashes
- Ensure routing logic is updated when disabling nodes
- Check that all conditional edges handle missing nodes

---

## Contact

For questions or issues:
- Check simulation logs in `logs/`
- Verify config in `.env` file
- Review experiment outputs in `experiments/baseline/results/`
