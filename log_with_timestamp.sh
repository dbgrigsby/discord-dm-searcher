#!/bin/bash

# Read input line by line and prepend the current timestamp
while IFS= read -r line; do
    echo "$(date +"%Y-%m-%d %H:%M:%S") $line"
done
