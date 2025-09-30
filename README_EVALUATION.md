# Llama Stack Agent Evaluation Framework

A comprehensive evaluation system for testing Llama Stack agents using the DeepEval framework. This system evaluates agent performance on financial and administrative tasks using CSV-based test cases.

## Features

- **Multi-metric evaluation**: Tool selection accuracy, parameter extraction, response quality
- **Comprehensive reporting**: Detailed results with category breakdowns and performance metrics
- **Flexible configuration**: Support for different models, tools, and evaluation parameters
- **CSV-based test cases**: Easy to create and manage test scenarios
- **Async evaluation**: Efficient parallel processing for faster evaluations
- **Extensible metrics**: Custom evaluation metrics for domain-specific requirements

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install individual packages
pip install deepeval llama-stack-client pandas pyyaml
```

### 2. Basic Usage

```bash
# Run evaluation with default settings
python evaluate.py scratch/compatibility.csv

# Specify model and tools
python evaluate.py scratch/compatibility.csv --model llama-3-2-3b --tools mcp::compatibility mcp::eligibility

# Save results and show verbose output
python evaluate.py scratch/compatibility.csv --output results.json --verbose

# Use different Llama Stack URL
python evaluate.py scratch/compatibility.csv --stack-url http://your-llama-stack:8321
```

### 3. Expected Output

```
Evaluation completed: 18/20 successful (90.00%)

LLAMA STACK AGENT EVALUATION RESULTS
====================================

SUMMARY:
  Total test cases: 20
  Successful evaluations: 18
  Failed evaluations: 2
  Overall success rate: 90.00%

METRIC AVERAGES:
  ToolSelectionMetric:
    Average score: 0.900
    Success rate: 90.00%
  ParameterAccuracyMetric:
    Average score: 0.850
    Success rate: 85.00%
  ResponseAccuracyMetric:
    Average score: 0.780
    Success rate: 75.00%
```

## File Structure

```
llama-stack-sandbox/
├── evaluate.py                    # Main evaluation script
├── evaluation_metrics.py          # Custom DeepEval metrics
├── evaluation_config.py           # Configuration management
├── evaluation_utils.py            # Utility functions and helpers
├── llama_stack_wrapper.py         # Llama Stack client wrapper
├── requirements.txt               # Python dependencies
├── README_EVALUATION.md           # This file
├── scratch/
│   └── compatibility.csv          # Sample test cases
└── evaluation_results/            # Output directory (created automatically)
    ├── reports/                   # Text and JSON reports
    └── logs/                      # Evaluation logs
```

## CSV Test Case Format

The CSV file should contain the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `question` | Input question for the agent | "Calculate penalty for 15 days late payment" |
| `expected_answer` | Expected response content | "$1,050 total penalty. Base penalty: 15 days × $100 = $1,500..." |
| `tool_name` | Expected tool to be called | "calc_penalty" |
| `tool_parameters` | Expected parameters (JSON) | `{"days_late": 15}` |
| `evaluation_criteria` | What to evaluate | "Correct tool selection, accurate calculation, mentions cap" |
| `category` | Test case category | "Penalty Calculations" |

## Supported Tools and Categories

### Available Tools
- `calc_penalty`: Late payment/delivery penalty calculations
- `calc_tax`: Progressive tax calculations with surcharges  
- `check_voting`: Voting result validation for different proposal types
- `distribute_waterfall`: Financial waterfall distribution calculations
- `check_housing_grant`: Housing assistance eligibility checks

### Test Categories
- **Penalty Calculations**: Late fees, liquidated damages
- **Tax Calculations**: Progressive income tax with brackets
- **Voting Validations**: Quorum and majority requirements
- **Waterfall Distributions**: Senior/junior debt distributions
- **Housing Grant Eligibility**: Income and household size checks

## Configuration

### Environment Variables

```bash
export LLAMA_STACK_URL="http://localhost:8321"
export LLAMA_STACK_MODEL="llama-3-2-3b"  
export LLAMA_STACK_TOOLS="mcp::compatibility,mcp::eligibility"
export EVALUATION_CSV_FILE="scratch/compatibility.csv"
export EVALUATION_OUTPUT_DIR="evaluation_results"
export EVALUATION_VERBOSE="true"
```

### Configuration File

Create a `config.yaml` file:

```yaml
stack_url: "http://localhost:8321"
default_model_id: "llama-3-2-3b"
default_tool_groups:
  - "mcp::compatibility"
  - "mcp::eligibility"

# Metric weights
tool_selection_weight: 0.3
parameter_accuracy_weight: 0.3
response_accuracy_weight: 0.4

