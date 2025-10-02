#!/bin/bash

set -e


if [ ! -f .env ]; then
  echo ".env file not found. Please create it with the necessary environment variables."
  exit 1
fi

source .env

# Fail if LLAMA_STACK_HOST or LLAMA_STACK_PORT is not set
if [ -z "$LLAMA_STACK_HOST" ] || [ -z "$LLAMA_STACK_PORT" ]; then
  echo "LLAMA_STACK_HOST or LLAMA_STACK_PORT is not set. Please set them in the .env file."
  exit 1
fi

export LLAMA_STACK_ENDPOINT=http://$LLAMA_STACK_HOST:$LLAMA_STACK_PORT

# Show the environment variables
echo "LLAMA_STACK_ENDPOINT: $LLAMA_STACK_ENDPOINT"

# Test the endpoint and fail if it's not working using jq .status is OK silently
echo "Testing the endpoint..."
if ! curl -s -X GET $LLAMA_STACK_ENDPOINT/v1/health | jq '.status == "OK"' > /dev/null; then
  echo "Failed to test the endpoint. Please check the .env file."
  exit 1
fi


podman run -p 8501:8501 \
  --env NO_PROXY=localhost,127.0.0.1 \
  --env LLAMA_STACK_ENDPOINT=${LLAMA_STACK_ENDPOINT} \
  quay.io/rh-aiservices-bu/llama-stack-playground:0.2.11