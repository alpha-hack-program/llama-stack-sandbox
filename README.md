# Llama Stack Sandbox - LLM Agent Evaluation Framework

A comprehensive evaluation framework for testing Large Language Model (LLM) agents running on the official Llama Stack Distribution. This repository provides tools for connecting to multiple LLMs and MCP (Model Context Protocol) servers, running structured evaluations using CSV test datasets, and generating detailed performance visualizations.

## 🎯 Purpose

This sandbox environment enables:

- **Local Llama Stack Distribution**: Run official Llama Stack containers locally with multiple LLM providers
- **MCP Server Integration**: Connect to Model Context Protocol servers for enhanced tool capabilities  
- **Structured Testing**: Define and execute test cases using CSV files with expected outcomes
- **Multi-Metric Evaluation**: Assess agent performance across QA accuracy, tool selection, parameter handling, and response quality
- **Interactive Visualization**: Generate comprehensive dashboards and charts for evaluation results analysis
- **Modular Architecture**: Clean separation between container management, evaluation, and visualization components

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Models    │    │ Llama Stack     │    │ MCP Servers     │
│                 │    │ Distribution    │    │                 │
│ • Llama 3.1 8B  │◄───┤                 ├───►│ • Compatibility │
│ • Granite 3.3   │    │ • Agents API    │    │ • Eligibility   │
│ • Scout 17B     │    │ • Tool Runtime  │    │ • Custom Tools  │
└─────────────────┘    │ • Vector Store  │    └─────────────────┘
                       │ • Safety        │
                       └─────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Evaluation Engine  │
                    │                     │
                    │ • DeepEval Framework│
                    │ • Custom Metrics    │
                    │ • CSV Test Runner   │
                    │ • Result Analyzer   │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Visualization     │
                    │                     │
                    │ • Interactive Plots │
                    │ • HTML Dashboards   │
                    │ • Performance Charts│
                    │ • Comparison Reports│
                    └─────────────────────┘
```

## 📦 Installation & Setup

### Prerequisites

- **Python 3.10-3.11** (required for dependencies compatibility)
- **UV** (recommended) or **pip** for dependency management
- **Podman** or **Docker** (for running Llama Stack Distribution)
- **curl** and **jq** (for API testing)

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd llama-stack-sandbox

# Install using uv (recommended)
uv sync

# OR install using pip
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file with your model and MCP server configurations:

```bash
# Model configurations (add as many as needed)
MODEL_1_URL=https://your-llama-model-endpoint.com/v1
MODEL_1_API_TOKEN=your_api_token_here
MODEL_1_MODEL=llama-3-1-8b-w4a16
MODEL_1_MAX_TOKENS=4096
MODEL_1_TLS_VERIFY=false

MODEL_2_URL=https://your-granite-model-endpoint.com/v1
MODEL_2_API_TOKEN=another_api_token
MODEL_2_MODEL=granite-3-3-8b
MODEL_2_MAX_TOKENS=4096
MODEL_2_TLS_VERIFY=false

# MCP Server configurations
MCP_SERVER_1_ID=mcp::compatibility
MCP_SERVER_1_URI=http://localhost:8002/sse

MCP_SERVER_2_ID=mcp::eligibility  
MCP_SERVER_2_URI=http://localhost:8001/sse

# Base directory for Llama Stack
LSD_BASE_DIR=/opt/app-root/src
```

### 3. Start Llama Stack Distribution

```bash
# Generate configuration and start the stack
./run.sh
```

This script will:
- Auto-discover models and MCP servers from `.env`
- Generate dynamic `run.yaml` configuration
- Start the Llama Stack Distribution container
- Test connectivity to all configured models

## 📊 CSV Test Datasets

### Test File Format

Create test cases in CSV format with the following structure:

```csv
question,expected_answer,tool_name,tool_parameters,evaluation_criteria,category
"Calculate penalty for 15 days late delivery","1050 total penalty. Base: 1500, capped at 1000. Interest: 50.",calc_penalty,"{""days_late"": 15}","Correct tool, accurate calculation, mentions cap",Penalty Calculations
"Check tax for 40000 income","7140 total tax. Bracket 1: 1000. Bracket 2: 6000. Surcharge: 140.",calc_tax,"{""income"": 40000}","Progressive calculation, surcharge applied",Tax Calculations
```

### Available Test Categories

The framework includes pre-built test cases for:

- **Penalty Calculations**: Late payment and delivery penalties with caps and interest
- **Tax Calculations**: Progressive tax brackets with surcharges
- **Voting Validations**: Meeting quorum and threshold validations  
- **Waterfall Distributions**: Financial distribution calculations
- **Housing Grant Eligibility**: Multi-criteria eligibility assessments

### Sample Test Files

- `scratch/compatibility-full.csv` - Complete test suite (21 test cases)
- `scratch/compatibility.csv` - Subset for quick testing

## 🧪 Running Evaluations

### Quick Start

```bash
# Run evaluation with default settings
./evaluate.sh

