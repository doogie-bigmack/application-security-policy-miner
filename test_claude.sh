#!/bin/bash

echo "=== Test 1: Direct claude call ==="
claude << 'PROMPT'
Say hello
PROMPT

echo ""
echo "=== Test 2: With dangerously-skip-permissions ==="
claude --dangerously-skip-permissions << 'PROMPT'
Say hello
PROMPT

echo ""
echo "=== Test 3: Capture to variable ==="
result=$(claude --dangerously-skip-permissions << 'PROMPT'
Say hello
PROMPT
)
echo "Captured result: $result"

echo ""
echo "=== Test 4: With tee ==="
claude --dangerously-skip-permissions << 'PROMPT'
Say hello
PROMPT
| tee /tmp/test.txt

echo ""
echo "=== Test 5: Check what's in temp file ==="
cat /tmp/test.txt
