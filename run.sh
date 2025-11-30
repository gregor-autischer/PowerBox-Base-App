#!/usr/bin/with-contenv bashio
# ==============================================================================
# PowerHaus Add-on
# Runs the main PowerHaus application
# ==============================================================================

bashio::log.info "Starting PowerHaus Add-on..."

# Run the Python application
exec python3 /app.py
