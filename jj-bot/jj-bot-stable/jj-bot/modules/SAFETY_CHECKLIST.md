# Module Development Safety Checklist

Before EVERY change:
- [ ] Current system backed up
- [ ] Working in /modules/ directory only
- [ ] Not touching /glue/api/main.py
- [ ] Not touching /dashboard/
- [ ] Can rollback if needed

Before connecting module:
- [ ] Module tested standalone
- [ ] Module has health check
- [ ] Fallback plan ready
- [ ] Backup created
