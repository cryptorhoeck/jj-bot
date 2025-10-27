# JJ-Bot Directory Cleanup Plan

## 🚨 CURRENT MESS - What We Have

```
/home/user/jj-bot/                          ← Git repo root
│
├── .git/                                    ✅ KEEP (Git data)
├── .gitignore                               ✅ KEEP
├── README_FOR_CLAUDE_CODE.md                ✅ KEEP
├── WINDOWS_SETUP.md                         ✅ KEEP
├── MIGRATION_INSTRUCTIONS.txt               ✅ KEEP
│
├── jj-bot/                                  ⚠️ FIRST NESTED LEVEL
│   ├── jj-bot/                             ⚠️⚠️ SECOND NESTED LEVEL (ACTIVE CODE)
│   │   ├── glue/api/                       ✅ ACTIVE - Has Windows fixes
│   │   ├── services/                       ✅ ACTIVE - Has Windows fixes
│   │   ├── dashboard/jj-dashboard/         ✅ ACTIVE - React dashboard
│   │   ├── modules/                        ✅ ACTIVE - Trading modules
│   │   ├── hands/                          ⚠️ ENTERPRISE FEATURES (not used)
│   │   ├── ops/                            ⚠️ ENTERPRISE FEATURES (not used)
│   │   ├── dev-portal/                     ⚠️ DEVELOPER PORTAL (not used)
│   │   ├── data/                           ✅ KEEP - Runtime data
│   │   ├── docs/                           ✅ KEEP - Documentation
│   │   ├── metadata/                       ⚠️ BACKUP METADATA (delete)
│   │   │
│   │   ├── *.bat                           ✅ KEEP - Windows scripts
│   │   ├── WINDOWS_*.md                    ✅ KEEP - Windows docs
│   │   ├── requirements.txt                ✅ KEEP
│   │   │
│   │   ├── *.sh (15+ files)                ❌ DELETE - Linux only
│   │   ├── jj (CLI script)                 ❌ DELETE - Linux only
│   │   ├── jj.backup.* (3 files)           ❌ DELETE - Backups
│   │   ├── *.backup (20+ files)            ❌ DELETE - Backups
│   │   ├── *_broken.py                     ❌ DELETE - Broken code
│   │   ├── test_*.py (10+ files)           ⚠️ MOVE to tests/ folder
│   │   ├── fix_*.py (5+ files)             ❌ DELETE - One-time scripts
│   │   └── add_*.py (3+ files)             ❌ DELETE - One-time scripts
│   │
│   ├── jj-bot-stable/                      ❌❌ DELETE ENTIRE FOLDER
│   │   ├── jj-bot/                         ⚠️⚠️⚠️ TRIPLE NESTING!
│   │   └── (duplicate old code)
│   │
│   └── jj-bot-backups/                     ❌❌ DELETE ENTIRE FOLDER
│       └── jj-bot-foundation-20250913/     (old backup from Sept 13)
│
└── (all other root files)                   ✅ KEEP

```

---

## 📊 SIZE BREAKDOWN

| Path | Size | Status |
|------|------|--------|
| `jj-bot/jj-bot/` (ACTIVE) | 1.9M | ✅ KEEP & FLATTEN |
| `jj-bot/jj-bot-stable/` | 3.7M | ❌ DELETE (1.9M duplicate code) |
| `jj-bot/jj-bot-backups/` | 1.6M | ❌ DELETE (old backup) |
| Backup files (.backup, .bak) | ~500K | ❌ DELETE (scattered) |
| Test scripts (test_*.sh/py) | ~100K | ⚠️ CONSOLIDATE |
| Linux scripts (*.sh, jj) | ~50K | ❌ DELETE (Windows only) |

**Total deletable:** ~7.8M out of 8M (97% waste!)

---

## 🎯 TARGET STRUCTURE - Clean & Flat

