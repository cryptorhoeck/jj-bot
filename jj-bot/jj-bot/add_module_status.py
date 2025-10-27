with open('dashboard/jj-dashboard/src/App.jsx', 'r') as f:
    lines = f.readlines()

# Find the last closing </div> and add before it
for i in range(len(lines)-1, 0, -1):
    if '</div>' in lines[i]:
        lines.insert(i, '      <ModuleStatus API_BASE={API_BASE} />\n')
        break

with open('dashboard/jj-dashboard/src/App.jsx', 'w') as f:
    f.writelines(lines)
