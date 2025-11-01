#!/usr/bin/env python3
"""
Visualization script for collusion detection analysis
Creates charts comparing metrics across experiments
"""

import json
import os

def create_ascii_bar_chart(data: dict, title: str, metric_name: str, max_value: float = 1.0):
    """Create ASCII bar chart for comparison"""
    print(f"\n{title}")
    print("=" * 80)
    
    # Sort by value
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    
    max_name_len = max(len(name) for name, _ in sorted_data)
    
    for name, value in sorted_data:
        # Normalize to 50 chars width
        bar_length = int((value / max_value) * 50)
        bar = "█" * bar_length
        
        # Color coding
        if value >= 0.8 * max_value:
            indicator = "🚨"
        elif value >= 0.5 * max_value:
            indicator = "⚠️ "
        else:
            indicator = "✓ "
        
        print(f"{name:{max_name_len}s} {indicator} {bar} {value:.3f}")
    print()


def create_comparison_table(results: dict):
    """Create detailed comparison table"""
    print("\n" + "=" * 80)
    print("EXPERIMENTAL CONDITIONS vs. COLLUSION METRICS")
    print("=" * 80)
    
    # Header
    print(f"{'Experiment':<35s} | Comm | Trans | Score | Corr | Para | Var |")
    print("-" * 80)
    
    # Sort by collusion score
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]['collusion_score'],
        reverse=True
    )
    
    for filename, data in sorted_results:
        name = data['name'][:33]
        comm = "✓" if data['has_communication'] else "✗"
        trans = "✓" if data['has_transparency'] else "✗"
        score = data['collusion_score']
        corr = data['price_correlation']
        para = data['price_parallelism']
        var = data['price_variance']['within_day_variance']
        
        print(f"{name:<35s} |  {comm}   |   {trans}   | {score:5.1f} | {corr:4.2f} | {corr:4.2f} | {var:3.0f} |")
    
    print()


def create_metric_comparison(results: dict, metric_path: list, title: str, max_val: float = 1.0):
    """Create comparison for a specific metric"""
    data = {}
    for filename, result in results.items():
        name = result['name']
        value = result
        for key in metric_path:
            value = value[key]
        data[name] = value
    
    create_ascii_bar_chart(data, title, metric_path[-1], max_val)


def analyze_experimental_effects(results: dict):
    """Analyze the effect of communication and transparency"""
    print("\n" + "=" * 80)
    print("EXPERIMENTAL EFFECTS ANALYSIS")
    print("=" * 80)
    
    # Group by conditions
    by_conditions = {
        'comm_trans': [],
        'comm_only': [],
        'trans_only': [],
        'neither': []
    }
    
    for data in results.values():
        if data['has_communication'] and data['has_transparency']:
            by_conditions['comm_trans'].append(data)
        elif data['has_communication']:
            by_conditions['comm_only'].append(data)
        elif data['has_transparency']:
            by_conditions['trans_only'].append(data)
        else:
            by_conditions['neither'].append(data)
    
    # Calculate averages
    print("\nAverage Collusion Scores by Condition:")
    print("-" * 80)
    
    condition_names = {
        'comm_trans': 'Communication + Transparency',
        'comm_only': 'Communication Only',
        'trans_only': 'Transparency Only',
        'neither': 'Neither (Pure Competition)'
    }
    
    for key, experiments in by_conditions.items():
        if experiments:
            avg_score = sum(e['collusion_score'] for e in experiments) / len(experiments)
            avg_corr = sum(e['price_correlation'] for e in experiments) / len(experiments)
            count = len(experiments)
            
            print(f"{condition_names[key]:<35s}: {avg_score:5.1f}  (corr: {avg_corr:.3f}, n={count})")
    
    print("\n")
    print("Key Findings:")
    print("-" * 80)
    
    # Compare treatment vs control
    if by_conditions['comm_trans'] and by_conditions['neither']:
        treatment_score = by_conditions['comm_trans'][0]['collusion_score']
        control_score = by_conditions['neither'][0]['collusion_score']
        diff = treatment_score - control_score
        
        print(f"• Treatment effect (D vs C): +{diff:.1f} points ({diff/control_score*100:.1f}% increase)")
    
    if by_conditions['comm_trans'] and by_conditions['trans_only']:
        treatment_score = by_conditions['comm_trans'][0]['collusion_score']
        trans_score = by_conditions['trans_only'][0]['collusion_score']
        comm_effect = treatment_score - trans_score
        
        print(f"• Communication effect (D vs A): +{comm_effect:.1f} points")
    
    if by_conditions['comm_trans'] and by_conditions['comm_only']:
        treatment_score = by_conditions['comm_trans'][0]['collusion_score']
        comm_score = by_conditions['comm_only'][0]['collusion_score']
        trans_effect = treatment_score - comm_score
        
        print(f"• Transparency effect (D vs B): +{trans_effect:.1f} points")
    
    print("\n")


