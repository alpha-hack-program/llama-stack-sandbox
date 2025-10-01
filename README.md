# Llama Stack Sandbox - LLM Agent Evaluation Framework

A comprehensive evaluation framework for testing locally Large Language Model (LLM) agents running on a Llama Stack Distribution image. This repository provides tools for connecting to multiple LLMs and MCP (Model Context Protocol) servers, running structured evaluations using CSV test datasets, and generating detailed evaluation visualizations.

## 🎯 Purpose

This sandbox environment enables:

- **Local Llama Stack Distribution**: Run Llama Stack containers locally with multiple LLM providers
- **MCP Server Integration**: Connect to Model Context Protocol servers for enhanced tool capabilities  
- **Structured Testing**: Define and execute test cases using CSV files with expected outcomes
- **Multi-Metric Evaluation**: Assess agent performance across QA accuracy, tool selection, parameter handling, and response quality
- **Interactive Visualization**: Generate comprehensive dashboards and charts for evaluation results analysis

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
                    ┌──────────────────────┐
                    │  Evaluation Engine   │
                    │                      │
                    │ • DeepEval Framework │
                    │ • Custom Metrics     │
                    │ • CSV Test Runner    │
                    │ • Result Analyzer    │
                    └──────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Visualization      │
                    │                      │
                    │ • HTML Dashboards    │
                    │ • Performance Charts │
                    │ • Comparison Reports │
                    └──────────────────────┘
```

## 📦 Installation & Setup

### Prerequisites

- **Python 3.10-3.11** (required for dependencies compatibility)
- **Podman** or **Docker** (for running Llama Stack Distribution)
- **curl** and **jq** (for API testing)
- **uv** (for python dependencies installation)

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd llama-stack-sandbox

# uv (recommended for faster installs)
uv sync
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

TODO start MCP Servers!!!

### 3. Start Llama Stack Distribution

```bash
# Generate configuration and start the stack
./lsd.sh
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
./run_evaluation.sh

# Run with specific parameters
./run_evaluation.sh run -c scratch/compatibility-full.csv -m llama-3-1-8b-w4a16 -v
```

### Manual Evaluation

```bash
# Using Python directly
python evaluate.py scratch/compatibility-full.csv \
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
# Create comprehensive dashboard
python visualize_results.py evaluation_results/evaluation_results_TIMESTAMP.json

# Generate specific chart types
python visualize_results.py results.json --chart-types "performance,category,timeline"

# Custom output directory
python visualize_results.py results.json --output-dir "custom_reports"
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
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project configuration
├── .env                         # Environment variables (create this)
│
├── 🚀 Core Scripts
├── lsd.sh                       # Llama Stack Distribution launcher  
├── run_evaluation.sh            # Evaluation runner with options
├── playground.sh                # Interactive testing environment
├── open_dashboard.sh            # Quick dashboard opener
│
├── 🧪 Evaluation Framework  
├── evaluate.py                  # Main evaluation orchestrator
├── evaluation_metrics.py        # Custom DeepEval metrics (941 lines)
├── evaluation_config.py         # Configuration management
├── evaluation_utils.py          # Helper functions
├── llama_stack_wrapper.py       # Agent wrapper and session management
│
├── 📊 Visualization & Analysis
├── visualize_results.py         # Chart and dashboard generator
├── compare_results.py           # Multi-result comparison tools
├── deepeval_dashboard.py        # DeepEval integration dashboard
│
├── ⚙️ Configuration
├── run.yaml                     # Generated Llama Stack config
├── run.yaml.template            # Jinja2 template for dynamic config
├── generate_run_yaml.py         # Dynamic configuration generator
├── configs/
│   └── sample_evaluation_config.yaml
│
├── 📋 Test Data
├── scratch/
│   ├── compatibility-full.csv   # Complete test suite (21 cases)
│   └── compatibility.csv        # Quick test subset
│
├── 📈 Results & Reports
├── evaluation_results/          # JSON results with timestamps
│   ├── evaluation_results_YYYYMMDD_HHMMSS.json
│   ├── logs/                    # Detailed execution logs
│   ├── reports/                 # Generated analysis reports  
│   └── visualizations/          # HTML dashboards and charts
│       ├── comprehensive_dashboard.html
│       ├── detailed_analysis.html
│       └── summary_dashboard.html
│
└── 📚 Documentation
    └── docs/
        ├── LyFin-Compliance-Annex.md
        ├── LysFin-Compliance.md
        ├── 2025_61-FR_INT.md
        └── 2025_61-FR.md
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
python generate_run_yaml.py
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
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure your models and MCP servers in .env
   cp .env.example .env
   # Edit .env with your configurations
   ```

2. **Start Llama Stack**:
   ```bash
   ./lsd.sh
   ```

3. **Run Quick Test**:
   ```bash
   ./run_evaluation.sh test
   ```

4. **Execute Full Evaluation**:
   ```bash
   ./run_evaluation.sh run -c scratch/compatibility-full.csv -v
   ```

5. **View Results**:
   ```bash
   # Generate and open dashboard
   python visualize_results.py evaluation_results/evaluation_results_*.json
   ./open_dashboard.sh
   ```

## 🔍 Advanced Usage

### Multi-Model Comparison

```bash
# Run evaluations with different models
./run_evaluation.sh run -m llama-3-1-8b-w4a16 -o results_llama.json
./run_evaluation.sh run -m granite-3-3-8b -o results_granite.json

# Compare results
python compare_results.py results_llama.json results_granite.json
```

### Custom Test Creation

1. **Create CSV File**:
   ```csv
   question,expected_answer,tool_name,tool_parameters,evaluation_criteria,category
   "Your test question","Expected response","tool_name","{\"param\":\"value\"}","Criteria for success","Custom Category"
   ```

2. **Run Evaluation**:
   ```bash
   ./run_evaluation.sh run -c your_tests.csv
   ```

3. **Analyze Results**:
   ```bash
   python visualize_results.py evaluation_results/your_results.json
   ```

### Integration with CI/CD

```bash
# Automated evaluation pipeline
./run_evaluation.sh validate -c tests/regression_tests.csv
./run_evaluation.sh run -c tests/regression_tests.csv --output results/ci_results.json
python visualize_results.py results/ci_results.json --format png --output-dir reports/
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
   ./run_evaluation.sh test
   ```

2. **Model Authentication Errors**:
   - Verify API tokens in `.env` file
   - Check model endpoint URLs are accessible
   - Ensure TLS settings match your endpoints

3. **MCP Server Connection Issues**:
   - Confirm MCP servers are running on specified ports
   - Check firewall settings for localhost connections
   - Verify MCP server URIs in `.env`

4. **Evaluation Failures**:
   ```bash
   # Run with verbose logging
   ./run_evaluation.sh run -v
   
   # Check evaluation logs
   tail -f evaluation_log.txt
   
   # Validate test CSV format
   ./run_evaluation.sh validate -c your_test_file.csv
   ```

## 📚 Additional Resources

- **Llama Stack Documentation**: [Official Llama Stack Docs](https://llama-stack.readthedocs.io/)
- **DeepEval Framework**: [DeepEval Documentation](https://docs.confident-ai.com/)
- **Model Context Protocol**: [MCP Specification](https://spec.modelcontextprotocol.io/)
- **Evaluation Best Practices**: See `docs/` directory for domain-specific guidelines

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
