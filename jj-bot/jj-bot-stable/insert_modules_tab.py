#!/usr/bin/env python3

with open('dashboard/jj-dashboard/src/App.jsx', 'r') as f:
    lines = f.readlines()

# Find the trades tab section
for i in range(len(lines)):
    if "activeTab === 'trades'" in lines[i]:
        # Count braces to find the end of trades section
        brace_count = 0
        start = i
        for j in range(i, len(lines)):
            brace_count += lines[j].count('{')
            brace_count -= lines[j].count('}')
            if brace_count == 0 and j > i:
                # Found the end, insert BEFORE the next closing div
                # but INSIDE the main container
                insert_at = j + 1
                
                # Make sure we're still inside the main function
                if insert_at < len(lines) - 5:  # Safety check
                    modules_code = '''
        {/* Modules Tab */}
        {activeTab === 'modules' && (
          <ModuleTab colors={colors} API_BASE={API_BASE} />
        )}

'''
                    lines.insert(insert_at, modules_code)
                    print(f"✅ Inserted modules tab at line {insert_at}")
                    break
        break

with open('dashboard/jj-dashboard/src/App.jsx', 'w') as f:
    f.writelines(lines)
