#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
HOST="http://localhost:5000"
REQUESTS=100
CONCURRENT=10  # Number of concurrent requests (adjust based on your system)
LOG_FILE="load_test.log"

# Initialize log file
> "$LOG_FILE"

# --- Helper functions ---
print_header() {
    echo ""
    echo "=================================================================="
    echo "=> $1"
    echo "=================================================================="
}

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

run_test() {
    local test_name=$1
    local endpoint=$2
    local method=$3
    local data=$4
    
    log "Starting $test_name..."
    
    # Run the test in parallel
    seq 1 $REQUESTS | xargs -I{} -P $CONCURRENT \
    curl -s -X $method "$HOST/$endpoint" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$data" >> "$LOG_FILE" 2>&1
    
    log "Completed $test_name"
}

# --- Login to get JWT token ---
print_header "Logging in to get JWT token"
TOKEN_RESPONSE=$(curl -s -X POST "$HOST/login" \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "admin123"}')

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    log "ERROR: Failed to get access token. Login failed."
    log "Response: $TOKEN_RESPONSE"
    exit 1
fi
log "Login successful. Token obtained."

# --- Test Suite ---

print_header "Starting load test with $REQUESTS requests per endpoint"

# Simple INSERT test
run_test "INSERT test" "data" "POST" '{"message": "Load test message"}'

# Simple SELECT test
run_test "SELECT test" "data" "GET" ""

# System status test
run_test "System status test" "system/status" "GET" ""

# Log creation test
run_test "Log creation test" "logs" "POST" '{"event": "load_test", "details": "This is a load test log entry."}'

# Transaction test (mix of valid and invalid)
run_test "Transaction test" "transactions/transfer" "POST" \
'{"from_account_id": '$((RANDOM % 5 + 1))', "to_account_id": '$((RANDOM % 5 + 1))', "amount": '$((RANDOM % 1000)).$((RANDOM % 99))'}'

print_header "Load test completed"
log "Check $LOG_FILE for detailed results"

# Optional: Add summary statistics
print_header "Summary Statistics"
grep -c "HTTP" "$LOG_FILE" | awk '{print "Total responses: " $1}'
log "Error count: $(grep -i "error" "$LOG_FILE" | wc -l)"