# JJ-Bot: Babylon + Buffett Integration Init

Copy everything below the line and paste it into your Claude Code session:

---

## INIT PROMPT (Copy from here)

```
[BABYLON-BUFFETT MODULE INIT]

Context: I'm integrating a profit-harvesting capital management system into JJ-Bot. This was designed in a Claude.ai session and needs to plug into the existing Glue Layer.

Full spec is in: docs/babylon-buffett-spec.md

QUICK SUMMARY:

System: "Babylon + Buffett" — systematic profit harvesting into hard assets

Parameters:
- Initial Capital: $10,000
- Deployment Trigger: $1,000 (10% of capital)
- Hard Assets: 50% BTC / 50% MNT (Gold) via Wealthsimple

Phase 1 - Harvest Rules (per position):
- +20% gain → Sell 25% → Harvest Account
- +50% gain → Sell 25% → Harvest Account  
- +100% gain → Sell 25% → Harvest Account
- Remaining 25% rides forever as "free shares"

Phase 2 - Accumulation:
- Harvest proceeds flow to dedicated Harvest Account
- Track running balance toward $1K trigger

Phase 3 - Deployment:
- When Harvest Account hits $1,000 → Deploy cycle activates
- $500 → BTC (Wealthsimple Crypto)
- $500 → MNT (Wealthsimple Trade)
- Reset and repeat

Integration Target:
- Extends Glue Layer as capital_management/ submodule
- Hooks into position update events
- Exposes /harvest and /deployment API endpoints

Automation Level: Semi-auto (alerts on triggers, user confirms)

Please read docs/babylon-buffett-spec.md for full details including data models, API endpoints, and storage schemas.

Ready to implement. What's the current state of the Glue Layer?

[END INIT]
```

---

## USAGE

1. Open your JJ-Bot project in Claude Code
2. Paste the init prompt above
3. Claude Code will have full context of the Babylon system
4. Point it to the spec file for detailed reference

## FILE PLACEMENT

Put `babylon-buffett-spec.md` in your project:

```
jj-bot/
├── docs/
│   ├── babylon-buffett-spec.md   ← Drop here
│   └── ...
├── glue/
│   └── ...
└── ...
```

Then Claude Code can reference it anytime with:
```
view docs/babylon-buffett-spec.md
```