# Run with specific parameters
./evaluate.sh run -c scratch/compatibility-full.csv -m llama-3-1-8b-w4a16 -v
```

### Using Python Modules Directly

```bash
# Using uv (recommended)
uv run -m evaluate scratch/compatibility-full.csv \
    --model "llama-3-1-8b-w4a16" \
    --stack-url "http://localhost:8080" \
    --tools "mcp::compatibility" \
    --output "results/my_evaluation.json" \
    --verbose

# Using pip-installed packages
python -m evaluate scratch/compatibility-full.csv \
    --model "llama-3-1-8b-w4a16" \
    --stack-url "http://localhost:8080" \
    --tools "mcp::compatibility" \
    --output "results/my_evaluation.json" \
    --verbose
```

### Evaluation Script Options

- `-c, --csv FILE`: Test case CSV file path
- `-m, --model MODEL`: LLM model identifier  
- `-t, --tools TOOLS`: Space-separated tool groups
- `-u, --url URL`: Llama Stack server URL
- `-o, --output FILE`: Results output file
- `-v, --verbose`: Enable detailed logging

## 📈 Evaluation Metrics

The framework uses custom DeepEval metrics to assess agent performance:

### Core Metrics

1. **Tool Selection Accuracy**: Did the agent select the correct tool?
2. **Parameter Accuracy**: Were the tool parameters extracted correctly?  
3. **Response Accuracy**: Does the response match expected outcomes?
4. **Comprehensive Evaluation**: Combined semantic and structural analysis

### Metric Configuration

```python
# Custom metrics with thresholds
from evaluate.metrics import (
    ToolSelectionMetric,
    ParameterAccuracyMetric, 
    ResponseAccuracyMetric,
    ComprehensiveEvaluationMetric
)

metrics = [
    ToolSelectionMetric(agent_wrapper, threshold=1.0),
    ParameterAccuracyMetric(agent_wrapper, threshold=0.95),
    ResponseAccuracyMetric(agent_wrapper, threshold=0.8),
    ComprehensiveEvaluationMetric(agent_wrapper, threshold=0.85)
]
```

### Results Structure

Evaluation results include:
- **Overall Statistics**: Pass rates, average scores, timing metrics
- **Per-Test Details**: Individual scores, tool calls, response analysis
- **Category Analysis**: Performance breakdown by test type
- **Error Analysis**: Common failure patterns and issues

## 📊 Visualization & Reporting

### Generate Visualizations

```bash
# Create comprehensive dashboard (using uv)
uv run -m visualize evaluation_results/evaluation_results_TIMESTAMP.json

# Create specific chart types
uv run -m visualize visualize results.json --type summary

# Upload to DeepEval cloud dashboard
uv run -m visualize dashboard results.json --login

