#!/usr/bin/env bash

set -o errexit   # exit immediately upon error
set -o pipefail  # exit if any step in a pipeline fails
#set -o xtrace    # print each command before execution

# The presence of this file will disable the shutdown at the end.
# Create this file to disable shutdown.
SHUTDOWN_DISABLE_FILE=$HOME/noshutdown

# Store first parameter in a variable, which should be the log file location.
LOG_FILE="$1"
# Set a default log file location if the parameter was empty, i.e. not specified.
if [ -z "$LOG_FILE" ]
then
  LOG_FILE="$HOME/moonpi.log"
fi


trap cleanup SIGINT SIGTERM ERR
cleanup() {
  trap - SIGINT SIGTERM ERR
  echo "run.sh exited abnormally" >> "$LOG_FILE"
}


# Rotate log file if necessary
MAX_LOG_SIZE=10000
if [ -f "$LOG_FILE" ]
then
    log_size=$(du -k "$LOG_FILE" | cut -f 1)
    if [ $log_size -ge $MAX_LOG_SIZE ]; then
        # rollover log file
        savelog -n -l -c 2 "$LOG_FILE"
    fi
fi

echo "----------------------------------------" >> "$LOG_FILE"
echo "System date and time: $(date '+%Y/%m/%d %H:%M:%S')" >> "$LOG_FILE"
echo "Kernel info: $(uname -rmv)" >> "$LOG_FILE"
echo "Uptime: $(uptime)" >> "$LOG_FILE"

# Activate pyenv and the virtual environment
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate moonpi &>> "$LOG_FILE"

# Run the moon_pi script
cd /home/moon/Moon-Pi
python moon_pi.py &>> "$LOG_FILE"


if [ -f "$SHUTDOWN_DISABLE_FILE" ]; then
    echo "$SHUTDOWN_DISABLE_FILE found. Disabling auto-shutdown."
    exit 0
else
    echo "Shutting down system in 10 seconds." >> "$LOG_FILE"
    sleep 10
    # revert trap
    trap - SIGINT SIGTERM ERR
    sudo shutdown now
fi
