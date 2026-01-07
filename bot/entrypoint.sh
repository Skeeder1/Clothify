#!/bin/bash
# ===========================================
# Clothify Bot - Entrypoint with Connectivity Tests
# ===========================================

set -e

echo "🚀 Starting Clothify Bot..."
echo ""

# Run connectivity tests
echo "Running pre-flight checks..."
python -m bot.tests.connectivity_test

# If tests passed, start the bot
if [ $? -eq 0 ]; then
    echo ""
    echo "🤖 Starting Discord bot..."
    exec python -m bot.main
else
    echo ""
    echo "❌ Pre-flight checks failed. Exiting..."
    exit 1
fi