# Open dashboards automatically
./visualize.sh
```

### Available Visualizations

1. **Performance Overview**: Success rates, score distributions
2. **Category Analysis**: Performance by test category  
3. **Timeline Charts**: Response times and processing metrics
4. **Comparison Plots**: Multi-model performance comparison
5. **Interactive Dashboards**: HTML reports with drill-down capabilities

### Dashboard Features

- **Interactive Plots**: Plotly-based charts with zoom, filter, and export
- **Performance Tables**: Sortable results with detailed breakdowns
- **Error Analysis**: Failure pattern identification and categorization
- **Export Options**: PNG, SVG, PDF, and raw data downloads

## 🗂️ Project Structure

```
llama-stack-sandbox/
├── 📦 Core Framework
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Modern Python config
├── .env                         # Environment variables (create this)
│
├── 🐳 Infrastructure (Container & Stack Management)
├── run.sh                       # Llama Stack Distribution launcher  
├── playground.sh                # Interactive testing environment
├── run/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: uv run -m run
│   ├── config.py                # Configuration parsing
│   └── yaml_generator.py        # Dynamic run.yaml generation
├── templates/
│   └── run.yaml.template        # Jinja2 template
├── run.yaml                     # Generated config (auto-created)
│
├── 🧪 Evaluation Framework
├── evaluate.sh                  # Evaluation runner script
├── evaluate/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: uv run -m evaluate
│   ├── evaluator.py             # Main evaluation orchestrator
│   ├── metrics.py               # Custom DeepEval metrics (1000+ lines)
│   ├── wrapper.py               # Agent wrapper and session management
│   ├── config.py                # Evaluation configuration
│   ├── loader.py                # CSV test case loading utilities
│   └── examples.py              # Example usage and demonstrations
│
├── 📊 Visualization & Reporting
├── visualize.sh                 # Quick dashboard opener
├── visualize/
│   ├── __init__.py
│   ├── __main__.py              # Entry point: uv run -m visualize
│   ├── results.py               # Chart and dashboard generator
│   └── dashboard.py             # DeepEval cloud dashboard integration
│
├── 🗂️ Data & Configuration
├── scratch/
│   ├── compatibility-full.csv   # Complete test suite (21 cases)
│   ├── compatibility.csv        # Quick test subset
│   └── compatibility-errors.csv # Error scenarios
├── configs/
│   └── sample_evaluation_config.yaml
├── docs/                        # Knowledge base documents
│   ├── LyFin-Compliance-Annex.md
│   └── ...
│
├── 📈 Results & Outputs (auto-created)
└── evaluation_results/          # JSON results with timestamps
    ├── evaluation_results_YYYYMMDD_HHMMSS.json
    ├── logs/                    # Detailed execution logs
    ├── reports/                 # Generated analysis reports  
    └── visualizations/          # HTML dashboards and charts
        ├── comprehensive_dashboard.html
        ├── detailed_analysis.html
        └── summary_dashboard.html
```

## 🔧 Configuration Files

### Llama Stack Configuration (`run.yaml`)

The `run.yaml` file defines:
- **Model Providers**: Remote VLLM endpoints, embedding models
- **Tool Runtime**: MCP server connections, search providers
- **Storage**: Vector databases, agent persistence, telemetry
- **APIs**: Enabled Llama Stack APIs (agents, inference, eval, etc.)

Generated dynamically from `.env` using:
```bash
uv run -m run
```

### Evaluation Configuration

Configure evaluation behavior in `configs/sample_evaluation_config.yaml`:
```yaml
model_config:
  default_model: "llama-3-1-8b-w4a16"
  tool_groups: ["mcp::compatibility"]
  
evaluation_settings:
  metrics: ["tool_selection", "parameter_accuracy", "response_accuracy"]
  thresholds:
    tool_selection: 1.0
    parameter_accuracy: 0.95
    response_accuracy: 0.8
    
output_settings:
  save_intermediate: true
  generate_visualizations: true
  create_html_dashboard: true
```

## 🚀 Quick Start Guide

1. **Setup Environment**:
   ```bash
   # Install dependencies with uv (recommended)
   uv sync
   
   # Configure your models and MCP servers in .env
   cp .env.example .env
   # Edit .env with your configurations
   ```

2. **Start Llama Stack**:
   ```bash
   ./run.sh
   ```

3. **Run Quick Test**:
   ```bash
   ./evaluate.sh test
   ```

4. **Execute Full Evaluation**:
   ```bash
   ./evaluate.sh run -c scratch/compatibility-full.csv -v
   ```

5. **View Results**:
   ```bash
   # Generate and open dashboard
   ./visualize.sh
   ```

## 🔍 Advanced Usage

### Multi-Model Comparison

```bash
# Run evaluations with different models
./evaluate.sh run -m llama-3-1-8b-w4a16 -o results_llama.json
./evaluate.sh run -m granite-3-3-8b -o results_granite.json

