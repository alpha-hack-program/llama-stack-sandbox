#!/bin/bash
# Quick script to open evaluation dashboards

echo "🚀 Opening Llama Stack Evaluation Dashboards..."

# Get the absolute path
DASHBOARD_DIR="/var/home/cvicensa/Projects/alpha-hack-program/llama-stack-sandbox/evaluation_results/visualizations"

echo "📊 Available dashboards:"
echo "  1. Comprehensive Dashboard (main)"
echo "  2. Summary Charts"
echo "  3. Detailed Analysis"
echo "  4. Results Table"

echo ""
# Check if visualizations exist and are up-to-date, if not, generate them
LATEST_RESULTS=$(ls -t evaluation_results/evaluation_results_*.json 2>/dev/null | head -1)
if [ ! -f "$DASHBOARD_DIR/comprehensive_dashboard.html" ] || ([ -n "$LATEST_RESULTS" ] && [ "$LATEST_RESULTS" -nt "$DASHBOARD_DIR/comprehensive_dashboard.html" ]); then
    if [ ! -f "$DASHBOARD_DIR/comprehensive_dashboard.html" ]; then
        echo "📊 Visualizations not found. Generating them..."
    else
        echo "📊 Results file is newer than visualizations. Regenerating..."
    fi
    if [ -n "$LATEST_RESULTS" ]; then
        echo "🔄 Using results file: $LATEST_RESULTS"
        uv run -m visualize "$LATEST_RESULTS" --type all
    else
        echo "❌ No results files found. Please run an evaluation first."
        exit 1
    fi
fi

echo "🌐 Opening comprehensive dashboard..."
xdg-open "file://$DASHBOARD_DIR/comprehensive_dashboard.html" 2>/dev/null || \
firefox "file://$DASHBOARD_DIR/comprehensive_dashboard.html" 2>/dev/null || \
chromium-browser "file://$DASHBOARD_DIR/comprehensive_dashboard.html" 2>/dev/null || \
echo "❌ Could not open browser. Please manually open: $DASHBOARD_DIR/comprehensive_dashboard.html"

echo ""
echo "📁 All files located at: $DASHBOARD_DIR"
echo "✅ Dashboard opened!"
