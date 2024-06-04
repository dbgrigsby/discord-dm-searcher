#!/bin/bash
# Activate the virtual environment
source virtualenv_run/bin/activate

# Execute the command passed to the container
exec "$@"
