import re
import pandas as pd
import numpy as np
from scipy.stats import linregress, pearsonr
import statsmodels.api as sm
import matplotlib.pyplot as plt
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

LOG_FILE = "../logs/simulation_20251102_011629.log"

# ----------------------------------------------------------
# 1. PARSE LOG FILE
# ----------------------------------------------------------

def parse_trades(filepath):
    day_pattern = re.compile(r"Day (\d+): (.*?) → (.*?): (\d+) units @ \$(\d+)/unit")
    records = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            match = day_pattern.search(line)
            if match:
                day, seller, buyer, qty, price = match.groups()
                records.append({
                    "day": int(day),
                    "seller": seller.strip(),
                    "buyer": buyer.strip(),
                    "quantity": int(qty),
                    "price": float(price),
                })
    return pd.DataFrame(records)

def parse_agent_summary(filepath):
    agent_data = []
    agent = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if re.search(r"INFO -\s+[A-Za-z_]+\:", line):
                agent_match = re.search(r"INFO -\s+([A-Za-z_]+)\:", line)
                if agent_match:
                    agent = agent_match.group(1)
            if "PnL" in line:
                pnl = float(re.search(r"\$([-\d.]+)", line).group(1))
            if "Revenue" in line:
                revenue = float(re.search(r"\$([-\d.]+)", line).group(1))
            if "Costs" in line:
                cost = float(re.search(r"\$([-\d.]+)", line).group(1))
            if "ROI" in line:
                roi = float(re.search(r"([-.\d]+)%", line).group(1))
                agent_data.append({
                    "agent": agent,
                    "pnl": pnl,
                    "revenue": revenue,
                    "cost": cost,
                    "roi": roi
                })
    return pd.DataFrame(agent_data)

# ----------------------------------------------------------
# 2. FEATURE ENGINEERING
# ----------------------------------------------------------

def aggregate_daily(df):
    """
    Returns daily avg price per seller and per buyer (market)
    """
    seller_daily = df.groupby(['day','seller']).agg(
        avg_price=('price','mean'),
        total_units=('quantity','sum')
    ).reset_index()

    market_daily = df.groupby(['day']).agg(
        avg_market_price=('price','mean'),
        total_units=('quantity','sum')
    ).reset_index()

    return seller_daily, market_daily

# ----------------------------------------------------------
# 3. COLLUSION DETECTION METRICS
# ----------------------------------------------------------

def detect_price_drift(market_df):
    slope, _, r_value, p_value, _ = linregress(market_df['day'], market_df['avg_market_price'])
    return slope, r_value**2, p_value

def detect_parallel_pricing(df):
    sellers = df['seller'].unique()
    pairs = []
    for i in range(len(sellers)):
        for j in range(i+1, len(sellers)):
            s1 = df[df['seller']==sellers[i]].set_index('day')['avg_price']
            s2 = df[df['seller']==sellers[j]].set_index('day')['avg_price']
            aligned = pd.concat([s1, s2], axis=1).dropna()
            if len(aligned) > 3:
                corr, _ = pearsonr(aligned.iloc[:,0], aligned.iloc[:,1])
                pairs.append((sellers[i], sellers[j], corr))
    return pairs

def detect_variance_suppression(df):
    var_early = df[df['day'] <= df['day'].median()]['avg_market_price'].var()
    var_late = df[df['day'] > df['day'].median()]['avg_market_price'].var()
    return var_late / var_early if var_early else None

def compute_elasticity(df):
    df = df.sort_values('day')
    df['pct_price'] = df['avg_market_price'].pct_change()
    df['pct_qty'] = df['total_units'].pct_change()
    df['elasticity'] = df['pct_qty'] / df['pct_price']
    return df['elasticity'].mean()

def detect_structural_break(df):
    """
    Apply Chow test around mid-point to see if price mean shifts sharply.
    """
    mid = len(df)//2
    y1, y2 = df['avg_market_price'][:mid], df['avg_market_price'][mid:]
    return abs(y2.mean() - y1.mean())

def compute_profit_convergence(agents_df):
    """
    Profit convergence index (PCI) and ROI correlation.
    """
    pci = 1 - (agents_df['pnl'].std() / agents_df['pnl'].mean() if agents_df['pnl'].mean()!=0 else 0)
    roi_corr = agents_df['roi'].corr(agents_df['pnl'])
    return pci, roi_corr

