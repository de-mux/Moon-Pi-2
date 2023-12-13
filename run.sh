#!/usr/bin/env bash

set -o errexit   # exit immediately upon error
set -o pipefail  # exit if any step in a pipeline fails
#set -o xtrace    # print each command before execution

# Store first parameter in a variable, which should be the log file location.
LOG_FILE="$1"

# Set a default log file location if the parameter was empty, i.e. not specified.
if [ -z "$LOG_FILE" ]
then
  LOG_FILE="$HOME/moonpi.log"
fi


trap cleanup SIGINT SIGTERM ERR EXIT
cleanup() {
  trap - SIGINT SIGTERM ERR EXIT
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

export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv activate moonpi &>> "$LOG_FILE"
cd /home/moon/Moon-Pi
python moon_pi.py &>> "$LOG_FILE"

echo "Shutting down system in 10 seconds." >> "$LOG_FILE"
sleep 10
# revert trap
trap - SIGINT SIGTERM ERR EXIT
sudo shutdown now
