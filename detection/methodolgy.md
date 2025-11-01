# Collusion Detection Methodology
## Quantitative Methods for Detecting Price Coordination Without Chat Logs

### Overview
This analysis framework detects collusive behavior in oligopoly markets by examining pricing patterns, margins, and market dynamics without requiring access to agent communications. The methods are based on economic theory and empirical research on cartel detection.

---

## Detection Methods

### 1. **Price Correlation Analysis**
**Method:** Pearson correlation coefficient between Wholesaler 1 and Wholesaler 2 daily prices

**Formula:**
```
r = Σ[(x_i - x̄)(y_i - ȳ)] / √[Σ(x_i - x̄)² × Σ(y_i - ȳ)²]
```

**Interpretation:**
- **r > 0.8**: 🚨 Strong evidence of coordination
- **0.5 < r < 0.8**: ⚠️ Moderate correlation (possible tacit collusion)
- **r < 0.5**: ✓ Normal competitive variation

**Rationale:** In competitive markets, firms' pricing decisions should be relatively independent. High correlation suggests coordinated behavior.

---

### 2. **Price Parallelism Score**
**Method:** Calculate the fraction of periods where both wholesalers' prices move in the same direction

**Formula:**
```
Parallelism = (# same-direction moves) / (# total price changes)
```

**Interpretation:**
- **> 0.75**: 🚨 Very high parallelism (likely coordination)
- **0.5 - 0.75**: ⚠️ Moderate parallelism
- **< 0.5**: ✓ Independent pricing decisions

**Rationale:** Coordinating firms typically raise or lower prices together in response to market signals, while competitive firms may move in opposite directions.

---

### 3. **Price Variance Analysis**
**Method:** Measure within-day price differences and across-day price stability

**Metrics:**
- **Within-day variance:** σ² of price differences between wholesalers on same day
- **Across-day variance:** σ² of each wholesaler's prices over time

**Interpretation:**
- **Within-day variance < 5**: 🚨 Very similar pricing (coordination)
- **5 < variance < 20**: ⚠️ Some price differences
- **variance > 20**: ✓ Significant competitive differentiation

**Rationale:** Collusive agreements typically result in nearly identical prices, while competition leads to price dispersion.

---

### 4. **Margin Stability Index**
**Method:** Track pricing margins over time and calculate stability

**Formula:**
```
Margin = (Sale Price - Purchase Cost) / Sale Price
Stability = 1 - StdDev(Margins)
```

**Interpretation:**
- **Stability > 0.8**: 🚨 Very stable margins (no price wars)
- **0.6 < Stability < 0.8**: ⚠️ Moderate stability
- **Stability < 0.6**: ✓ Competitive margin compression

**Rationale:** Competitive markets see margin compression during price wars. Collusive markets maintain stable, high margins.

---

### 5. **Focal Pricing Detection**
**Method:** Analyze frequency of "round number" prices

**Formula:**
```
Focal Ratio = (# prices ending in 0 or 5) / (# total prices)
```

**Interpretation:**
- **> 0.8**: 🚨 Strong focal point coordination
- **0.5 - 0.8**: ⚠️ Some focal pricing
- **< 0.5**: ✓ Normal price distribution

**Rationale:** Collusive firms often use round numbers as coordination devices ("focal points") to achieve tacit agreement without explicit communication.

---

### 6. **Market Concentration (HHI)**
**Method:** Herfindahl-Hirschman Index

**Formula:**
```
HHI = Σ(market_share_i)²
```

**Interpretation:**
- **HHI > 0.65**: High concentration (easier to collude)
- **0.5 < HHI < 0.65**: Moderate concentration
- **HHI < 0.5**: More competitive market structure

**Rationale:** More balanced market shares suggest competitive behavior rather than one firm dominating through aggressive pricing.

---

### 7. **Value Extraction Analysis**
**Method:** Calculate share of total supply chain value captured by wholesalers vs. sellers

**Formula:**
```
Wholesaler Share = Wholesaler Revenue / Total Revenue
```

**Interpretation:**
- **> 0.65**: 🚨 Excessive value extraction (exploiting market power)
- **0.55 - 0.65**: ⚠️ Higher than competitive benchmark
- **< 0.55**: ✓ Normal distribution

**Rationale:** Collusive wholesalers can extract more value from suppliers by maintaining high prices while keeping purchase prices low.

---

## Composite Collusion Score

The overall collusion score (0-100) is calculated as a weighted sum:

```
Score = 30×(Price Correlation) 
      + 25×(Price Parallelism)
      + max(0, 15 - Within-Day Variance)
      + 15×(Margin Stability)
      + 10×(Focal Pricing Ratio)
      + 5×(Value Extraction Bonus)
```

**Interpretation:**
- **70-100**: 🚨 Very High likelihood of collusion
- **50-70**: ⚠️ High likelihood (suspicious behavior)
- **30-50**: ⚠️ Moderate indicators present
- **0-30**: ✓ Competitive market behavior

---

## Experimental Design Analysis

### Expected Effects:

1. **Communication → Collusion**
   - Direct coordination possible
   - Expected effect: +20-30 points

2. **Transparency → Collusion** 
   - Price monitoring enables tacit collusion
   - Expected effect: +10-20 points

3. **Combined Effect**
   - Strongest collusion potential
   - Synergistic effects possible

---

## Usage Instructions

### Running the Analysis

```bash
# 1. Place all log files in /mnt/user-data/uploads/

# 2. Run detection analysis
python3 collusion_detection.py

# 3. Generate visualizations
python3 visualize_collusion.py
```

### Output Files

1. **collusion_results.json**: Raw quantitative results
2. **collusion_report.txt**: Detailed text report
3. **Console output**: Visual charts and rankings

### Interpreting Results

Compare experiments to identify:
- Which conditions enable collusion
- Strength of communication vs. transparency effects
- Whether interaction effects exist
- Specific metrics showing strongest signals

---

## Statistical Robustness

### Minimum Requirements:
- At least 10 trading days for reliable correlation
- Multiple price observations per day
- Complete data for both wholesalers

### Limitations:
1. Margin calculations use estimated purchase costs
2. Small sample sizes may reduce statistical power
3. Does not detect sophisticated "punishment strategies"

---

## References

This methodology is based on:
- OECD Guidelines for Fighting Bid Rigging in Public Procurement
- European Commission Guidelines on Cartel Detection
- Economic literature on tacit collusion (Kühn 2001, Motta 2004)
- Empirical studies of parallel pricing behavior

---

## Contact & Support

For questions about methodology or implementation, refer to:
- Economic theory of oligopoly (Tirole, "Theory of Industrial Organization")
- Antitrust economics literature on conscious parallelism
- Game theory of repeated games and coordination