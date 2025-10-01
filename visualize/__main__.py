#!/usr/bin/env python3
"""
Main entry point for the visualize package.

This script provides functionality to create visualizations and upload to dashboards
from evaluation results.
"""

import argparse
import sys
from pathlib import Path

from .results import EvaluationVisualizer
from .dashboard import DeepEvalDashboardUploader


def main():
    """Main entry point."""
    # Check if first argument looks like a command or a file
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        if first_arg in ['visualize', 'dashboard']:
            # New subcommand-based usage
            use_subcommands = True
        else:
            # Backward compatibility - first argument is results file
            use_subcommands = False
    else:
        use_subcommands = True
    
    if use_subcommands:
        # Use subcommand-based argument parsing
        parser = argparse.ArgumentParser(
            description="Visualize Llama Stack evaluation results"
        )
        
        # Add subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Visualize command
        viz_parser = subparsers.add_parser('visualize', help='Create local visualizations')
        viz_parser.add_argument("results_file", help="Path to JSON results file")
        viz_parser.add_argument("--type", "-t", choices=['summary', 'detailed', 'table', 'all'], 
                               default='all', help="Type of visualization to create")
        viz_parser.add_argument("--open", "-o", action="store_true", help="Open result in browser")
        
        # Dashboard command  
        dash_parser = subparsers.add_parser('dashboard', help='Upload to DeepEval cloud dashboard')
        dash_parser.add_argument("results_file", help="Path to JSON results file")
        dash_parser.add_argument("--login", action="store_true", help="Login to Confident AI first")
        dash_parser.add_argument("--name", help="Dataset name for the dashboard")
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
            
    else:
        # Backward compatibility mode - direct file argument
        parser = argparse.ArgumentParser(
            description="Visualize Llama Stack evaluation results"
        )
        parser.add_argument("results_file", help="Path to JSON results file")
        parser.add_argument("--type", "-t", choices=['summary', 'detailed', 'table', 'all'], 
                           default='all', help="Type of visualization to create")
        parser.add_argument("--open", "-o", action="store_true", help="Open result in browser")
        
        args = parser.parse_args()
        args.command = 'visualize'  # Default to visualize command
    
    # Validate results file exists
    if not Path(args.results_file).exists():
        print(f"❌ Results file not found: {args.results_file}")
        sys.exit(1)
    
    # Execute command
    if args.command == 'visualize':
        handle_visualize_command(args)
    elif args.command == 'dashboard':
        handle_dashboard_command(args)


def handle_visualize_command(args):
    """Handle the visualize command."""
    # Create visualizer
    visualizer = EvaluationVisualizer(args.results_file)
    
    # Generate visualizations
    if args.type == 'all':
        files = visualizer.generate_all_visualizations()
        main_file = files[-1]  # Comprehensive dashboard
    elif args.type == 'summary':
        main_file = visualizer.create_summary_charts()
    elif args.type == 'detailed':
        main_file = visualizer.create_detailed_analysis()
    elif args.type == 'table':
        main_file = visualizer.create_data_table()
    
    print(f"📁 Output directory: {visualizer.output_dir}")
    print(f"🌐 Main file: {main_file}")
    
    if args.open:
        import webbrowser
        webbrowser.open(f"file://{Path(main_file).absolute()}")
        print("🚀 Opening in browser...")


def handle_dashboard_command(args):
    """Handle the dashboard command."""
    uploader = DeepEvalDashboardUploader(args.results_file)
    
    # Check/handle login
    if args.login or not uploader.check_login_status():
        if not uploader.login_to_confident_ai():
            print("❌ Cannot proceed without login")
            sys.exit(1)
    
    # Run dashboard evaluation
    uploader.run_dashboard_evaluation()


if __name__ == "__main__":
    main()
