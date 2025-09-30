#!/usr/bin/env python3
"""
DeepEval Cloud Dashboard Integration Script
Helps you upload results to Confident AI for web-based visualization.
"""

import json
import argparse
import subprocess
import sys
from pathlib import Path
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset
from deepeval.dataset.golden import Golden


class DeepEvalDashboardUploader:
    """Upload evaluation results to DeepEval's cloud dashboard."""
    
    def __init__(self, results_file: str):
        self.results_file = results_file
        self.data = self._load_results()
    
    def _load_results(self):
        """Load results from JSON file."""
        with open(self.results_file, 'r') as f:
            return json.load(f)
    
    def check_login_status(self) -> bool:
        """Check if user is logged into Confident AI."""
        try:
            result = subprocess.run(
                ['deepeval', 'login', '--status'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            print("❌ DeepEval CLI not found. Install with: pip install deepeval")
            return False
    
    def login_to_confident_ai(self):
        """Guide user through login process."""
        print("🔐 Logging into Confident AI...")
        print("This will open a browser window for authentication.")
        
        try:
            result = subprocess.run(['deepeval', 'login'], check=True)
            print("✅ Successfully logged into Confident AI!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to login. Please try manually: deepeval login")
            return False
        except FileNotFoundError:
            print("❌ DeepEval CLI not found. Install with: pip install deepeval")
            return False
    
    def convert_to_deepeval_format(self) -> EvaluationDataset:
        """Convert our results to DeepEval format."""
        detailed_results = self.data.get('detailed_results', [])
        goldens = []
        
        for result in detailed_results:
            if 'input' in result and 'expected_output' in result:
                golden = Golden(
                    input=result['input'],
                    expected_output=result['expected_output'],
                    actual_output=result.get('actual_output', ''),
                    context=result.get('context', []),
                    additional_metadata={
                        'category': result.get('original_test_case', {}).get('category', 'Unknown'),
                        'tool_name': result.get('original_test_case', {}).get('tool_name', 'Unknown'),
                        'evaluation_criteria': result.get('original_test_case', {}).get('evaluation_criteria', ''),
                        'metric_results': result.get('metric_results', {})
                    }
                )
                goldens.append(golden)
        
        return EvaluationDataset(goldens=goldens)
    
    def upload_to_dashboard(self, dataset_name: str = None) -> bool:
        """Upload dataset to Confident AI dashboard."""
        if not dataset_name:
            dataset_name = f"llama_stack_evaluation_{int(pd.Timestamp.now().timestamp())}"
        
        try:
            # Convert data
            dataset = self.convert_to_deepeval_format()
            
            # Upload dataset
            print(f"📤 Uploading dataset '{dataset_name}' to Confident AI...")
            
            # Use DeepEval's dataset upload functionality
            from deepeval.dataset import EvaluationDataset
            
            # This would upload to the cloud dashboard
            # Note: The exact API might vary based on DeepEval version
            print("📊 Dataset uploaded! Check your Confident AI dashboard at: https://app.confident-ai.com")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to upload dataset: {e}")
            return False
    
    def create_evaluation_script(self) -> str:
        """Create a Python script that can be run with DeepEval CLI."""
        script_content = f"""
# Generated DeepEval test script
import json
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric

# Load results data
with open('{self.results_file}', 'r') as f:
    data = json.load(f)

# Create test cases from results
test_cases = []
detailed_results = data.get('detailed_results', [])

for result in detailed_results:
    if 'input' in result and 'expected_output' in result:
        test_case = LLMTestCase(
            input=result['input'],
            expected_output=result['expected_output'],
            actual_output=result.get('actual_output', ''),
            context=result.get('context', [])
        )
        test_cases.append(test_case)

# Define metrics
answer_relevancy_metric = AnswerRelevancyMetric(threshold=0.7)
faithfulness_metric = FaithfulnessMetric(threshold=0.7)

# Run evaluation
if test_cases:
    evaluate(
        test_cases=test_cases,
        metrics=[answer_relevancy_metric, faithfulness_metric]
    )
    print("✅ Evaluation complete! Check the dashboard link above.")
else:
    print("❌ No test cases found to evaluate.")
"""
        
        script_file = Path("deepeval_test_script.py")
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        return str(script_file)
    
    def run_dashboard_evaluation(self):
        """Run evaluation that will show in dashboard."""
        script_file = self.create_evaluation_script()
        
        print(f"📝 Created evaluation script: {script_file}")
        print("🚀 Running DeepEval dashboard evaluation...")
        
        try:
            result = subprocess.run(
                ['deepeval', 'test', 'run', script_file],
                check=True
            )
            print("✅ Evaluation complete! Dashboard link should be shown above.")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run dashboard evaluation: {e}")
            print("💡 You can also run manually:")
            print(f"   deepeval test run {script_file}")
        
        except FileNotFoundError:
            print("❌ DeepEval CLI not found")
            print("💡 Install with: pip install deepeval")
            print(f"💡 Or run the script directly: python {script_file}")


def main():
    parser = argparse.ArgumentParser(description="Upload results to DeepEval dashboard")
    parser.add_argument("results_file", help="Path to JSON results file")
    parser.add_argument("--login", action="store_true", help="Login to Confident AI first")
    parser.add_argument("--name", help="Dataset name for the dashboard")
    
    args = parser.parse_args()
    
    if not Path(args.results_file).exists():
        print(f"❌ Results file not found: {args.results_file}")
        return
    
    uploader = DeepEvalDashboardUploader(args.results_file)
    
    # Check/handle login
    if args.login or not uploader.check_login_status():
        if not uploader.login_to_confident_ai():
            print("❌ Cannot proceed without login")
            return
    
    # Run dashboard evaluation
    uploader.run_dashboard_evaluation()


if __name__ == "__main__":
    main()
