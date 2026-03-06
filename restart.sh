#!/bin/bash
# Prism VNC Proxy Restart Script
# This script kills any running proxy instances and starts a fresh one with a watchdog loop

echo "🔄 Restarting Prism VNC Proxy..."

# Kill any existing proxy watchdog loops and processes
echo "🛑 Stopping existing proxy processes..."
pkill -f "prism-vnc-proxy.*loop" 2>/dev/null || true
pkill -f "prism_vnc_proxy.py" 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 2

# Verify processes are stopped
if pgrep -f "prism_vnc_proxy.py" > /dev/null; then
    echo "⚠️  Force killing remaining proxy processes..."
    pkill -9 -f "prism_vnc_proxy.py" 2>/dev/null || true
    sleep 1
fi

# Change to the proxy directory
cd /home/nutanix/devapps/prism-vnc-proxy

# Start the watchdog loop in the background
echo "🚀 Starting Prism VNC Proxy with watchdog loop..."
nohup bash -c "while true; do 
    source .venv/bin/activate && \
    python3 prism_vnc_proxy.py --prism_hostname=10.142.151.30 --prism_username=admin --prism_password='iVXcB1b#S6lO' --bind_port=8080 --use_pc >> /tmp/prism-vnc-proxy.log 2>&1
    echo \"[$(date)] Proxy crashed with exit code \$?. Restarting...\" >> /tmp/prism-vnc-proxy.log
    sleep 1
done" > /dev/null 2>&1 &

WATCHDOG_PID=$!

# Wait a moment for watchdog to start
sleep 2

# Check if watchdog is running
if ps -p $WATCHDOG_PID > /dev/null; then
    echo "✅ Prism VNC Proxy started successfully with self-healing loop"
    echo "📝 Logs: tail -f /tmp/prism-vnc-proxy.log"
    echo "🌐 Proxy backend: http://10.142.152.112:8080"
    echo ""
    echo "To stop: pkill -f 'prism-vnc-proxy.*loop'"
else
    echo "❌ Failed to start proxy. Check /tmp/prism-vnc-proxy.log for errors."
    exit 1
fi
