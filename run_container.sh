#!/bin/sh

# Get the current working directory
current_dir=$(pwd)

# Check if the container exists
container_id=$(sudo docker ps -a -q -f name=discord-dm-searcher)

if [ -n "$container_id" ]; then
    # Container exists, stop and remove it
    echo "Stopping and removing the existing container..."
    sudo docker stop discord-dm-searcher
    sudo docker rm discord-dm-searcher
fi

# Create and start a new container
echo "Creating and starting a new container..."
sudo docker run --name discord-dm-searcher \
  -v "$current_dir/summaries:/app/summaries" \
  -v "$current_dir/searches:/app/searches" \
  -v "$current_dir/import:/app/import" \
  -v "$current_dir/OPENAI_KEY.txt:/app/OPENAI_KEY.txt:ro" \
  -v "$current_dir/DISCORD_TOKEN.txt:/app/DISCORD_TOKEN.txt:ro" \
  discord-dm-searcher
