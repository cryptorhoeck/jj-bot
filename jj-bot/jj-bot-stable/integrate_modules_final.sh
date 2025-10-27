#!/bin/bash

# Add modules tab to App.jsx with minimal changes

cd ~/jj-bot/dashboard/jj-dashboard/src

# Step 1: Add import at the very top of App.jsx (after existing imports)
sed -i "1a import { ModuleTab } from './ModuleTab.jsx';" App.jsx

# Step 2: Add 'modules' to the tab array (find the line with overview, market, control, trades)
sed -i "s/\['overview', 'market', 'control', 'trades'\]/['overview', 'market', 'control', 'trades', 'modules']/" App.jsx

# Step 3: Add the modules tab render (add before the last closing div)
# This is trickier, so we'll do it with a temporary marker
cat >> App.jsx << 'MODULEBLOCK'

        {/* Modules Tab - Trading System */}
        {activeTab === 'modules' && (
          <ModuleTab colors={colors} API_BASE={API_BASE} />
        )}
MODULEBLOCK

echo "✅ Modules tab added to dashboard"