```
/home/user/jj-bot/                          ← Git repo root
│
├── .git/
├── .gitignore
├── README.md                               ← Updated main README
├── requirements.txt
│
├── setup_windows.bat                       ← Windows setup
├── start_all.bat                           ← Windows start
├── stop_all.bat                            ← Windows stop
│
├── glue/                                   ← Moved from jj-bot/jj-bot/
│   └── api/
│       ├── main.py                         ← Fixed for Windows
│       ├── engine.py                       ← Fixed for Windows
│       ├── service_endpoints.py
│       └── ...
│
├── services/                               ← Moved from jj-bot/jj-bot/
│   ├── manager_v2.py                       ← Fixed for Windows
│   ├── base/
│   ├── trading/
│   └── core/
│
├── dashboard/                              ← Moved from jj-bot/jj-bot/
│   └── jj-dashboard/
│       ├── src/
│       │   ├── App.jsx
│       │   ├── ControlPanel.jsx
│       │   └── ...
│       ├── package.json
│       └── vite.config.js
│
├── modules/                                ← Moved from jj-bot/jj-bot/
│   ├── data_feed/
│   │   └── enhanced_feed.py
│   ├── strategy/
│   ├── risk/
│   └── polished_system.py                  ← Fixed for Windows
│
├── data/                                   ← Runtime data (gitignored)
│   ├── trades.db
│   └── jjbot.db
│
├── docs/                                   ← Documentation
│   ├── WINDOWS_MIGRATION_COMPLETE.md
│   ├── QUICKSTART_WINDOWS.md
│   ├── MIGRATION_SUMMARY.md
│   └── current-state/
│
└── tests/                                  ← NEW: Consolidated tests
    ├── test_real_services.py
    ├── test_service_manager.py
    └── final_system_test.py

```

---

## ❌ WHAT TO DELETE

### 1. Entire Folders (DELETE IMMEDIATELY)
```bash
jj-bot/jj-bot-stable/                       # 3.7M - Old version
jj-bot/jj-bot-backups/                      # 1.6M - Dated backups
jj-bot/jj-bot/hands/                        # 80K - Enterprise features
jj-bot/jj-bot/ops/                          # 97K - Operations tools
jj-bot/jj-bot/dev-portal/                   # 649K - Developer portal
jj-bot/jj-bot/metadata/                     # 185K - Backup metadata
jj-bot/jj-bot/dashboard/simple/             # Old simple dashboard
```

### 2. Linux Scripts (DELETE - Windows only)
```bash
jj-bot/jj-bot/backup_manager.sh
jj-bot/jj-bot/backup_with_changelog.sh
jj-bot/jj-bot/check_status.sh
jj-bot/jj-bot/enhanced_jj.sh
jj-bot/jj-bot/fix_jj_cli.sh
jj-bot/jj-bot/jj                            # Linux CLI
jj-bot/jj-bot/jj_enhanced.sh
jj-bot/jj-bot/module_status.sh
jj-bot/jj-bot/restore.sh
jj-bot/jj-bot/start_clean.sh
jj-bot/jj-bot/update_template.sh
jj-bot/jj-bot/test_*.sh (7 files)
```

### 3. Backup Files (DELETE)
```bash
jj-bot/jj-bot/jj.backup.*                   # 3 files
jj-bot/jj-bot/jj_old_backup
jj-bot/jj-bot/glue/api/*.backup             # 5+ files
jj-bot/jj-bot/glue/api/*_broken.py
jj-bot/jj-bot/dashboard/jj-dashboard/src/*.backup  # 5 files
jj-bot/jj-bot/dashboard/jj-dashboard/src/*_broken.jsx
jj-bot/jj-bot/dev-portal/*.backup           # 3+ files
```

### 4. One-Time Fix Scripts (DELETE)
```bash
jj-bot/jj-bot/fix_dev_portal.py
jj-bot/jj-bot/fix_jj_status.py
jj-bot/jj-bot/add_module_status.py
jj-bot/jj-bot/add_modules_correctly.py
jj-bot/jj-bot/insert_modules_tab.py
```

