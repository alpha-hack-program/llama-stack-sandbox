#!/bin/bash

# Llama Stack Agent Evaluation Runner Script
# This script helps run evaluations with different configurations

set -e

# Default values
CSV_FILE="scratch/compatibility-full.csv"
# MODEL="llama-3-2-3b"
MODEL="llama-3-1-8b-w4a16"
TOOLS="mcp::compatibility"
STACK_URL="http://localhost:8080"
OUTPUT_DIR="evaluation_results"
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Llama Stack is running
check_llama_stack() {
    print_info "Checking Llama Stack connectivity..."
    
    if curl -s --connect-timeout 5 "$STACK_URL/health" > /dev/null 2>&1; then
        print_success "Llama Stack is running at $STACK_URL"
        return 0
    else
        print_error "Cannot connect to Llama Stack at $STACK_URL"
        print_info "Please ensure Llama Stack is running:"
        print_info "  1. Check if the server is started"
        print_info "  2. Verify the URL is correct"
        print_info "  3. Check firewall/network settings"
        return 1
    fi
}

# Function to check dependencies
check_dependencies() {
    print_info "Checking Python dependencies..."
    
    if ! python3 -c "import deepeval, llama_stack_client" > /dev/null 2>&1; then
        print_warning "Missing required dependencies"
        print_info "Installing dependencies from requirements.txt..."
        
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
        else
            print_info "requirements.txt not found, installing core dependencies..."
            pip install deepeval llama-stack-client pandas pyyaml
        fi
        
        print_success "Dependencies installed"
    else
        print_success "All dependencies are available"
    fi
}

# Function to validate CSV file
validate_csv() {
    local csv_file="$1"
    
    print_info "Validating CSV file: $csv_file"
    
    if [ ! -f "$csv_file" ]; then
        print_error "CSV file not found: $csv_file"
        return 1
    fi
    
    # Check if CSV has required headers
    local headers=$(head -n 1 "$csv_file")
    local required_headers="question,expected_answer,tool_name,tool_parameters,evaluation_criteria,category"
    
    if [[ "$headers" == *"question"* ]] && [[ "$headers" == *"expected_answer"* ]]; then
        print_success "CSV file format appears valid"
        
        # Count test cases
        local test_count=$(($(wc -l < "$csv_file") - 1))
        print_info "Found $test_count test cases in CSV"
        return 0
    else
        print_error "CSV file missing required headers"
        print_info "Required headers: $required_headers"
        return 1
    fi
}

# Function to setup evaluation environment
setup_environment() {
    print_info "Setting up evaluation environment..."
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR/reports"
    mkdir -p "$OUTPUT_DIR/logs"
    
    # Run Python setup if available
    if [ -f "evaluation_utils.py" ]; then
        python3 -c "from evaluation_utils import setup_evaluation_environment; setup_evaluation_environment()" 2>/dev/null || true
    fi
    
    print_success "Evaluation environment ready"
}

# Function to run evaluation
run_evaluation() {
    local csv_file="$1"
    local model="$2"
    local tools="$3"
    local stack_url="$4"
    local output_file="$5"
    local verbose="$6"
    
    print_info "Starting evaluation..."
    print_info "  CSV file: $csv_file"
    print_info "  Model: $model"
    print_info "  Tools: $tools"
    print_info "  Stack URL: $stack_url"
    print_info "  Output: $output_file"
    
    # Build command
    local cmd="python3 evaluate.py \"$csv_file\" --model \"$model\" --stack-url \"$stack_url\""
    
    if [ "$output_file" != "" ]; then
        cmd="$cmd --output \"$output_file\""
    fi
    
    if [ "$verbose" = true ]; then
        cmd="$cmd --verbose"
    fi
    
    # Add tools
    for tool in $tools; do
        cmd="$cmd --tools $tool"
    done
    
    print_info "Running command: $cmd"
    
    # Execute evaluation
    if eval "$cmd"; then
        print_success "Evaluation completed successfully"
        
        if [ "$output_file" != "" ] && [ -f "$output_file" ]; then
            print_info "Results saved to: $output_file"
        fi
        return 0
    else
        print_error "Evaluation failed"
        return 1
    fi
}

# Function to run quick test
run_quick_test() {
    print_info "Running quick connectivity test..."
    
    if check_llama_stack; then
        print_success "Quick test passed - Llama Stack is accessible"
    else
        print_error "Quick test failed - cannot connect to Llama Stack"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  run                 Run evaluation (default)"
    echo "  test                Run quick connectivity test"
    echo "  setup               Setup evaluation environment"
    echo "  validate            Validate CSV file only"
    echo ""
    echo "Options:"
    echo "  -c, --csv FILE      CSV file path (default: $CSV_FILE)"
    echo "  -m, --model MODEL   Model ID (default: $MODEL)"
    echo "  -t, --tools TOOLS   Space-separated tool groups (default: $TOOLS)"
    echo "  -u, --url URL       Llama Stack URL (default: $STACK_URL)"
    echo "  -o, --output FILE   Output file path"
    echo "  -v, --verbose       Enable verbose output"
    echo "  -h, --help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 run -c scratch/compatibility.csv -v"
    echo "  $0 run -m llama-4-scout-17b -o results.json"
    echo "  $0 test"
    echo "  $0 setup"
}

# Parse command line arguments
COMMAND="run"
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--csv)
            CSV_FILE="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -t|--tools)
            TOOLS="$2"
            shift 2
            ;;
        -u|--url)
            STACK_URL="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        run|test|setup|validate)
            COMMAND="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_info "Llama Stack Agent Evaluation Runner"
    print_info "Command: $COMMAND"
    
    case "$COMMAND" in
        "test")
            run_quick_test
            ;;
        "setup")
            setup_environment
            ;;
        "validate")
            validate_csv "$CSV_FILE"
            ;;
        "run")
            # Full evaluation run
            setup_environment
            
            if ! validate_csv "$CSV_FILE"; then
                exit 1
            fi
            
            # if ! check_dependencies; then
            #     exit 1
            # fi
            
            if ! check_llama_stack; then
                exit 1
            fi
            
            # Set output file if not specified
            if [ "$OUTPUT_FILE" == "" ]; then
                timestamp=$(date +"%Y%m%d_%H%M%S")
                OUTPUT_FILE="$OUTPUT_DIR/evaluation_results_${timestamp}.json"
            fi
            
            if run_evaluation "$CSV_FILE" "$MODEL" "$TOOLS" "$STACK_URL" "$OUTPUT_FILE" "$VERBOSE"; then
                print_success "Evaluation completed successfully!"
                
                if [ -f "$OUTPUT_FILE" ]; then
                    print_info "Results available at: $OUTPUT_FILE"
                fi
            else
                exit 1
            fi
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main
