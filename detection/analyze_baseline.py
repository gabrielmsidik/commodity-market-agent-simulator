#!/usr/bin/env python3
"""
Analyze only the 4 baseline experiments (A, B, C, D)
Provides clean 2x2 comparison without noise from test runs
"""
from collusion_detection import CollusionDetector
import os

def main():
    print("=" * 80)
    print("BASELINE EXPERIMENTS ANALYSIS")
    print("2x2 Factorial Design: Communication x Transparency")
    print("=" * 80)
    print()

    detector = CollusionDetector('../logs')

    # Specify the 4 baseline experiments explicitly
    # Format: Display Name -> Log filename
    baseline_files = {
        'Experiment A (No Comm, No Trans)': 'simulation_20251101_164504.log',
        'Experiment B (No Comm, With Trans)': 'simulation_20251101_164510.log',
        'Experiment C (With Comm, No Trans)': 'simulation_20251101_164516.log',
        'Experiment D (With Comm, With Trans)': 'simulation_20251101_170449.log',
    }

    # Analyze only these 4
    print("Parsing baseline experiments...")
    results = {}
    for label, filename in baseline_files.items():
        filepath = f'../logs/{filename}'
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} not found!")
            continue
        print(f"  - {label}")
        results[label] = detector.analyze_experiment(filepath)

    print()
    print(f"Analyzed {len(results)} experiments")
    print()

    # Replace detector's results with just our 4 baselines
    detector.results = results

    # Generate focused report
    report = detector.generate_report()
    print(report)

    # Save to dedicated baseline outputs folder
    output_dir = './outputs/baseline_analysis'
    detector.save_results(output_dir)

    print()
    print("=" * 80)
    print(f"Baseline analysis complete!")
    print(f"Results saved to: {output_dir}/")
    print("=" * 80)

    # Print quick summary table
    print()
    print("QUICK SUMMARY TABLE:")
    print("-" * 80)
    print(f"{'Experiment':<40} {'Communication':<15} {'Transparency':<15} {'Score':>8}")
    print("-" * 80)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['collusion_score'], reverse=True)
    for label, data in sorted_results:
        comm = "✓" if data['has_communication'] else "✗"
        trans = "✓" if data['has_transparency'] else "✗"
        score = data['collusion_score']
        print(f"{label:<40} {comm:<15} {trans:<15} {score:>8.2f}")

    print("-" * 80)
    print()

    # Print change-point analysis
    print()
    print("=" * 80)
    print("TEMPORAL DYNAMICS - CHANGE POINT ANALYSIS")
    print("=" * 80)
    print()
    print("Detecting when collusion patterns emerge or break down over 21 days:")
    print()

    for label, data in sorted_results:
        cp_data = data['change_points']
        num_changes = cp_data['num_change_points']

        print(f"{label}")
        print(f"  Change Points Detected: {num_changes}")

        if num_changes == 0:
            print(f"  → STABLE: No significant behavioral shifts detected")
            print(f"     Market behavior remained consistent throughout simulation")
        else:
            print(f"  → DYNAMIC: Detected {num_changes} significant shift(s):")
            for i, cp in enumerate(cp_data['change_points'][:3], 1):  # Show first 3
                day = cp['day']
                cp_type = cp['type']
                if cp_type == 'price_shift':
                    print(f"     Day {day}: Price difference changed by ${cp['diff_change']:.1f}")
                    print(f"              New avg price diff: ${cp['new_price_diff']:.1f}")
                else:
                    print(f"     Day {day}: Correlation shifted by {cp['corr_change']:.2f}")
                    print(f"              New correlation: {cp['new_correlation']:.2f}")

            if len(cp_data['change_points']) > 3:
                print(f"     ... and {len(cp_data['change_points']) - 3} more")

            # Show phases
            print(f"  Identified Phases:")
            for phase in cp_data['phases']:
                phase_name = phase['phase']
                print(f"     {phase_name.title()}: Days {phase['start_day']}-{phase['end_day']}")

        print()

    print("=" * 80)
    print()

if __name__ == '__main__':
    main()