### 5. Unused/Incomplete Files
```bash
jj-bot/jj-bot/jj_enterprise_master.py       # Not used
jj-bot/jj-bot/jj_master_control.py          # Not used
jj-bot/jj-bot/config.json                   # Empty config
jj-bot/jj-bot/CHANGELOG.md                  # Old changelog
jj-bot/jj-bot/VERSION                       # Not tracking versions
jj-bot/jj-bot/ROADMAP.md                    # Old roadmap
jj-bot/jj-bot/TRADING_ANALYSIS.md           # Old analysis
jj-bot/jj-bot/JJ_COMMANDS.md                # Linux commands
jj-bot/jj-bot/PROJECT_STATUS.md             # Outdated
```

---

## ✅ WHAT TO KEEP & MOVE

### Core Application Files
```
✅ glue/api/*.py                            → Move to root /glue/api/
✅ services/**/*.py                         → Move to root /services/
✅ dashboard/jj-dashboard/**/*              → Move to root /dashboard/jj-dashboard/
✅ modules/**/*.py                          → Move to root /modules/
✅ requirements.txt                         → Move to root
✅ data/ (runtime)                          → Move to root
✅ docs/                                    → Move to root
```

### Windows Files (Already at right level)
```
✅ setup_windows.bat                        → Move to root
✅ start_all.bat                            → Move to root
✅ stop_all.bat                             → Move to root
✅ WINDOWS_MIGRATION_COMPLETE.md            → Move to docs/
✅ QUICKSTART_WINDOWS.md                    → Move to docs/
✅ MIGRATION_SUMMARY.md                     → Move to docs/
```

### Test Files (Consolidate)
```
✅ test_real_services.py                    → Move to root /tests/
✅ test_service_manager.py                  → Move to root /tests/
✅ final_system_test.py                     → Move to root /tests/
✅ test_enterprise_complete.py              → Move to root /tests/
✅ test_notifications.py                    → Move to root /tests/
```

---

## 🔧 FILES NEEDING PATH UPDATES

After moving from `jj-bot/jj-bot/` to root, these files need path fixes:

### 1. Python Files
```python
# glue/api/main.py
- Currently: Goes up 2 levels to find project root
- After move: Goes up 1 level to find project root

# services/manager_v2.py
- Currently: os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
- After move: os.path.dirname(os.path.abspath(__file__))

# glue/api/engine.py
- Currently: Path(__file__).parent.parent.parent
- After move: Path(__file__).parent.parent
```

### 2. Batch Scripts
```batch
# start_all.bat
- Currently: cd glue\api
- After move: cd glue\api (SAME - no change needed)

# setup_windows.bat
- Currently: cd dashboard\jj-dashboard
- After move: cd dashboard\jj-dashboard (SAME - no change needed)
```

### 3. Documentation
```
# Update all docs to show new paths
- README.md (create new)
- QUICKSTART_WINDOWS.md (update paths)
- WINDOWS_MIGRATION_COMPLETE.md (update paths)
```

---

## 📋 EXECUTION PLAN - Step by Step

### Phase 1: Backup Safety
```bash
# 1. Verify we're on the right branch
git status

# 2. Create a safety tag before cleanup
git tag pre-cleanup-backup

# 3. Commit current state
git add -A
git commit -m "Pre-cleanup checkpoint"
```

### Phase 2: Move Active Code to Root
```bash
# 1. Move core directories
mv jj-bot/jj-bot/glue ./
mv jj-bot/jj-bot/services ./
mv jj-bot/jj-bot/dashboard ./
mv jj-bot/jj-bot/modules ./
mv jj-bot/jj-bot/data ./
mv jj-bot/jj-bot/docs ./

# 2. Move Windows files
mv jj-bot/jj-bot/*.bat ./
mv jj-bot/jj-bot/requirements.txt ./

# 3. Create tests directory and move
mkdir tests
mv jj-bot/jj-bot/test_*.py tests/ 2>/dev/null
mv jj-bot/jj-bot/final_system_test.py tests/ 2>/dev/null
```

