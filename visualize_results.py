#!/usr/bin/env python3
"""
Visualization script for Llama Stack evaluation results.
Creates interactive charts, graphs, and HTML dashboards from JSON results.
"""

import json
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class EvaluationVisualizer:
    """Class for creating visualizations from evaluation results."""
    
    def __init__(self, results_file: str):
        """
        Initialize with results file.
        
        Args:
            results_file: Path to JSON results file
        """
        self.results_file = results_file
        self.data = self._load_results()
        self.output_dir = Path("evaluation_results/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_results(self) -> Dict[str, Any]:
        """Load results from JSON file."""
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load results file: {e}")
    
    def create_summary_charts(self, save_html: bool = True) -> str:
        """
        Create summary charts showing overall performance.
        
        Args:
            save_html: Whether to save as HTML file
            
        Returns:
            Path to saved HTML file
        """
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Overall Success Rate', 
                'Metric Performance', 
                'Category Breakdown',
                'Score Distribution'
            ),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "histogram"}]]
        )
        
        # 1. Overall Success Rate (Pie Chart)
        summary = self.data.get('summary', {})
        success_data = [
            summary.get('successful_evaluations', 0),
            summary.get('failed_evaluations', 0)
        ]
        
        fig.add_trace(
            go.Pie(
                labels=['Successful', 'Failed'],
                values=success_data,
                hole=0.4,
                marker_colors=['#2E8B57', '#DC143C']
            ),
            row=1, col=1
        )
        
        # 2. Metric Performance (Bar Chart)
        metric_data = self.data.get('metric_averages', {})
        metric_names = list(metric_data.keys())
        metric_scores = [metric_data[m].get('average_score', 0) for m in metric_names]
        
        fig.add_trace(
            go.Bar(
                x=metric_names,
                y=metric_scores,
                marker_color='#4682B4',
                name='Average Score'
            ),
            row=1, col=2
        )
        
        # 3. Category Breakdown (Bar Chart)
        category_data = self.data.get('category_results', {})
        categories = list(category_data.keys())
        category_success_rates = []
        
        for category in categories:
            results = category_data[category]
            successful = sum(1 for r in results if 'error' not in r)
            total = len(results)
            success_rate = successful / total if total > 0 else 0
            category_success_rates.append(success_rate * 100)
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=category_success_rates,
                marker_color='#32CD32',
                name='Success Rate %'
            ),
            row=2, col=1
        )
        
        # 4. Score Distribution (Histogram)
        all_scores = []
        detailed_results = self.data.get('detailed_results', [])
        
        for result in detailed_results:
            if 'metric_results' in result:
                for metric_name, metric_result in result['metric_results'].items():
                    all_scores.append(metric_result.get('score', 0))
        
        if all_scores:
            fig.add_trace(
                go.Histogram(
                    x=all_scores,
                    nbinsx=20,
                    marker_color='#FFD700',
                    name='Score Distribution'
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            height=800,
            showlegend=True,
            title_text="Llama Stack Evaluation Results Dashboard",
            title_x=0.5
        )
        
        # Update axes
        fig.update_yaxes(title_text="Success Rate %", row=2, col=1)
        fig.update_xaxes(title_text="Categories", row=2, col=1, tickangle=45)
        fig.update_yaxes(title_text="Score", row=1, col=2)
        fig.update_xaxes(title_text="Metrics", row=1, col=2, tickangle=45)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)
        fig.update_xaxes(title_text="Score", row=2, col=2)
        
        if save_html:
            output_file = self.output_dir / "summary_dashboard.html"
            pyo.plot(fig, filename=str(output_file), auto_open=False)
            return str(output_file)
        else:
            fig.show()
            return ""
    
    def create_detailed_analysis(self) -> str:
        """Create detailed analysis charts."""
        
        # Prepare data for detailed analysis
        detailed_results = self.data.get('detailed_results', [])
        
        # Create DataFrame
        rows = []
        for result in detailed_results:
            if 'metric_results' in result:
                base_row = {
                    'test_case_index': result.get('test_case_index', 0),
                    'category': result.get('original_test_case', {}).get('category', 'Unknown')
                }
                
                for metric_name, metric_result in result['metric_results'].items():
                    row = base_row.copy()
                    row.update({
                        'metric': metric_name,
                        'score': metric_result.get('score', 0),
                        'success': metric_result.get('success', False)
                    })
                    rows.append(row)
        
        if not rows:
            return "No detailed data available for visualization"
        
        df = pd.DataFrame(rows)
        
        # Create detailed visualizations
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Metric Scores by Category',
                'Success Rate by Metric', 
                'Test Case Performance Heatmap',
                'Category vs Metric Performance'
            ),
            specs=[[{"type": "box"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "heatmap"}]]
        )
        
        # 1. Box plot of scores by category
        for category in df['category'].unique():
            category_data = df[df['category'] == category]
            fig.add_trace(
                go.Box(
                    y=category_data['score'],
                    name=category,
                    boxpoints='outliers'
                ),
                row=1, col=1
            )
        
        # 2. Success rate by metric
        metric_success = df.groupby('metric')['success'].mean() * 100
        fig.add_trace(
            go.Bar(
                x=metric_success.index,
                y=metric_success.values,
                marker_color='#FF6347'
            ),
            row=1, col=2
        )
        
        # 3. Test case performance scatter
        test_case_avg = df.groupby('test_case_index')['score'].mean()
        fig.add_trace(
            go.Scatter(
                x=test_case_avg.index,
                y=test_case_avg.values,
                mode='markers+lines',
                marker=dict(
                    size=8,
                    color=test_case_avg.values,
                    colorscale='Viridis'
                ),
                name='Average Score'
            ),
            row=2, col=1
        )
        
        # 4. Heatmap of category vs metric performance
        pivot_data = df.pivot_table(
            values='score', 
            index='category', 
            columns='metric', 
            aggfunc='mean'
        )
        
        fig.add_trace(
            go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='RdYlGn',
                text=pivot_data.round(3).values,
                texttemplate="%{text}",
                textfont={"size": 10}
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=900,
            showlegend=True,
            title_text="Detailed Evaluation Analysis",
            title_x=0.5
        )
        
        # Update axes
        fig.update_yaxes(title_text="Score", row=1, col=1)
        fig.update_yaxes(title_text="Success Rate %", row=1, col=2)
        fig.update_xaxes(title_text="Metrics", row=1, col=2, tickangle=45)
        fig.update_yaxes(title_text="Average Score", row=2, col=1)
        fig.update_xaxes(title_text="Test Case Index", row=2, col=1)
        
        # Save file
        output_file = self.output_dir / "detailed_analysis.html"
        pyo.plot(fig, filename=str(output_file), auto_open=False)
        return str(output_file)
    
    def create_data_table(self) -> str:
        """Create an interactive data table."""
        detailed_results = self.data.get('detailed_results', [])
        
        # Prepare table data
        table_data = []
        for result in detailed_results:
            if 'metric_results' in result:
                row = {
                    'Test Case': result.get('test_case_index', 0) + 1,
                    'Category': result.get('original_test_case', {}).get('category', 'Unknown'),
                    'Input': result.get('input', '')[:100] + '...' if len(result.get('input', '')) > 100 else result.get('input', ''),
                    'Expected Tool': result.get('original_test_case', {}).get('tool_name', 'Unknown')
                }
                
                # Add metric scores
                for metric_name, metric_result in result['metric_results'].items():
                    metric_short = metric_name.replace('Metric', '').replace('Evaluation', '')
                    row[f'{metric_short} Score'] = f"{metric_result.get('score', 0):.3f}"
                    row[f'{metric_short} Success'] = "✅" if metric_result.get('success', False) else "❌"
                
                table_data.append(row)
        
        if not table_data:
            return "No data available for table"
        
        df = pd.DataFrame(table_data)
        
        # Create interactive table
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='paleturquoise',
                align='left',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color='lavender',
                align='left',
                font=dict(size=11, color='black'),
                height=30
            )
        )])
        
        fig.update_layout(
            title="Detailed Evaluation Results Table",
            height=600
        )
        
        # Save file
        output_file = self.output_dir / "results_table.html"
        pyo.plot(fig, filename=str(output_file), auto_open=False)
        return str(output_file)
    
    def create_comprehensive_dashboard(self) -> str:
        """Create a comprehensive HTML dashboard."""
        
        # Generate individual visualizations
        summary_file = self.create_summary_charts(save_html=False)
        detailed_file = self.create_detailed_analysis()
        table_file = self.create_data_table()
        
        # Create comprehensive dashboard HTML
        dashboard_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Llama Stack Evaluation Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            text-align: center;
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
        }}
        .card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .section {{
            background: white;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .section-header {{
            background: #34495e;
            color: white;
            padding: 15px 20px;
            margin: 0;
        }}
        .section-content {{
            padding: 20px;
        }}
        iframe {{
            width: 100%;
            height: 600px;
            border: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Llama Stack Agent Evaluation Dashboard</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary-cards">
        <div class="card">
            <h3>Total Test Cases</h3>
            <div class="value">{self.data.get('summary', {}).get('total_test_cases', 0)}</div>
        </div>
        <div class="card">
            <h3>Success Rate</h3>
            <div class="value">{self.data.get('summary', {}).get('success_rate', 0):.1%}</div>
        </div>
        <div class="card">
            <h3>Categories</h3>
            <div class="value">{len(self.data.get('category_results', {}))}</div>
        </div>
        <div class="card">
            <h3>Metrics</h3>
            <div class="value">{len(self.data.get('metric_averages', {}))}</div>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-header">📊 Summary Charts</h2>
        <div class="section-content">
            <iframe src="summary_dashboard.html"></iframe>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-header">🔍 Detailed Analysis</h2>
        <div class="section-content">
            <iframe src="detailed_analysis.html"></iframe>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-header">📋 Results Table</h2>
        <div class="section-content">
            <iframe src="results_table.html"></iframe>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-header">📈 Key Insights</h2>
        <div class="section-content">
            {self._generate_insights()}
        </div>
    </div>
</body>
</html>
        """
        
        # Save dashboard
        dashboard_file = self.output_dir / "comprehensive_dashboard.html"
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)
        
        return str(dashboard_file)
    
    def _generate_insights(self) -> str:
        """Generate textual insights from the data."""
        insights = []
        
        summary = self.data.get('summary', {})
        metrics = self.data.get('metric_averages', {})
        categories = self.data.get('category_results', {})
        
        # Overall performance
        success_rate = summary.get('success_rate', 0) * 100
        insights.append(f"• Overall success rate: {success_rate:.1f}%")
        
        # Best and worst performing metrics
        if metrics:
            metric_scores = {k: v.get('average_score', 0) for k, v in metrics.items()}
            best_metric = max(metric_scores, key=metric_scores.get)
            worst_metric = min(metric_scores, key=metric_scores.get)
            insights.append(f"• Best performing metric: {best_metric} ({metric_scores[best_metric]:.3f})")
            insights.append(f"• Needs improvement: {worst_metric} ({metric_scores[worst_metric]:.3f})")
        
        # Category performance
        if categories:
            category_rates = {}
            for category, results in categories.items():
                successful = sum(1 for r in results if 'error' not in r)
                total = len(results)
                category_rates[category] = successful / total if total > 0 else 0
            
            best_category = max(category_rates, key=category_rates.get)
            insights.append(f"• Best category: {best_category} ({category_rates[best_category]:.1%})")
        
        return "<br>".join(insights)
    
    def generate_all_visualizations(self) -> List[str]:
        """Generate all visualization types and return file paths."""
        files = []
        
        print("🎨 Generating visualizations...")
        
        # Summary dashboard
        print("  📊 Creating summary charts...")
        summary_file = self.create_summary_charts()
        files.append(summary_file)
        
        # Detailed analysis
        print("  🔍 Creating detailed analysis...")
        detailed_file = self.create_detailed_analysis()
        files.append(detailed_file)
        
        # Data table
        print("  📋 Creating results table...")
        table_file = self.create_data_table()
        files.append(table_file)
        
        # Comprehensive dashboard
        print("  🚀 Creating comprehensive dashboard...")
        dashboard_file = self.create_comprehensive_dashboard()
        files.append(dashboard_file)
        
        print("✅ All visualizations created!")
        return files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Visualize Llama Stack evaluation results")
    parser.add_argument("results_file", help="Path to JSON results file")
    parser.add_argument("--type", "-t", choices=['summary', 'detailed', 'table', 'all'], 
                       default='all', help="Type of visualization to create")
    parser.add_argument("--open", "-o", action="store_true", help="Open result in browser")
    
    args = parser.parse_args()
    
    # Check if results file exists
    if not Path(args.results_file).exists():
        print(f"❌ Results file not found: {args.results_file}")
        return
    
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


if __name__ == "__main__":
    main()
