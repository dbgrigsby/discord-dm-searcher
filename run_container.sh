#!/bin/bash

# Get the current working directory
current_dir=$(pwd)

# Check if the container exists
container_id=$(sudo docker ps -a -q -f name=discord-dm-searcher)

if [ -n "$container_id" ]; then
    # Container exists, check if it is stopped
    container_status=$(sudo docker inspect -f '{{.State.Status}}' discord-dm-searcher)
    if [ "$container_status" == "exited" ]; then
        echo "Starting the existing container..."
        sudo docker start discord-dm-searcher
    else
        echo "Container is already running."
    fi
else
    # Container does not exist, create and start a new one
    echo "Creating and starting a new container..."
    sudo docker run -d --name discord-dm-searcher \
      -v "$current_dir/summaries:/app/summaries" \
      -v "$current_dir/searches:/app/searches" \
      -v "$current_dir/import:/app/import" \
      -v "$current_dir/OPENAI_KEY.txt:/app/OPENAI_KEY.txt:ro" \
      -v "$current_dir/DISCORD_TOKEN.txt:/app/DISCORD_TOKEN.txt:ro" \
      discord-dm-searcher
fi
