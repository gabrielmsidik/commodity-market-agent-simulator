# Collusion Detection Analysis - Quick Start Guide

## 📁 Files Included

### Analysis Scripts
- **`collusion_detection.py`** - Main analysis script (runs all detection methods)
- **`visualize_collusion.py`** - Creates visual comparisons and charts

### Documentation
- **`METHODOLOGY.md`** - Detailed explanation of all detection methods
- **`collusion_report.txt`** - Full analysis report (generated)
- **`collusion_results.json`** - Raw quantitative results (generated)

---

## 🚀 Quick Start

### Current Analysis Results

Based on your 2 uploaded log files:

**Experiment D (Treatment)** - Communication + Transparency
- **Collusion Score: 65.7/100** ⚠️ HIGH
- Price correlation: 0.817 🚨 (very high)
- Within-day price variance: 2.86 (very low)
- Margin stability: 0.979 🚨 (extremely stable)
- **Conclusion:** Strong evidence of collusive behavior

**Experiment A (No Communication)** - Transparency Only  
- **Collusion Score: 42.1/100** ⚠️ MODERATE
- Price correlation: 0.591 (moderate)
- Within-day price variance: 439.26 (high variation)
- Margin stability: 0.615 (moderate)
- **Conclusion:** Some coordination signals, but more competitive

### Key Finding
**Communication Effect: +23.5 points**
- Enabling communication increased collusion likelihood by 56%
- This suggests explicit coordination is the primary driver

---

## 📊 To Analyze All 4 Experiments

### Step 1: Upload Missing Log Files
You currently have 2 of 4 experiments. Please upload:
- **Experiment B** (Communication, No Transparency)
- **Experiment C** (No Communication, No Transparency - baseline)

### Step 2: Run Analysis
```bash
cd ./detection
python3 collusion_detection.py
python3 visualize_collusion.py
```

### Step 3: Review Results
- Console output shows visual charts
- `collusion_report.txt` has detailed metrics
- `collusion_results.json` has raw data

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