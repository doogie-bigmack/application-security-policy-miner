#!/bin/zsh

for ((i=1; i<=2; i++)); do
    echo ""
    echo "Iteration $i"
    echo "---"
    
    # Test with just a simple prompt
    claude --dangerously-skip-permissions << 'PROMPT' | tee /tmp/test_$i.txt
Say "hello world" and then say "task complete"
PROMPT
    
    echo ""
    echo "Checking temp file..."
    cat /tmp/test_$i.txt
    
    if grep -q "task complete" /tmp/test_$i.txt; then
        echo "Found task complete!"
    fi
done
