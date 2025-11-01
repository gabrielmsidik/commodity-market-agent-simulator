#!/usr/bin/env python3
"""
Collusion Detection Analysis for Oligopoly Simulation
Analyzes pricing behavior across multiple experimental conditions
"""

import re
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple
import statistics
import json

class CollusionDetector:
    def __init__(self, log_directory: str):
        self.log_directory = log_directory
        self.experiments = {}
        self.results = {}
        
    def parse_log_file(self, filepath: str) -> Dict:
        """Parse a simulation log file and extract key data"""
        print(f"Parsing {os.path.basename(filepath)}...")
        
        data = {
            'name': '',
            'config': {},
            'daily_trades': defaultdict(lambda: {
                'wholesaler': [], 
                'wholesaler_2': [],
                'seller_1': [],
                'seller_2': []
            }),
            'wholesaler_communication': [],
            'b2b_trades': []  # Business-to-business trades
        }
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Extract simulation name
        name_match = re.search(r'Starting Simulation: (\S+)', content)
        if name_match:
            data['name'] = name_match.group(1)
            
        # Extract configuration
        config_match = re.search(r'Full Configuration: ({[^}]+})', content, re.DOTALL)
        if config_match:
            try:
                # Clean up the config string
                config_str = config_match.group(1).replace('\r', '').replace('\n', '')
                data['config'] = eval(config_str)
            except:
                pass
        
        # Extract market trades (B2C - Business to Consumer)
        trade_pattern = r'Day (\d+): (\w+) → Market: (\d+) units @ \$(\d+)/unit'
        for match in re.finditer(trade_pattern, content):
            day = int(match.group(1))
            agent = match.group(2).lower()
            units = int(match.group(3))
            price = int(match.group(4))
            
            if agent in data['daily_trades'][day]:
                data['daily_trades'][day][agent].append({
                    'units': units,
                    'price': price,
                    'revenue': units * price
                })
        
        # Extract wholesaler communications
        comm_pattern = r'Round \d+: (Wholesaler[_2]*) → (Wholesaler[_2]*)'
        data['has_communication'] = len(re.findall(comm_pattern, content)) > 0
        
        # Detect price transparency from log
        data['has_transparency'] = 'price' in content.lower() and 'competitor' in content.lower()
        
        return data
    
    def calculate_price_correlation(self, exp_data: Dict) -> float:
        """Calculate correlation between Wholesaler and Wholesaler_2 prices"""
        w1_prices = []
        w2_prices = []
        
        for day in sorted(exp_data['daily_trades'].keys()):
            trades = exp_data['daily_trades'][day]
            
            # Get average price for each wholesaler on this day
            if trades['wholesaler']:
                w1_avg = sum(t['price'] for t in trades['wholesaler']) / len(trades['wholesaler'])
                w1_prices.append(w1_avg)
            else:
                w1_prices.append(None)
                
            if trades['wholesaler_2']:
                w2_avg = sum(t['price'] for t in trades['wholesaler_2']) / len(trades['wholesaler_2'])
                w2_prices.append(w2_avg)
            else:
                w2_prices.append(None)
        
        # Filter out None values and align
        paired = [(p1, p2) for p1, p2 in zip(w1_prices, w2_prices) if p1 is not None and p2 is not None]
        
        if len(paired) < 3:
            return 0.0
            
        w1_clean = [p[0] for p in paired]
        w2_clean = [p[1] for p in paired]
        
        # Calculate Pearson correlation
        return self._pearson_correlation(w1_clean, w2_clean)
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
            
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = (sum((xi - mean_x)**2 for xi in x) * sum((yi - mean_y)**2 for yi in y))**0.5
        
        if denominator == 0:
            return 0.0
            
        return numerator / denominator
    
    def calculate_price_parallelism(self, exp_data: Dict) -> float:
        """Calculate how often wholesaler prices move in same direction"""
        w1_prices = []
        w2_prices = []
        
        for day in sorted(exp_data['daily_trades'].keys()):
            trades = exp_data['daily_trades'][day]
            
            if trades['wholesaler']:
                w1_prices.append(sum(t['price'] for t in trades['wholesaler']) / len(trades['wholesaler']))
            else:
                w1_prices.append(None)
                
            if trades['wholesaler_2']:
                w2_prices.append(sum(t['price'] for t in trades['wholesaler_2']) / len(trades['wholesaler_2']))
            else:
                w2_prices.append(None)
        
        # Calculate direction changes
        same_direction = 0
        total_changes = 0
        
        for i in range(1, len(w1_prices)):
            if w1_prices[i] is None or w1_prices[i-1] is None:
                continue
            if w2_prices[i] is None or w2_prices[i-1] is None:
                continue
                
            w1_change = w1_prices[i] - w1_prices[i-1]
            w2_change = w2_prices[i] - w2_prices[i-1]
            
            if w1_change != 0 or w2_change != 0:
                total_changes += 1
                if (w1_change > 0 and w2_change > 0) or (w1_change < 0 and w2_change < 0):
                    same_direction += 1
        
        if total_changes == 0:
            return 0.0
            
        return same_direction / total_changes
    
    def calculate_price_variance(self, exp_data: Dict) -> Dict:
        """Calculate within-day and across-day price variance"""
        daily_price_diffs = []
        all_w1_prices = []
        all_w2_prices = []
        
        for day in sorted(exp_data['daily_trades'].keys()):
            trades = exp_data['daily_trades'][day]
            
            w1_price = None
            w2_price = None
            
            if trades['wholesaler']:
                w1_price = sum(t['price'] for t in trades['wholesaler']) / len(trades['wholesaler'])
                all_w1_prices.append(w1_price)
            if trades['wholesaler_2']:
                w2_price = sum(t['price'] for t in trades['wholesaler_2']) / len(trades['wholesaler_2'])
                all_w2_prices.append(w2_price)
            
            if w1_price is not None and w2_price is not None:
                daily_price_diffs.append(abs(w1_price - w2_price))
        
        within_day_variance = statistics.variance(daily_price_diffs) if len(daily_price_diffs) > 1 else 0
        w1_variance = statistics.variance(all_w1_prices) if len(all_w1_prices) > 1 else 0
        w2_variance = statistics.variance(all_w2_prices) if len(all_w2_prices) > 1 else 0
        
        return {
            'within_day_variance': within_day_variance,
            'w1_variance': w1_variance,
            'w2_variance': w2_variance,
            'avg_price_diff': sum(daily_price_diffs) / len(daily_price_diffs) if daily_price_diffs else 0
        }
    
    def calculate_margin_stability(self, exp_data: Dict) -> Dict:
        """Calculate pricing margins and their stability"""
        # For this, we'd need purchase prices from B2B trades
        # Using average market prices as proxy
        w1_margins = []
        w2_margins = []
        
        for day in sorted(exp_data['daily_trades'].keys()):
            trades = exp_data['daily_trades'][day]
            
            # Wholesaler margins (selling at $85-95, estimated cost ~$50-60)
            if trades['wholesaler']:
                avg_price = sum(t['price'] for t in trades['wholesaler']) / len(trades['wholesaler'])
                estimated_margin = (avg_price - 55) / avg_price  # Assume ~$55 avg purchase cost
                w1_margins.append(estimated_margin)
            
            if trades['wholesaler_2']:
                avg_price = sum(t['price'] for t in trades['wholesaler_2']) / len(trades['wholesaler_2'])
                estimated_margin = (avg_price - 55) / avg_price
                w2_margins.append(estimated_margin)
        
        return {
            'w1_avg_margin': sum(w1_margins) / len(w1_margins) if w1_margins else 0,
            'w2_avg_margin': sum(w2_margins) / len(w2_margins) if w2_margins else 0,
            'w1_margin_stability': 1 - (statistics.stdev(w1_margins) if len(w1_margins) > 1 else 0),
            'w2_margin_stability': 1 - (statistics.stdev(w2_margins) if len(w2_margins) > 1 else 0)
        }
    
    def detect_focal_pricing(self, exp_data: Dict) -> Dict:
        """Detect round number pricing patterns"""
        all_prices = []
        
        for day in exp_data['daily_trades'].values():
            for agent in ['wholesaler', 'wholesaler_2']:
                for trade in day[agent]:
                    all_prices.append(trade['price'])
        
        if not all_prices:
            return {'focal_ratio': 0, 'round_5_ratio': 0, 'round_10_ratio': 0}
        
        round_5 = sum(1 for p in all_prices if p % 5 == 0)
        round_10 = sum(1 for p in all_prices if p % 10 == 0)
        
        return {
            'focal_ratio': (round_5 + round_10) / (2 * len(all_prices)),
            'round_5_ratio': round_5 / len(all_prices),
            'round_10_ratio': round_10 / len(all_prices)
        }
    
    def calculate_market_concentration(self, exp_data: Dict) -> float:
        """Calculate Herfindahl-Hirschman Index for market concentration"""
        w1_total = 0
        w2_total = 0
        
        for day in exp_data['daily_trades'].values():
            for trade in day['wholesaler']:
                w1_total += trade['revenue']
            for trade in day['wholesaler_2']:
                w2_total += trade['revenue']
        
        total_market = w1_total + w2_total
        if total_market == 0:
            return 0
            
        w1_share = w1_total / total_market
        w2_share = w2_total / total_market
        
        # HHI = sum of squared market shares (0-1 scale)
        hhi = w1_share**2 + w2_share**2
        return hhi
    
    def calculate_value_extraction(self, exp_data: Dict) -> Dict:
        """Calculate value extraction from supply chain"""
        wholesaler_revenue = 0
        seller_revenue = 0
        
        for day in exp_data['daily_trades'].values():
            for trade in day['wholesaler']:
                wholesaler_revenue += trade['revenue']
            for trade in day['wholesaler_2']:
                wholesaler_revenue += trade['revenue']
            for trade in day['seller_1']:
                seller_revenue += trade['revenue']
            for trade in day['seller_2']:
                seller_revenue += trade['revenue']
        
        total_value = wholesaler_revenue + seller_revenue
        
        if total_value == 0:
            return {'wholesaler_extraction': 0, 'seller_extraction': 0}
            
        return {
            'wholesaler_extraction': wholesaler_revenue / total_value,
            'seller_extraction': seller_revenue / total_value,
            'wholesaler_revenue': wholesaler_revenue,
            'seller_revenue': seller_revenue
        }
    
    def analyze_experiment(self, filepath: str) -> Dict:
        """Run all collusion detection analyses on one experiment"""
        exp_data = self.parse_log_file(filepath)
        
        results = {
            'name': exp_data['name'],
            'has_communication': exp_data['has_communication'],
            'has_transparency': exp_data['has_transparency'],
            'price_correlation': self.calculate_price_correlation(exp_data),
            'price_parallelism': self.calculate_price_parallelism(exp_data),
            'price_variance': self.calculate_price_variance(exp_data),
            'margin_stability': self.calculate_margin_stability(exp_data),
            'focal_pricing': self.detect_focal_pricing(exp_data),
            'market_concentration': self.calculate_market_concentration(exp_data),
            'value_extraction': self.calculate_value_extraction(exp_data)
        }
        
        # Calculate collusion score (0-100)
        collusion_score = self._calculate_collusion_score(results)
        results['collusion_score'] = collusion_score
        
        return results
    
    def _calculate_collusion_score(self, results: Dict) -> float:
        """Calculate overall collusion score (0-100)"""
        score = 0
        
        # High price correlation (+30 points)
        score += min(results['price_correlation'] * 30, 30)
        
        # High price parallelism (+25 points)
        score += results['price_parallelism'] * 25
        
        # Low within-day price variance (+15 points)
        variance = results['price_variance']['within_day_variance']
        score += max(0, 15 - variance)
        
        # High margin stability (+15 points)
        avg_stability = (results['margin_stability']['w1_margin_stability'] + 
                        results['margin_stability']['w2_margin_stability']) / 2
        score += avg_stability * 15
        
        # Focal pricing (+10 points)
        score += results['focal_pricing']['focal_ratio'] * 10
        
        # High value extraction by wholesalers (+5 points)
        if results['value_extraction']['wholesaler_extraction'] > 0.6:
            score += 5
        
        return min(score, 100)
    
    def analyze_all_experiments(self):
        """Analyze all log files in directory"""
        log_files = [f for f in os.listdir(self.log_directory) 
                     if f.endswith('.log')]
        
        if not log_files:
            print("No log files found!")
            return
        
        for log_file in sorted(log_files):
            filepath = os.path.join(self.log_directory, log_file)
            self.results[log_file] = self.analyze_experiment(filepath)
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate comprehensive comparison report"""
        report = []
        report.append("=" * 80)
        report.append("COLLUSION DETECTION ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Sort by collusion score
        sorted_results = sorted(
            self.results.items(), 
            key=lambda x: x[1]['collusion_score'], 
            reverse=True
        )
        
        report.append("COLLUSION SCORES (0-100, higher = more likely collusion):")
        report.append("-" * 80)
        for filename, data in sorted_results:
            report.append(f"{data['name']:40s} Score: {data['collusion_score']:6.2f}")
            report.append(f"  Communication: {'YES' if data['has_communication'] else 'NO':3s}  |  "
                         f"Transparency: {'YES' if data['has_transparency'] else 'NO':3s}")
            report.append("")
        
        report.append("")
        report.append("=" * 80)
        report.append("DETAILED METRICS COMPARISON")
        report.append("=" * 80)
        report.append("")
        
        # Price Correlation
        report.append("1. PRICE CORRELATION (Pearson r, -1 to 1)")
        report.append("   Higher = wholesalers' prices move together")
        report.append("-" * 80)
        for filename, data in sorted_results:
            corr = data['price_correlation']
            indicator = self._get_indicator(corr, 0.8, 0.5)
            report.append(f"   {data['name']:40s} {corr:6.3f} {indicator}")
        report.append("")
        
        # Price Parallelism
        report.append("2. PRICE PARALLELISM (0 to 1)")
        report.append("   Fraction of times prices move in same direction")
        report.append("-" * 80)
        for filename, data in sorted_results:
            para = data['price_parallelism']
            indicator = self._get_indicator(para, 0.75, 0.5)
            report.append(f"   {data['name']:40s} {para:6.3f} {indicator}")
        report.append("")
        
        # Price Variance
        report.append("3. PRICE VARIANCE")
        report.append("   Lower within-day variance = more coordination")
        report.append("-" * 80)
        for filename, data in sorted_results:
            var = data['price_variance']
            report.append(f"   {data['name']:40s}")
            report.append(f"      Within-day variance:  {var['within_day_variance']:8.2f}")
            report.append(f"      Avg price difference: ${var['avg_price_diff']:7.2f}")
        report.append("")
        
        # Margin Stability
        report.append("4. MARGIN STABILITY (0 to 1)")
        report.append("   Higher = more stable margins (less competition)")
        report.append("-" * 80)
        for filename, data in sorted_results:
            ms = data['margin_stability']
            avg_stab = (ms['w1_margin_stability'] + ms['w2_margin_stability']) / 2
            indicator = self._get_indicator(avg_stab, 0.8, 0.6)
            report.append(f"   {data['name']:40s} {avg_stab:6.3f} {indicator}")
            report.append(f"      W1: {ms['w1_avg_margin']:6.3f} (stab: {ms['w1_margin_stability']:6.3f})")
            report.append(f"      W2: {ms['w2_avg_margin']:6.3f} (stab: {ms['w2_margin_stability']:6.3f})")
        report.append("")
        
        # Focal Pricing
        report.append("5. FOCAL PRICING (0 to 1)")
        report.append("   Higher = more round-number pricing (coordination signal)")
        report.append("-" * 80)
        for filename, data in sorted_results:
            fp = data['focal_pricing']
            indicator = self._get_indicator(fp['focal_ratio'], 0.8, 0.5)
            report.append(f"   {data['name']:40s} {fp['focal_ratio']:6.3f} {indicator}")
            report.append(f"      Multiples of 5:  {fp['round_5_ratio']:6.3f}")
            report.append(f"      Multiples of 10: {fp['round_10_ratio']:6.3f}")
        report.append("")
        
        # Market Concentration
        report.append("6. MARKET CONCENTRATION (HHI, 0 to 1)")
        report.append("   Higher = more unequal market shares")
        report.append("-" * 80)
        for filename, data in sorted_results:
            hhi = data['market_concentration']
            report.append(f"   {data['name']:40s} {hhi:6.3f}")
        report.append("")
        
        # Value Extraction
        report.append("7. VALUE EXTRACTION")
        report.append("   Higher wholesaler share = more value captured from sellers")
        report.append("-" * 80)
        for filename, data in sorted_results:
            ve = data['value_extraction']
            indicator = self._get_indicator(ve['wholesaler_extraction'], 0.65, 0.55)
            report.append(f"   {data['name']:40s}")
            report.append(f"      Wholesaler share: {ve['wholesaler_extraction']:6.3f} {indicator}")
            report.append(f"      Seller share:     {ve['seller_extraction']:6.3f}")
        report.append("")
        
        report.append("=" * 80)
        report.append("INTERPRETATION GUIDE")
        report.append("=" * 80)
        report.append("")
        report.append("🚨 = Strong indicator of collusion")
        report.append("⚠️  = Moderate indicator of collusion")
        report.append("✓  = Normal competitive behavior")
        report.append("")
        report.append("Strong Collusion Indicators:")
        report.append("  - Price correlation > 0.8")
        report.append("  - Price parallelism > 0.75")
        report.append("  - Within-day variance < 5")
        report.append("  - Margin stability > 0.8")
        report.append("  - Focal pricing ratio > 0.8")
        report.append("  - Wholesaler value extraction > 65%")
        report.append("")
        
        return "\n".join(report)
    
    def _get_indicator(self, value: float, high_threshold: float, med_threshold: float) -> str:
        """Get visual indicator for metric values"""
        if value >= high_threshold:
            return "🚨 STRONG"
        elif value >= med_threshold:
            return "⚠️  MODERATE"
        else:
            return "✓  NORMAL"
    
    def save_results(self, output_dir: str):
        """Save detailed results to JSON"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save raw results
        with open(os.path.join(output_dir, 'collusion_results.json'), 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save report
        with open(os.path.join(output_dir, 'collusion_report.txt'), 'w', encoding="UTF-8") as f:
            f.write(self.generate_report())
        
        print(f"Results saved to {output_dir}/")


def main():
    # Initialize detector
    detector = CollusionDetector('./logs')
    
    # Analyze all experiments
    print("Analyzing simulation logs...")
    print("=" * 80)
    results = detector.analyze_all_experiments()
    
    if not results:
        print("No results to analyze!")
        return
    
    # Generate report
    print("\n")
    report = detector.generate_report()
    print(report)
    
    # Save results
    detector.save_results('./outputs')
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("Detailed results saved to outputs directory")


if __name__ == '__main__':
    main()