#!/usr/bin/env python3

with open('dashboard/jj-dashboard/src/App.jsx', 'r') as f:
    content = f.read()

# Find the trades tab section and the closing of the main div
trades_section = "activeTab === 'trades'"
if trades_section in content:
    # Find where trades section ends
    trades_start = content.index(trades_section)
    
    # Find the closing of the trades section (count braces)
    pos = trades_start
    brace_count = 0
    started = False
    
    for i in range(trades_start, len(content)):
        if content[i] == '{':
            brace_count += 1
            started = True
        elif content[i] == '}':
            brace_count -= 1
            if started and brace_count == 0:
                # Found the end of trades section
                # Insert modules tab after this
                insert_pos = i + 1
                
                modules_code = '''

        {/* Modules Tab */}
        {activeTab === 'modules' && (
          <ModuleTab colors={colors} API_BASE={API_BASE} />
        )}'''
                
                content = content[:insert_pos] + modules_code + content[insert_pos:]
                break

with open('dashboard/jj-dashboard/src/App.jsx', 'w') as f:
    f.write(content)

print("✅ Modules tab added correctly")
