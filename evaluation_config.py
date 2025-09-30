"""
Configuration settings for the Llama Stack evaluation system.
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvaluationConfig:
    """Configuration class for evaluation settings."""
    
    # Llama Stack settings
    stack_url: str = "http://localhost:8321"
    default_model_id: str = "llama-3-2-3b"
    default_tool_groups: List[str] = field(default_factory=lambda: ["mcp::compatibility", "mcp::eligibility"])
    
    # Evaluation settings
    default_csv_file: str = "scratch/compatibility.csv"
    output_directory: str = "evaluation_results"
    
    # Metric weights for comprehensive evaluation
    tool_selection_weight: float = 0.3
    parameter_accuracy_weight: float = 0.3
    response_accuracy_weight: float = 0.4
    
    # Thresholds
    tool_selection_threshold: float = 1.0  # Exact match required
    parameter_accuracy_threshold: float = 0.8
    response_accuracy_threshold: float = 0.7
    comprehensive_threshold: float = 0.7
    
    # Agent configuration
    agent_system_prompt: Optional[str] = None
    agent_sampling_params: Dict[str, Any] = field(default_factory=lambda: {
        "strategy": "greedy",
        "temperature": 0.0,
        "max_tokens": 2048
    })
    
    # Evaluation behavior
    verbose_output: bool = False
    save_detailed_results: bool = True
    session_cleanup: bool = True
    parallel_evaluation: bool = False  # Set to True for faster evaluation
    max_concurrent_evaluations: int = 3
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    @classmethod
    def from_yaml(cls, yaml_file: str) -> 'EvaluationConfig':
        """Load configuration from YAML file."""
        import yaml
        
        with open(yaml_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> 'EvaluationConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if available
        config.stack_url = os.getenv('LLAMA_STACK_URL', config.stack_url)
        config.default_model_id = os.getenv('LLAMA_STACK_MODEL', config.default_model_id)
        
        if os.getenv('LLAMA_STACK_TOOLS'):
            config.default_tool_groups = os.getenv('LLAMA_STACK_TOOLS').split(',')
        
        config.default_csv_file = os.getenv('EVALUATION_CSV_FILE', config.default_csv_file)
        config.output_directory = os.getenv('EVALUATION_OUTPUT_DIR', config.output_directory)
        config.verbose_output = os.getenv('EVALUATION_VERBOSE', 'false').lower() == 'true'
        config.log_level = os.getenv('LOG_LEVEL', config.log_level)
        config.log_file = os.getenv('LOG_FILE', config.log_file)
        
        return config
    
    def save_yaml(self, yaml_file: str):
        """Save configuration to YAML file."""
        import yaml
        
        # Convert to dictionary, excluding non-serializable items
        config_dict = {
            'stack_url': self.stack_url,
            'default_model_id': self.default_model_id,
            'default_tool_groups': self.default_tool_groups,
            'default_csv_file': self.default_csv_file,
            'output_directory': self.output_directory,
            'tool_selection_weight': self.tool_selection_weight,
            'parameter_accuracy_weight': self.parameter_accuracy_weight,
            'response_accuracy_weight': self.response_accuracy_weight,
            'tool_selection_threshold': self.tool_selection_threshold,
            'parameter_accuracy_threshold': self.parameter_accuracy_threshold,
            'response_accuracy_threshold': self.response_accuracy_threshold,
            'comprehensive_threshold': self.comprehensive_threshold,
            'agent_sampling_params': self.agent_sampling_params,
            'verbose_output': self.verbose_output,
            'save_detailed_results': self.save_detailed_results,
            'session_cleanup': self.session_cleanup,
            'parallel_evaluation': self.parallel_evaluation,
            'max_concurrent_evaluations': self.max_concurrent_evaluations,
            'log_level': self.log_level,
            'log_file': self.log_file
        }
        
        with open(yaml_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def create_output_directory(self):
        """Create output directory if it doesn't exist."""
        Path(self.output_directory).mkdir(parents=True, exist_ok=True)
    
    def get_output_file_path(self, filename: str) -> str:
        """Get full path for output file."""
        self.create_output_directory()
        return os.path.join(self.output_directory, filename)


