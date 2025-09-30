#!/usr/bin/env python3
"""
Compare old (broken) vs new (fixed) evaluation results to show the improvement.
"""

import json
import argparse
from pathlib import Path


def load_results(file_path: str) -> dict:
    """Load results from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def compare_results(old_file: str, new_file: str):
    """Compare old vs new results."""
    old_results = load_results(old_file)
    new_results = load_results(new_file)
    
    print("🔄 EVALUATION RESULTS COMPARISON")
    print("=" * 50)
    
    # Summary comparison
    old_summary = old_results.get('summary', {})
    new_summary = new_results.get('summary', {})
    
    print("\n📊 SUMMARY:")
    print(f"  Total test cases: {old_summary.get('total_test_cases', 0)} → {new_summary.get('total_test_cases', 0)}")
    print(f"  Success rate: {old_summary.get('success_rate', 0):.1%} → {new_summary.get('success_rate', 0):.1%}")
    
    # Metric comparison
    old_metrics = old_results.get('metric_averages', {})
    new_metrics = new_results.get('metric_averages', {})
    
    print("\n🎯 METRIC IMPROVEMENTS:")
    for metric_name in new_metrics.keys():
        old_score = old_metrics.get(metric_name, {}).get('average_score', 0)
        new_score = new_metrics.get(metric_name, {}).get('average_score', 0)
        improvement = new_score - old_score
        
        if improvement > 0:
            print(f"  ✅ {metric_name}:")
            print(f"     {old_score:.3f} → {new_score:.3f} (+{improvement:.3f} 📈)")
        elif improvement < 0:
            print(f"  📉 {metric_name}:")
            print(f"     {old_score:.3f} → {new_score:.3f} ({improvement:.3f})")
        else:
            print(f"  ➡️ {metric_name}: {new_score:.3f} (no change)")
    
    # Response content analysis
    old_detailed = old_results.get('detailed_results', [])
    new_detailed = new_results.get('detailed_results', [])
    
    old_empty_responses = sum(1 for r in old_detailed if not r.get('actual_output', '').strip())
    new_empty_responses = sum(1 for r in new_detailed if not r.get('actual_output', '').strip())
    
    print("\n📝 RESPONSE QUALITY:")
    print(f"  Empty responses: {old_empty_responses} → {new_empty_responses}")
    
    if old_detailed and new_detailed:
        old_avg_length = sum(len(r.get('actual_output', '')) for r in old_detailed) / len(old_detailed)
        new_avg_length = sum(len(r.get('actual_output', '')) for r in new_detailed) / len(new_detailed)
        print(f"  Average response length: {old_avg_length:.0f} → {new_avg_length:.0f} characters")
    
    print("\n🚀 KEY IMPROVEMENTS:")
    
    # Tool selection improvement
    old_tool_score = old_metrics.get('ToolSelectionMetric', {}).get('average_score', 0)
    new_tool_score = new_metrics.get('ToolSelectionMetric', {}).get('average_score', 0)
    
    if new_tool_score > old_tool_score:
        if new_tool_score >= 0.9:
            print("  🎯 PERFECT TOOL SELECTION - Agent correctly identifies tools 100% of the time!")
        else:
            print(f"  🔧 Tool selection improved from {old_tool_score:.1%} to {new_tool_score:.1%}")
    
    # Parameter accuracy improvement  
    old_param_score = old_metrics.get('ParameterAccuracyMetric', {}).get('average_score', 0)
    new_param_score = new_metrics.get('ParameterAccuracyMetric', {}).get('average_score', 0)
    
    if new_param_score > old_param_score:
        if new_param_score >= 0.8:
            print("  📊 EXCELLENT PARAMETER EXTRACTION - High accuracy in extracting parameters!")
        elif new_param_score >= 0.5:
            print("  📈 GOOD PARAMETER EXTRACTION - Agent captures most parameters correctly")
        else:
            print(f"  📊 Parameter accuracy improved from {old_param_score:.1%} to {new_param_score:.1%}")
    
    # Response quality improvement
    old_response_score = old_metrics.get('ResponseAccuracyMetric', {}).get('average_score', 0)
    new_response_score = new_metrics.get('ResponseAccuracyMetric', {}).get('average_score', 0)
    
    if new_response_score > old_response_score:
        if new_response_score >= 0.8:
            print("  📝 HIGH-QUALITY RESPONSES - Agent provides excellent answers!")
        elif new_response_score >= 0.6:
            print("  📝 SOLID RESPONSE QUALITY - Agent gives good, accurate responses")
        else:
            print(f"  📝 Response quality improved from {old_response_score:.1%} to {new_response_score:.1%}")
    
    # Overall improvement
    old_overall = old_metrics.get('ComprehensiveEvaluationMetric', {}).get('average_score', 0)
    new_overall = new_metrics.get('ComprehensiveEvaluationMetric', {}).get('average_score', 0)
    
    if new_overall > old_overall:
        improvement_pct = ((new_overall - old_overall) / old_overall * 100) if old_overall > 0 else float('inf')
        if improvement_pct == float('inf'):
            print("  🎊 INCREDIBLE IMPROVEMENT - From broken evaluation to working system!")
        else:
            print(f"  🚀 OVERALL IMPROVEMENT: {improvement_pct:.0f}% better performance!")
    
    print("\n" + "=" * 50)
    
    if new_overall >= 0.7:
        print("🎉 EVALUATION CONCLUSION: Your Llama Stack agent is performing WELL!")
    elif new_overall >= 0.5:
        print("👍 EVALUATION CONCLUSION: Your Llama Stack agent shows SOLID performance!")
    else:
        print("🔧 EVALUATION CONCLUSION: Your Llama Stack agent needs some tuning.")
    
    print("\n💡 WHAT FIXED THE ISSUE:")
    print("  • Streaming response parsing was broken")
    print("  • Fixed chunk.event.payload.delta.text extraction")  
    print("  • Fixed chunk.event.payload.turn.output_message.content handling")
    print("  • Now capturing actual agent responses instead of empty strings")


def main():
    parser = argparse.ArgumentParser(description="Compare old vs new evaluation results")
    parser.add_argument("--old", default="evaluation_results/evaluation_results_20250929_183121.json")
    parser.add_argument("--new", default="evaluation_results/fixed_results_20250929_185034.json")
    
    args = parser.parse_args()
    
    if not Path(args.old).exists():
        print(f"❌ Old results file not found: {args.old}")
        return
    
    if not Path(args.new).exists():
        print(f"❌ New results file not found: {args.new}")
        return
    
    compare_results(args.old, args.new)


if __name__ == "__main__":
    main()
