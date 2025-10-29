# DDEV Git Tracking Reference

## What's Version Controlled ✅

These files ARE committed to Git and shared with team:

```
carpart-scraper-wp/
├── .ddev/
│   ├── config.yaml              ✅ Version controlled (team needs this)
│   ├── README.md                ✅ Version controlled (documentation)
│   └── GIT_TRACKING.md          ✅ Version controlled (this file)
├── admin/                       ✅ Plugin source code
├── blocks/                      ✅ Plugin source code
├── includes/                    ✅ Plugin source code
├── test-data/                   ✅ Test data for imports
├── csf-parts-catalog.php        ✅ Plugin entry point
└── package.json                 ✅ Build configuration
```

## What's NOT Version Controlled ❌

These are generated/downloaded by DDEV and gitignored:

```
carpart-scraper-wp/
├── wordpress/                   ❌ WordPress core (DDEV downloads)
│   ├── wp-admin/
│   ├── wp-content/
│   │   ├── plugins/
│   │   │   ├── akismet/         ❌ Default plugins
│   │   │   └── csf-parts-catalog/  ❌ Symlink to plugin root
│   │   ├── themes/              ❌ Default themes
│   │   └── uploads/             ❌ User uploads
│   ├── wp-config.php            ❌ Auto-generated config
│   └── ...                      ❌ All WordPress core
├── .ddev/
│   ├── .homeadditions/          ❌ DDEV runtime
│   ├── .gitignore               ❌ DDEV auto-generated
│   ├── db_snapshots/            ❌ Database backups
│   ├── .ddev-docker-*           ❌ DDEV temp files
│   └── traefik/                 ❌ DDEV routing
└── node_modules/                ❌ npm dependencies
```

## Why This Structure?

### ✅ Version Controlled

**Plugin Source Code**
- Your team needs the actual plugin code
- Changes tracked in Git history
- Code reviews possible

**DDEV Config**
- Team gets identical development environment
- One `ddev start` command for everyone
- Infrastructure as Code

**Test Data**
- Consistent testing across team
- Example data for imports
- Documentation by example

### ❌ Not Version Controlled

**WordPress Core**
- Downloaded fresh by DDEV (consistent versions)
- Saves 50+ MB per clone
- Easy to update (`ddev wp core update`)

**Database/Uploads**
- User-generated content (not source code)
- Can be large (GBs)
- Use `ddev snapshot` for local backups

**DDEV Runtime**
- Auto-generated per environment
- Specific to each developer's machine
- Recreated automatically

## Team Workflow

### Developer 1 (You)

```bash
# Setup DDEV
cd carpart-scraper-wp
ddev start
ddev wp core download
ddev wp core install ...

# Work on plugin
vim includes/class-something.php
git add includes/
git commit -m "Add new feature"
git push
```

### Developer 2 (Teammate)

```bash
# Clone repo
git clone <repo>
cd carpart-scraper/carpart-scraper-wp

# DDEV config is already there! Just start:
ddev start
ddev wp core download
ddev wp core install ...

# Plugin code is already there (from Git)
# Start working immediately!
```

## Quick Checks

### Verify Git Ignores

```bash
# Should show ONLY plugin files, not wordpress/
git status

# Expected output:
# On branch main
# Untracked files:
#   .ddev/config.yaml
#   .ddev/README.md
#   admin/
#   blocks/
#   includes/
```

### Verify DDEV Setup

```bash
# This directory should exist but NOT be in Git
ls wordpress/

# This should be a symlink
ls -la wordpress/wp-content/plugins/csf-parts-catalog
# -> points to /var/www/html (plugin root inside container)
```

## Troubleshooting

### "WordPress directory committed to Git"

```bash
# Remove from Git tracking (keeps local files)
git rm -r --cached wordpress/
git commit -m "Remove WordPress core from Git"

# Re-download clean copy
rm -rf wordpress/
ddev wp core download
```

### "Teammate can't start DDEV"

Make sure they have:
1. `.ddev/config.yaml` (from Git)
2. Docker Desktop running
3. DDEV installed (`brew install ddev/ddev/ddev`)

Then:
```bash
ddev start
```

## Summary

| Item | In Git? | Why? |
|------|---------|------|
| Plugin source | ✅ Yes | Your code |
| DDEV config | ✅ Yes | Team environment |
| Test data | ✅ Yes | Consistent testing |
| WordPress core | ❌ No | Downloaded by DDEV |
| Database | ❌ No | User content |
| Uploads | ❌ No | User files |
| DDEV runtime | ❌ No | Auto-generated |

**Golden Rule**: Version control SOURCE CODE and CONFIGURATION, not GENERATED FILES or DOWNLOADS.