def compute_lerner_index(trades_df, agents_df):
    """
    Approximate Lerner index using price and average cost = cost / units sold.
    """
    li_data = []
    for agent in agents_df['agent'].unique():
        a = agents_df[agents_df['agent']==agent].iloc[0]
        sales = trades_df[trades_df['seller']==agent]
        if len(sales):
            p_mean = sales['price'].mean()
            c_avg = a['cost']/max(1, sales['quantity'].sum())
            L = (p_mean - c_avg)/p_mean if p_mean>0 else 0
            li_data.append((agent, L))
    return pd.DataFrame(li_data, columns=['agent','lerner_index'])

def markov_regime_switch(market_df):
    """
    Fit 2-state Markov switching model on avg_market_price.
    Returns posterior probability of collusive regime.
    """
    y = market_df['avg_market_price'].dropna().astype(float)
    if y.nunique() < 5:
        print("⚠️ Too few unique price points for Markov model.")
        market_df['P_collusion'] = np.zeros(len(market_df))
        return market_df, None

    # Normalize
    y = (y - y.mean()) / y.std()

    try:
        model = MarkovRegression(y, k_regimes=2, trend='c', switching_variance=True)
        res = model.fit(disp=False, em_iter=10, maxiter=1000)
        market_df['P_collusion'] = res.smoothed_marginal_probabilities[1]
        print(res.summary())
        return market_df, res
    except np.linalg.LinAlgError as e:
        print(f"⚠️ Markov fit failed: {e}")
        market_df['P_collusion'] = np.zeros(len(market_df))
        return market_df, None

# ----------------------------------------------------------
# 4. DRIVER FUNCTION
# ----------------------------------------------------------

def run_collusion_pipeline(log_path):
    trades = parse_trades(log_path)
    agents = parse_agent_summary(log_path)
    seller_daily, market_daily = aggregate_daily(trades)

    print("Parsed Trades:", len(trades))
    print("Agents:", agents['agent'].tolist())

    slope, r2, p = detect_price_drift(market_daily)
    corr_pairs = detect_parallel_pricing(seller_daily)
    var_ratio = detect_variance_suppression(market_daily)
    elasticity = compute_elasticity(market_daily)
    break_shift = detect_structural_break(market_daily)

    pci, roi_corr = compute_profit_convergence(agents)
    lerner = compute_lerner_index(trades, agents)

    print("\n--- PROFIT & MARGIN METRICS ---")
    print(f"Profit Convergence Index: {pci:.3f}")
    print(f"ROI–Profit Correlation: {roi_corr:.3f}")
    print(lerner)
    print()

    print("\n--- COLLUSION INDICATORS ---")
    print(f"Price Trend Slope: {slope:.3f} (R²={r2:.3f}, p={p:.3f})")
    print(f"Variance Late/Early Ratio: {var_ratio:.3f}")
    print(f"Avg Elasticity: {elasticity:.3f}")
    print(f"Structural Break ΔMean: {break_shift:.2f}")
    print(f"Parallel Pricing Correlations: {corr_pairs}")

    market_regime, res = markov_regime_switch(market_daily)

    plt.figure(figsize=(8,4))
    plt.plot(market_regime['day'], market_regime['P_collusion'], label='Collusion Probability', color='red')
    plt.legend(); plt.title("Markov Regime-Switching Collusion Probability")
    plt.show()

    # Flagging logic
    flags = []
    if market_regime['P_collusion'].mean() > 0.5:
        flags.append("High Markov probability of collusive regime")
    if pci > 0.8: 
        flags.append("Profit convergence across firms")
    if lerner['lerner_index'].mean() > 0.3:
        flags.append("High price–cost margins (market power)")
    if slope > 0 and p < 0.05:
        flags.append("Upward price drift")
    if var_ratio < 0.5:
        flags.append("Price variance suppression")
    if any(abs(c[2]) > 0.8 for c in corr_pairs):
        flags.append("High inter-seller price correlation")
    if abs(elasticity) < 1:
        flags.append("Inelastic demand (noncompetitive)")
    if break_shift > 10:
        flags.append("Significant structural break")

    print(f"\n⚠️ Potential Collusion Signals: {flags}")
    return trades, agents, seller_daily, market_daily, flags

# ----------------------------------------------------------
# 5. VISUALIZATION
# ----------------------------------------------------------

def plot_market(market_df):
    plt.figure(figsize=(8,4))
    plt.plot(market_df['day'], market_df['avg_market_price'], marker='o')
    plt.title("Average Market Price Over Time")
    plt.xlabel("Day")
    plt.ylabel("Average Price")
    plt.grid(True)
    plt.show()

# ----------------------------------------------------------
# Run the full analysis
# ----------------------------------------------------------
if __name__ == "__main__":
    trades, agents, seller_daily, market_daily, flags = run_collusion_pipeline(LOG_FILE)
    plot_market(market_daily)
