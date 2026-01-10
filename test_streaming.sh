#!/bin/bash

echo "Testing real-time streaming..."
echo ""

TEMP_OUTPUT=$(mktemp)

echo "🤖 Starting Claude..."
echo ""

claude --dangerously-skip-permissions << 'PROMPT' | tee "$TEMP_OUTPUT"
Count from 1 to 5, with a sentence between each number. Be conversational.
PROMPT

echo ""
echo "=== Contents captured to temp file ==="
cat "$TEMP_OUTPUT"
rm -f "$TEMP_OUTPUT"