### Phase 3: Delete Cruft
```bash
# 1. Delete entire backup folders
rm -rf jj-bot/jj-bot-stable
rm -rf jj-bot/jj-bot-backups

# 2. Delete enterprise/unused folders from active code
rm -rf jj-bot/jj-bot/hands
rm -rf jj-bot/jj-bot/ops
rm -rf jj-bot/jj-bot/dev-portal
rm -rf jj-bot/jj-bot/metadata

# 3. Delete Linux scripts
rm -f jj-bot/jj-bot/*.sh
rm -f jj-bot/jj-bot/jj jj-bot/jj-bot/jj.*

# 4. Delete backup files
find jj-bot/jj-bot -name "*.backup*" -delete
find jj-bot/jj-bot -name "*.bak" -delete
find jj-bot/jj-bot -name "*_broken.*" -delete

# 5. Delete fix scripts
rm -f jj-bot/jj-bot/fix_*.py
rm -f jj-bot/jj-bot/add_*.py
rm -f jj-bot/jj-bot/insert_*.py

# 6. Delete old docs
rm -f jj-bot/jj-bot/CHANGELOG.md
rm -f jj-bot/jj-bot/VERSION*
rm -f jj-bot/jj-bot/ROADMAP.md
rm -f jj-bot/jj-bot/TRADING_ANALYSIS.md
rm -f jj-bot/jj-bot/JJ_COMMANDS.md
rm -f jj-bot/jj-bot/PROJECT_STATUS.md
rm -f jj-bot/jj-bot/README.md
rm -f jj-bot/jj-bot/config.json

# 7. Delete enterprise scripts
rm -f jj-bot/jj-bot/jj_enterprise_master.py
rm -f jj-bot/jj-bot/jj_master_control.py
```

### Phase 4: Delete Now-Empty Nested Folder
```bash
# After moving everything, delete the nested jj-bot folders
rm -rf jj-bot/jj-bot
rm -rf jj-bot
```

### Phase 5: Fix Paths in Moved Files
```bash
# Update Python files to use correct relative paths
# (Details in next section)
```

### Phase 6: Create New README
```bash
# Create comprehensive Windows-focused README.md at root
```

### Phase 7: Test & Commit
```bash
# 1. Test that structure works
ls -la

# 2. Add all changes
git add -A

# 3. Commit cleanup
git commit -m "Major cleanup: Flatten directory structure, remove backups and cruft"

# 4. Push
git push origin claude/migrate-to-windows-011CUWsMxgpj4Cdb8M8ffDnr
```

---

## 🎯 EXPECTED RESULT

### Before Cleanup
```
/home/user/jj-bot/ (8.0M)
└── jj-bot/ (7.0M)
    ├── jj-bot/ (1.9M) ← ACTIVE
    ├── jj-bot-stable/ (3.7M) ← DELETE
    └── jj-bot-backups/ (1.6M) ← DELETE
```

### After Cleanup
```
/home/user/jj-bot/ (2.0M - 75% reduction!)
├── glue/
├── services/
├── dashboard/
├── modules/
├── data/
├── docs/
├── tests/
├── setup_windows.bat
├── start_all.bat
├── stop_all.bat
├── requirements.txt
└── README.md
```

---

## ⚠️ RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Accidentally delete active code | CRITICAL | Safety tag before cleanup |
| Break path imports | HIGH | Test after each move |
| Lose important docs | MEDIUM | Review docs before deleting |
| Git confusion | LOW | Use separate commit for each phase |

---

## ✅ SUCCESS CRITERIA

- [ ] No more nested jj-bot folders
- [ ] All active code at repository root
- [ ] Windows batch scripts work from root
- [ ] All backup folders deleted
- [ ] All .backup/.bak files deleted
- [ ] All Linux scripts deleted
- [ ] File size reduced by ~75%
- [ ] Clear, flat directory structure
- [ ] All tests pass
- [ ] Documentation updated

---

**Ready to execute? Approve this plan and I'll run it step by step.**
