#!/bin/bash

# DISTRIBUTION_IMAGE=quay.io/opendatahub/llama-stack:odh
DISTRIBUTION_IMAGE=registry.redhat.io/rhoai/odh-llama-stack-core-rhel9:v2.23

export LLAMA_STACK_PORT=8080
export LLAMA_STACK_SERVER=http://localhost:$LLAMA_STACK_PORT

if [ ! -f .env ]; then
  echo ".env file not found. Please create it with the necessary environment variables."
  exit 1
fi

source .env

# Set default base directory if not already set
# You can override this by setting LSD_BASE_DIR in your environment
export LSD_BASE_DIR=${LSD_BASE_DIR:-/opt/app-root/src}

# Function to generate dynamic run.yaml using Python script
generate_run_yaml() {
  echo "Generating dynamic run.yaml using Jinja2 template..."
  
  # # Activate virtual environment if it exists
  # if [ -f .venv/bin/activate ]; then
  #   source .venv/bin/activate
  # fi
  
  if ! python generate_run_yaml.py; then
    echo "Error: Failed to generate run.yaml from template"
    echo ""
    echo "To install Jinja2, run one of these commands:"
    echo "  pip install jinja2"
    echo "  pip install -e ."
    echo "  uv sync  # if using uv"
    exit 1
  fi
}

# Discover all available models dynamically
MODEL_NUMBERS=$(env | grep -E '^MODEL_[0-9]+_URL=' | sed 's/^MODEL_\([0-9]\+\)_URL=.*/\1/' | sort -n)

if [ -z "$MODEL_NUMBERS" ]; then
  echo "No models found in .env file. Please define MODEL_1_URL, MODEL_1_API_TOKEN, etc."
  exit 1
fi

# Discover all available MCP servers dynamically
MCP_NUMBERS=$(env | grep -E '^MCP_SERVER_[0-9]+_ID=' | sed 's/^MCP_SERVER_\([0-9]\+\)_ID=.*/\1/' | sort -n)

echo "Found models: $(echo $MODEL_NUMBERS | tr '\n' ' ')"
if [ -n "$MCP_NUMBERS" ]; then
  echo "Found MCP servers: $(echo $MCP_NUMBERS | tr '\n' ' ')"
fi
echo "Using base directory: $LSD_BASE_DIR"

# Generate dynamic run.yaml based on discovered models
generate_run_yaml

# Test each model
for model_num in $MODEL_NUMBERS; do
  url_var="MODEL_${model_num}_URL"
  token_var="MODEL_${model_num}_API_TOKEN" 
  model_var="MODEL_${model_num}_MODEL"
  
  url=${!url_var}
  token=${!token_var}
  model=${!model_var}
  
  if [ -n "$url" ] && [ -n "$token" ] && [ -n "$model" ]; then
    echo "Testing Model $model_num ($model):"
    echo "- Listing models:"
    curl -s -X GET -H "Authorization: Bearer $token" "$url/models" | jq .
    echo "- Testing chat completion:"
    curl -s -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $token" -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hello, how are you?\"}], \"model\": \"$model\"}" "$url/chat/completions" | jq .
    echo
  else
    echo "Warning: Model $model_num is missing required variables (URL, API_TOKEN, or MODEL)"
  fi
done

# Build dynamic environment variables for all models and MCP servers
MODEL_ENV_VARS=""
for model_num in $MODEL_NUMBERS; do
  for var_suffix in URL TLS_VERIFY API_TOKEN MAX_TOKENS MODEL; do
    var_name="MODEL_${model_num}_${var_suffix}"
    var_value=${!var_name}
    if [ -n "$var_value" ]; then
      MODEL_ENV_VARS="$MODEL_ENV_VARS -e $var_name=$var_value"
    fi
  done
done

# Add MCP server environment variables
for mcp_num in $MCP_NUMBERS; do
  for var_suffix in ID URI; do
    var_name="MCP_SERVER_${mcp_num}_${var_suffix}"
    var_value=${!var_name}
    if [ -n "$var_value" ]; then
      MODEL_ENV_VARS="$MODEL_ENV_VARS -e $var_name=$var_value"
    fi
  done
done

echo "Starting Llama Stack container with models: $(echo $MODEL_NUMBERS | tr '\n' ' ')"
if [ -n "$MCP_NUMBERS" ]; then
  echo "MCP servers: $(echo $MCP_NUMBERS | tr '\n' ' ')"
fi
echo "Environment variables being passed: $MODEL_ENV_VARS"

# Run the container
podman run -it --rm \
  --name llama-stack \
  -p ${LLAMA_STACK_PORT}:${LLAMA_STACK_PORT} \
  -e NO_PROXY=localhost,127.0.0.1 \
  -e "FMS_ORCHESTRATOR_URL=http://localhost" \
  $MODEL_ENV_VARS \
  -e HF_HOME=/cache/huggingface \
  -e "NAMESPACE=llama-stack" \
  -e "KUBECONFIG=/opt/app-root/src/.kube/config" \
  -v $(pwd)/.hf_cache:/cache/huggingface:Z \
  -v $(pwd)/.milvus:/opt/app-root/src/.milvus:Z \
  -v $(pwd)/run.yaml:/opt/app-root/run.yaml:ro,Z \
  -v ~/.kube:/opt/app-root/src/.kube:ro \
  -v /tmp:/tmp \
  $DISTRIBUTION_IMAGE --port ${LLAMA_STACK_PORT}

# DISTRIBUTION_IMAGE=llamastack/distribution-ollama:0.2.2

# export LLAMA_STACK_MODEL="llama3.2:3b"
# export INFERENCE_MODEL="llama3.2:3b"
# export LLAMA_STACK_PORT=8321
# export LLAMA_STACK_SERVER=http://localhost:$LLAMA_STACK_PORT

# podman run -it \
#   -p ${LLAMA_STACK_PORT}:${LLAMA_STACK_PORT} \
#   ${DISTRIBUTION_IMAGE} \
#   --port ${LLAMA_STACK_PORT} \
#   --env NO_PROXY=localhost,127.0.0.1 \
#   --env INFERENCE_MODEL=${LLAMA_STACK_MODEL} \
#   --env OLLAMA_URL=http://host.containers.internal:11434