# Collusion Detection Analysis - Quick Start Guide

## 📁 Files Included

### Analysis Scripts
- **`collusion_detection.py`** - Main analysis script (runs all detection methods)
- **`analyze_baseline.py`** - Focused analysis for 4 baseline experiments (A, B, C, D)
- **`visualize_collusion.py`** - Creates visual comparisons and charts

### Documentation
- **`METHODOLOGY.md`** - Detailed explanation of all detection methods
- **`collusion_report.txt`** - Full analysis report (generated)
- **`collusion_results.json`** - Raw quantitative results (generated)

---

## 🚀 Quick Start

### Option 1: Analyze Baseline Experiments (Recommended)

Analyzes the 4 core baseline experiments with clean output:

```bash
cd detection
python3 analyze_baseline.py
```

**Output includes:**
- Collusion scores ranked by severity
- Detailed metrics comparison
- **Temporal dynamics** - when collusion emerges/breaks down
- Change-point detection showing behavioral shifts

### Option 2: Analyze All Log Files

Analyzes every .log file in the logs directory:

```bash
cd detection
python3 collusion_detection.py
```

**Output:**
- Console report with all experiments ranked
- `outputs/collusion_report.txt` - detailed text report
- `outputs/collusion_results.json` - raw JSON data

---

## 🎯 Expected Experimental Results

Based on your design:

| Experiment | Communication | Transparency | Expected Score |
|------------|---------------|--------------|----------------|
| **D: Treatment** | ✓ | ✓ | **70-80** (highest) |
| **A: No Comm** | ✗ | ✓ | **40-50** (moderate) |
| **B: No Trans** | ✓ | ✗ | **50-60** (communication helps) |
| **C: Baseline** | ✗ | ✗ | **20-30** (lowest/competitive) |

### Hypotheses to Test:
1. **H1:** D > A (communication increases collusion)
2. **H2:** D > B (transparency increases collusion)  
3. **H3:** A,B > C (either feature enables some coordination)
4. **H4:** D > A+B-C (superadditive interaction effect)

---

## 📈 Key Metrics Explained

### 1. Collusion Score (0-100)
Overall likelihood of collusion based on all metrics.

### 2. Price Correlation
How closely wholesaler prices move together (0-1).
- 🚨 >0.8 = Strong coordination
- ✓ <0.5 = Competitive

### 3. Within-Day Price Variance  
Price difference between wholesalers on same day.
- 🚨 <5 = Nearly identical (suspicious)
- ✓ >20 = Differentiation

### 4. Margin Stability
How consistent profit margins are over time (0-1).
- 🚨 >0.8 = No price wars
- ✓ <0.6 = Competitive pressure

### 5. Focal Pricing
Frequency of round-number prices (0-1).
- 🚨 >0.8 = Coordination signal
- ✓ <0.5 = Normal distribution

### 6. Change-Point Detection (NEW)
Identifies when collusion patterns shift over time.
- Detects structural breaks in pricing behavior
- Shows distinct phases (e.g., competitive → collusive)
- Uses sliding 5-day windows for temporal analysis

---

## 💡 Interpretation Guide

### Strong Evidence of Collusion (Score > 70)
- Prices move together (correlation > 0.8)
- Minimal price differences (variance < 5)
- Stable margins (no competitive pressure)
- Consider: Agents may be explicitly coordinating

### Moderate Evidence (Score 50-70)  
- Some coordination signals present
- May be tacit collusion or parallel behavior
- Further investigation warranted

### Competitive Behavior (Score < 30)
- Prices vary independently
- Active price competition
- Normal market dynamics

---

## 🔧 Customization

### To Adjust Thresholds
Edit `collusion_detection.py` in the `_calculate_collusion_score()` method.

### To Add New Metrics
1. Add calculation method to `CollusionDetector` class
2. Call it in `analyze_experiment()`
3. Add to scoring in `_calculate_collusion_score()`

### To Modify Visualizations
Edit `visualize_collusion.py` chart creation functions.