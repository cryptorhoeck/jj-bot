with open('main.py', 'r') as f:
    lines = f.readlines()

# Find where to insert (before if __name__)
insert_pos = -1
for i, line in enumerate(lines):
    if 'if __name__ == "__main__":' in line:
        insert_pos = i
        break

if insert_pos > 0:
    endpoint_code = '''
@app.get("/api/module-status")
async def get_module_status():
    """Check module status from file"""
    import json
    try:
        with open("../../data/module_status.json", "r") as f:
            return json.load(f)
    except:
        return {"running": False, "last_update": None}

'''
    lines.insert(insert_pos, endpoint_code)

with open('main.py', 'w') as f:
    f.writelines(lines)
print("Fixed")