# Thresholds
comprehensive_threshold: 0.7
verbose_output: true
```

## Evaluation Metrics

### 1. Tool Selection Metric
- **Purpose**: Validates that the agent selects the correct tool
- **Scoring**: Binary (1.0 for correct tool, 0.0 otherwise)
- **Threshold**: 1.0 (exact match required)

### 2. Parameter Accuracy Metric  
- **Purpose**: Evaluates accuracy of parameter extraction
- **Scoring**: Ratio of correct parameters to total expected
- **Threshold**: 0.8 (80% of parameters must be correct)

### 3. Response Accuracy Metric
- **Purpose**: Assesses overall response quality and correctness
- **Scoring**: Composite score based on numerical accuracy, status matches, warnings
- **Threshold**: 0.7 (70% accuracy required)

### 4. Comprehensive Evaluation Metric
- **Purpose**: Weighted combination of all metrics
- **Scoring**: Weighted average of individual metric scores
- **Threshold**: 0.7 (overall performance requirement)

## Advanced Usage

### Custom Configuration

```python
from evaluation_config import EvaluationConfig

# Create custom configuration
config = EvaluationConfig(
    stack_url="http://custom-stack:8321",
    default_model_id="llama-4-scout-17b-16e-w4a16",
    tool_selection_weight=0.4,
    parameter_accuracy_weight=0.3,
    response_accuracy_weight=0.3,
    parallel_evaluation=True,
    max_concurrent_evaluations=5
)

# Run evaluation with custom config
evaluator = LlamaStackEvaluator(
    stack_url=config.stack_url,
    model_id=config.default_model_id,
    tool_groups=config.default_tool_groups
)
```

### Parallel Evaluation

```python
# Enable parallel processing for faster evaluation
config = EvaluationConfig(
    parallel_evaluation=True,
    max_concurrent_evaluations=3
)
```

### Category-Specific Evaluation

```python
from evaluation_utils import CSVTestCaseLoader

# Load and filter test cases
loader = CSVTestCaseLoader("scratch/compatibility.csv")
all_cases = loader.load_and_validate()

# Evaluate only penalty calculations
penalty_cases = loader.filter_by_category("Penalty Calculations")
```

## Troubleshooting

### Common Issues

1. **Connection Error**: Ensure Llama Stack is running and accessible
   ```bash
   curl http://localhost:8321/health
   ```

2. **Tool Not Found**: Check that MCP endpoints are properly configured in `run.yaml`

3. **Parameter Parsing Failed**: Verify CSV has valid JSON in `tool_parameters` column

4. **Import Error**: Install missing dependencies
   ```bash
   pip install -r requirements.txt
   ```

### Debug Mode

Run with verbose logging:
```bash
python evaluate.py scratch/compatibility.csv --verbose
export LOG_LEVEL=DEBUG
```

### Validation

Test with a small subset:
```python
# Create a small test CSV with 2-3 cases
python evaluate.py small_test.csv --verbose
```

## API Reference

### Main Classes

#### `LlamaStackEvaluator`
Main evaluation orchestrator

```python
evaluator = LlamaStackEvaluator(
    stack_url="http://localhost:8321",
    model_id="llama-3-2-3b", 
    tool_groups=["mcp::compatibility"]
)

results = await evaluator.run_evaluation(
    csv_file_path="test_cases.csv",
    output_file="results.json",
    verbose=True
)
```

#### `LlamaStackAgentWrapper`
Wrapper for Llama Stack client

```python
wrapper = LlamaStackAgentWrapper(client, model_id, tool_groups)
await wrapper.initialize()
response = await wrapper.get_response("Calculate tax for income 50000")
```

### Custom Metrics

Extend `BaseMetric` for custom evaluation:

```python
from evaluation_metrics import BaseMetric

class CustomMetric(BaseMetric):
    def __init__(self, threshold=0.8):
        self.threshold = threshold
    
    async def a_measure(self, test_case):
        # Your evaluation logic here
        score = your_evaluation_function(test_case)
        return self._create_metric_result(score, "Custom evaluation")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### Adding New Tools

1. Add tool detection logic in `evaluation_metrics.py`
2. Update parameter extraction patterns
3. Add tool configuration in `evaluation_config.py`
4. Create test cases in CSV format

### Adding New Metrics

1. Create new metric class extending `BaseMetric`
2. Implement `a_measure()` method
3. Add to metric list in `evaluate.py`
4. Update configuration options

## License

[Your License Here]

## Support

For issues and questions:
- Check the troubleshooting section above
- Review CSV format requirements
- Ensure Llama Stack connectivity
- Verify tool group configurations
