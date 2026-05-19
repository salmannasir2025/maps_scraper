#!/bin/bash

# Absolute paths configuration
PROJECT_DIR="$HOME/Documents/projects/maps_scrapper"
VENV_STREAMLIT="$PROJECT_DIR/venv/bin/streamlit"
APP_SCRIPT="$PROJECT_DIR/app.py"
PORT=8501

# Function to check if Streamlit is already running
is_running() {
    pgrep -f "streamlit run.*app.py" > /dev/null
}

if is_running; then
    echo "MapScraper Pro is already running. Opening default browser to UI..."
    xdg-open "http://localhost:$PORT"
else
    echo "Starting MapScraper Pro server in background..."
    cd "$PROJECT_DIR"
    
    # Run Streamlit in headless server mode to prevent automatic double-tab opening
    nohup "$VENV_STREAMLIT" run "$APP_SCRIPT" --server.port $PORT --server.headless true > /tmp/mapscraper_runner.log 2>&1 &
    
    # Wait for the process to spin up and register
    for i in {1..10}; do
        if is_running; then
            break
        fi
        sleep 0.5
    done
    
    echo "Opening default browser to UI..."
    xdg-open "http://localhost:$PORT"
fi