# Default configurations for different scenarios
DEFAULT_CONFIGS = {
    'development': EvaluationConfig(
        stack_url="http://localhost:8321",
        verbose_output=True,
        log_level="DEBUG"
    ),
    
    'production': EvaluationConfig(
        stack_url="http://production-llama-stack:8321",
        verbose_output=False,
        log_level="INFO",
        parallel_evaluation=True,
        max_concurrent_evaluations=5
    ),
    
    'testing': EvaluationConfig(
        stack_url="http://localhost:8321",
        default_csv_file="test_data/small_compatibility.csv",
        verbose_output=True,
        log_level="DEBUG",
        session_cleanup=True
    )
}


def get_config(config_name: str = 'development') -> EvaluationConfig:
    """Get a predefined configuration."""
    if config_name in DEFAULT_CONFIGS:
        return DEFAULT_CONFIGS[config_name]
    else:
        raise ValueError(f"Unknown configuration: {config_name}. Available: {list(DEFAULT_CONFIGS.keys())}")


def load_config_from_file(config_file: str) -> EvaluationConfig:
    """Load configuration from file (YAML or environment)."""
    if config_file.endswith('.yaml') or config_file.endswith('.yml'):
        return EvaluationConfig.from_yaml(config_file)
    else:
        # Assume environment-based configuration
        return EvaluationConfig.from_env()


# Tool group definitions
AVAILABLE_TOOL_GROUPS = {
    'compatibility': 'mcp::compatibility',
    'eligibility': 'mcp::eligibility', 
    'websearch': 'builtin::websearch',
    'rag': 'builtin::rag'
}

# Model configurations
MODEL_CONFIGS = {
    'llama-3-2-3b': {
        'model_id': 'llama-3-2-3b',
        'provider_id': 'model-1',
        'max_tokens': 4096,
        'recommended_temperature': 0.0
    },
    'llama-4-scout-17b': {
        'model_id': 'llama-4-scout-17b-16e-w4a16',
        'provider_id': 'model-2', 
        'max_tokens': 4096,
        'recommended_temperature': 0.1
    }
}

# Evaluation criteria mapping
EVALUATION_CRITERIA = {
    'tool_selection': 'Correct tool selection',
    'parameter_extraction': 'Accurate parameter extraction',  
    'calculation_accuracy': 'Correct calculations',
    'response_format': 'Proper response formatting',
    'warning_handling': 'Appropriate warning messages',
    'edge_case_handling': 'Handling of edge cases'
}

# Category-specific configurations
CATEGORY_CONFIGS = {
    'Penalty Calculations': {
        'expected_tools': ['calc_penalty'],
        'key_parameters': ['days_late'],
        'validation_focus': ['calculation_accuracy', 'warning_handling']
    },
    'Tax Calculations': {
        'expected_tools': ['calc_tax'],
        'key_parameters': ['income'],
        'validation_focus': ['calculation_accuracy', 'response_format']
    },
    'Voting Validations': {
        'expected_tools': ['check_voting'],
        'key_parameters': ['eligible_voters', 'turnout', 'yes_votes', 'proposal_type'],
        'validation_focus': ['parameter_extraction', 'response_format']
    },
    'Waterfall Distributions': {
        'expected_tools': ['distribute_waterfall'],
        'key_parameters': ['cash_available', 'senior_debt', 'junior_debt'],
        'validation_focus': ['calculation_accuracy', 'warning_handling']
    },
    'Housing Grant Eligibility': {
        'expected_tools': ['check_housing_grant'],
        'key_parameters': ['ami', 'household_size', 'income', 'has_other_subsidy'],
        'validation_focus': ['parameter_extraction', 'edge_case_handling']
    }
}
