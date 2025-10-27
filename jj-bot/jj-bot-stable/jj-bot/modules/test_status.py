#!/usr/bin/env python3
import json
from datetime import datetime

# Write a test status
status = {
    "running": True,
    "last_update": datetime.now().isoformat(),
    "coins_tracked": 20,
    "signals_today": 5
}

with open("../data/module_status.json", "w") as f:
    json.dump(status, f)
    
print("Status written:", status)