# Compare results using the visualization module
uv run -m visualize visualize results_llama.json --type detailed
uv run -m visualize visualize results_granite.json --type detailed
```

### Custom Test Creation

1. **Create CSV File**:
   ```csv
   question,expected_answer,tool_name,tool_parameters,evaluation_criteria,category
   "Your test question","Expected response","tool_name","{\"param\":\"value\"}","Criteria for success","Custom Category"
   ```

2. **Run Evaluation**:
   ```bash
   ./evaluate.sh run -c your_tests.csv
   ```

3. **Analyze Results**:
   ```bash
   uv run -m visualize your_results.json
   ```

### Direct Python Usage

```python
# Import the evaluation framework
from evaluate.evaluator import LlamaStackEvaluator
from evaluate.metrics import ToolSelectionMetric
from evaluate.loader import CSVTestCaseLoader

# Initialize evaluator
evaluator = LlamaStackEvaluator(
    stack_url="http://localhost:8080",
    model_id="llama-3-1-8b-w4a16",
    tool_groups=["mcp::compatibility"]
)

# Run evaluation
results = await evaluator.run_evaluation(
    csv_file_path="scratch/compatibility-full.csv",
    output_file="my_results.json",
    verbose=True
)
```

### Integration with CI/CD

```bash
# Automated evaluation pipeline
./evaluate.sh validate -c tests/regression_tests.csv
./evaluate.sh run -c tests/regression_tests.csv --output results/ci_results.json
uv run -m visualize visualize results/ci_results.json --type summary
```

## 🐛 Troubleshooting

### Common Issues

1. **Llama Stack Connection Failed**:
   ```bash
   # Check if container is running
   podman ps | grep llama-stack
   
   # Check logs
   podman logs llama-stack
   
   # Test connectivity
   ./evaluate.sh test
   ```

2. **Model Authentication Errors**:
   - Verify API tokens in `.env` file
   - Check model endpoint URLs are accessible
   - Ensure TLS settings match your endpoints

3. **MCP Server Connection Issues**:
   - Confirm MCP servers are running on specified ports
   - Check firewall settings for localhost connections
   - Verify MCP server URIs in `.env`

4. **Python Module Import Errors**:
   ```bash
   # Ensure proper installation
   uv sync
   
   # Check if modules are accessible
   uv run python -c "from evaluate import evaluator; print('OK')"
   ```

5. **Evaluation Failures**:
   ```bash
   # Run with verbose logging
   ./evaluate.sh run -v
   
   # Check specific module
   uv run -m evaluate --help
   
   # Validate test CSV format
   ./evaluate.sh validate -c your_test_file.csv
   ```

## 🆕 What's New in This Version

### Modular Architecture
- **Separated Concerns**: Infrastructure (`run/`), Evaluation (`evaluate/`), Visualization (`visualize/`)
- **Python Packages**: Each component is now a proper Python package with `__main__.py` entry points
- **UV Integration**: Full support for modern Python dependency management with UV

### Improved Commands
- **Simplified Entry Points**: `uv run -m evaluate`, `uv run -m visualize`, `uv run -m run`
- **Enhanced Shell Scripts**: Updated `evaluate.sh`, `visualize.sh`, `run.sh` with better error handling
- **Backward Compatibility**: Old usage patterns still supported during transition

### Better Organization
- **Clear Directory Structure**: Related files grouped logically
- **Legacy Preservation**: Old files moved to `old/` directory for reference
- **Auto-Generated Outputs**: Results and visualizations organized systematically

## 📚 Additional Resources

- **Llama Stack Documentation**: [Official Llama Stack Docs](https://llama-stack.readthedocs.io/)
- **DeepEval Framework**: [DeepEval Documentation](https://docs.confident-ai.com/)
- **Model Context Protocol**: [MCP Specification](https://spec.modelcontextprotocol.io/)
- **UV Package Manager**: [UV Documentation](https://github.com/astral-sh/uv)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Update documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy Evaluating! 🚀**

For questions or issues, please check the troubleshooting section or create an issue in the repository.