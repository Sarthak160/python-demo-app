#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
HOST="http://localhost:5000"

# --- Helper function for clean output ---
print_header() {
    echo ""
    echo "=================================================================="
    echo "=> $1"
    echo "=================================================================="
}

# --- 1. Log in and get JWT token ---
print_header "Logging in to get JWT token"
TOKEN_RESPONSE=$(curl -s -X POST "$HOST/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo "ERROR: Failed to get access token. Login failed."
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi
echo "Login successful. Token obtained."

# --- Test Suite ---

print_header "Test 1: Simple INSERT into 'payloads' table"
curl -s -X POST "$HOST/data" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello from the test script!"}' | jq .

print_header "Test 2: Simple SELECT from 'payloads' table"
curl -s -X GET "$HOST/data" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 3: Fetching System & Session Variables (DQL)"
curl -s -X GET "$HOST/system/status" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 4: Fetching Django Migrations (DQL with DATETIME)"
curl -s -X GET "$HOST/system/migrations" \
    -H "Authorization: Bearer $ACCESS_TOKEN" 

print_header "Test 5: Checking Blacklisted Token with INNER JOIN (DQL)"
curl -s -X GET "$HOST/auth/check-token/9522d59c56404995af98d4c30bde72b3" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 6: Creating an API Log with a large parameter INSERT (DML)"
curl -s -X POST "$HOST/logs" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: test-run-$(date +%s)" \
    -d '{"event": "test_run", "details": "This is a test log entry."}' | jq .

print_header "Test 7: Applying interest to accounts with an UPDATE..IN..SELECT (DML)"
curl -s -X POST "$HOST/accounts/apply-interest" \
    -H "Authorization: Bearer $ACCESS_TOKEN" 

print_header "Test 8: Generating a report using a TEMPORARY TABLE (DDL, DML, DQL)"
curl -s -X GET "$HOST/reports/client-summary" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 9: Setting session variables (SET SESSION)"
curl -s -X POST "$HOST/system/session-config" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 10: Running Full Financial Summary Report (Complex JOIN, CASE, Subquery, Aggregation)"
curl -s -X GET "$HOST/reports/full-financial-summary" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 11: Running Complex Client Search (JOIN with LIKE and OR)"
curl -s -X GET "$HOST/search/clients?q=Corp" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

print_header "Test 12: Performing a Transaction (UPDATEs and INSERT within a transaction block)"
echo "--> Attempting a valid transfer..."
curl -s -X POST "$HOST/transactions/transfer" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"from_account_id": 1, "to_account_id": 2, "amount": 1000.50}' | jq .
echo "--> Attempting an invalid transfer (insufficient funds)..."
curl -s -X POST "$HOST/transactions/transfer" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"from_account_id": 3, "to_account_id": 1, "amount": 999999.99}' | jq .

print_header "Test 13: Hitting the original /generate-complex-queries endpoint"
curl -s -X GET "$HOST/generate-complex-queries" \
    -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo ""
print_header "All tests completed successfully!"