#!/usr/bin/expect -f
# Wrapper to run claude with unbuffered output

set timeout -1
log_user 1

# Get prompt from stdin
set prompt [read stdin]

# Spawn claude with arguments
eval spawn claude --dangerously-skip-permissions -p {@prd.json @progress.txt}

# Send the prompt
send -- "$prompt"
send -- "\04"  ;# Send EOF

# Pass through all output
expect eof
catch wait result
exit [lindex $result 3]
