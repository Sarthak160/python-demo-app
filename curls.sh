#!/bin/bash

set -e
HOST="http://localhost:5000"

echo "--- Logging in to get JWT token ---"
TOKEN_RESPONSE=$(curl -s -X POST "$HOST/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ]; then
    echo "Failed to get access token. Response: $TOKEN_RESPONSE"
    exit 1
fi
echo "Login successful."
echo ""

echo "--- Hitting simple endpoint to generate simple INSERT ---"
curl -s -X POST "$HOST/data" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message": "hello world"}' | jq .
echo ""

echo "--- Hitting special endpoint to generate all complex queries at once ---"
curl -s -X GET "$HOST/generate-complex-queries" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
echo ""

echo "--- Test script finished ---"