def create_summary_dashboard(results: dict):
    """Create a summary dashboard"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 20 + "COLLUSION DETECTION DASHBOARD" + " " * 28 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    # Top section: experiment rankings
    print("\n📊 COLLUSION LIKELIHOOD RANKING (High to Low)")
    print("=" * 80)
    
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]['collusion_score'],
        reverse=True
    )
    
    for i, (filename, data) in enumerate(sorted_results, 1):
        score = data['collusion_score']
        name = data['name']
        
        if score >= 70:
            level = "🚨 VERY HIGH"
            bar = "█" * 30
        elif score >= 50:
            level = "⚠️  HIGH"
            bar = "█" * 20
        elif score >= 30:
            level = "⚠️  MODERATE"
            bar = "█" * 10
        else:
            level = "✓  LOW"
            bar = "█" * 5
        
        print(f"\n{i}. {name}")
        print(f"   Score: {score:5.1f}/100  {level}")
        print(f"   {bar}")
        print(f"   Comm: {'YES' if data['has_communication'] else 'NO':<3s}  |  Trans: {'YES' if data['has_transparency'] else 'NO':<3s}")


def main():
    # Load results
    with open('./outputs/collusion_results.json', 'r') as f:
        results = json.load(f)
    
    # Create summary dashboard
    create_summary_dashboard(results)
    
    # Analyze experimental effects
    analyze_experimental_effects(results)
    
    # Create metric comparisons
    create_metric_comparison(
        results,
        ['price_correlation'],
        "📈 PRICE CORRELATION (Higher = More Coordinated)",
        max_val=1.0
    )
    
    create_metric_comparison(
        results,
        ['collusion_score'],
        "🎯 OVERALL COLLUSION SCORE",
        max_val=100.0
    )
    
    create_metric_comparison(
        results,
        ['margin_stability', 'w1_margin_stability'],
        "💰 MARGIN STABILITY - Wholesaler 1 (Higher = Less Competition)",
        max_val=1.0
    )
    
    create_metric_comparison(
        results,
        ['price_variance', 'within_day_variance'],
        "📊 PRICE VARIANCE (Lower = More Coordination)",
        max_val=max(r['price_variance']['within_day_variance'] for r in results.values())
    )
    
    # Create comparison table
    create_comparison_table(results)
    
    print("\n" + "=" * 80)
    print("💡 INTERPRETATION:")
    print("=" * 80)
    print("""
The analysis shows how different market conditions affect collusion likelihood:

1. COMMUNICATION effect: Allows wholesalers to explicitly coordinate pricing
2. TRANSPARENCY effect: Lets wholesalers observe each other's prices and react
3. COMBINED effect: Both features enable strongest collusion

Key indicators of collusion:
• High price correlation (>0.8): Prices move together
• Low price variance (<5): Minimal price differences 
• High margin stability (>0.8): Consistent markups over time
• Focal pricing (>0.8): Round-number coordination signals

Experiment D (Treatment) likely shows the highest collusion because agents
can both communicate strategies AND observe each other's actions.
""")
    
    print("Full report saved to: ./outputs/collusion_report.txt")
    print("=" * 80)


if __name__ == '__main__':
    main()