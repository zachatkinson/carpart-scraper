# DDEV WordPress Development Environment

This directory contains DDEV configuration for local WordPress development with the CSF Parts Catalog plugin.

## Prerequisites

- **Docker Desktop** - Must be running
- **DDEV** - Install via Homebrew (Mac) or package manager

### Install DDEV (Mac)

```bash
brew install ddev/ddev/ddev
```

For other platforms, see: https://ddev.readthedocs.io/en/stable/users/install/

## Quick Start

```bash
# 1. Start DDEV (from carpart-scraper-wp directory)
ddev start

# 2. Download and install WordPress
ddev wp core download
ddev wp core install \
  --url=https://csf-parts-catalog.ddev.site \
  --title="CSF Parts Catalog Dev" \
  --admin_user=admin \
  --admin_password=admin \
  --admin_email=admin@example.com

# 3. Activate the plugin
ddev wp plugin activate csf-parts-catalog

# 4. Open in browser
ddev launch
```

## Access Points

After running `ddev start`, you can access:

- **WordPress Site**: https://csf-parts-catalog.ddev.site
- **WordPress Admin**: https://csf-parts-catalog.ddev.site/wp-admin
  - Username: `admin`
  - Password: `admin`
- **PHPMyAdmin**: https://csf-parts-catalog.ddev.site:8037
- **Mailhog** (email testing): https://csf-parts-catalog.ddev.site:8026

## Useful Commands

### WordPress Management

```bash
# WP-CLI commands
ddev wp plugin list
ddev wp theme list
ddev wp user list

# Update WordPress
ddev wp core update

# Clear cache
ddev wp cache flush
```

### Database Operations

```bash
# Access MySQL CLI
ddev mysql

# Import database
ddev import-db backup.sql.gz

# Export database
ddev export-db --gzip=false > backup.sql

# Create snapshot (for quick rollback)
ddev snapshot
ddev snapshot restore --latest
```

### Development Workflow

```bash
# SSH into container
ddev ssh

# View logs
ddev logs

# Restart services
ddev restart

# Stop environment (preserves data)
ddev stop

# Delete everything (careful!)
ddev delete -y
```

### Building Gutenberg Blocks

```bash
# Install npm dependencies (from host)
cd blocks/single-product
npm install
npm run build

# Or use DDEV's Node.js
ddev npm install
ddev npm run build
```

### Debugging

```bash
# Enable Xdebug
ddev xdebug on

# Disable Xdebug (faster)
ddev xdebug off

# View WordPress debug log
ddev logs | grep "PHP"
```

## Project Structure

```
carpart-scraper-wp/
├── .ddev/                    # DDEV configuration (version controlled)
│   ├── config.yaml          # Main DDEV config
│   └── README.md            # This file
├── wordpress/               # WordPress core (NOT in Git, DDEV installs this)
│   ├── wp-admin/
│   ├── wp-content/
│   │   └── plugins/
│   │       └── csf-parts-catalog/  # Symlink to plugin root
│   └── wp-config.php
├── admin/                   # Plugin files (version controlled)
├── blocks/
├── includes/
├── test-data/
└── csf-parts-catalog.php
```

## Testing the Import System

```bash
# 1. Make sure WordPress is running
ddev wp plugin activate csf-parts-catalog

# 2. Open admin
ddev launch wp-admin

# 3. Navigate to: CSF Parts → Import
# 4. Upload: test-data/sample-import.json
# 5. Click "Start Import"
# 6. Verify: CSF Parts → All Parts (should show 8 parts)
```

## Troubleshooting

### DDEV won't start

```bash
# Check Docker is running
docker ps

# Restart DDEV
ddev restart

# Rebuild containers
ddev restart --rebuild
```

### Plugin not appearing

```bash
# Check symlink exists
ddev ssh
ls -la /var/www/html/wordpress/wp-content/plugins/

# Recreate symlink manually if needed
cd /var/www/html/wordpress/wp-content/plugins
ln -sf ../../../../ csf-parts-catalog
```

### Database issues

```bash
# Drop and recreate
ddev delete -y
ddev start
# Reinstall WordPress
```

### Port conflicts

```bash
# Check what's using ports
lsof -i :80
lsof -i :443

# Change DDEV ports in config.yaml:
# router_http_port: "8080"
# router_https_port: "8443"
```

## Performance Tips

1. **Disable Xdebug when not debugging** (it's slow)
   ```bash
   ddev xdebug off
   ```

2. **Use NFS mounts** (Mac/Linux) for better file I/O
   ```bash
   ddev config --nfs-mount-enabled
   ```

3. **Allocate more resources to Docker Desktop**
   - Docker Desktop → Preferences → Resources
   - Increase CPUs and Memory

## Environment Variables

WordPress environment variables are set in `.ddev/config.yaml`:

- `WP_ENVIRONMENT_TYPE=local`
- `WP_DEBUG=true`
- `WP_DEBUG_LOG=true`
- `WP_DEBUG_DISPLAY=false`

Debug logs appear in: `wordpress/wp-content/debug.log`

## Sharing with Team

Your teammates can clone and run:

```bash
git clone <repo>
cd carpart-scraper-wp
ddev start
ddev wp core download
ddev wp core install ... # (same as above)
```

Everyone gets an identical environment!

## Advanced: Custom Docker Configuration

Create `.ddev/docker-compose.custom.yaml` for custom services (e.g., Redis, Elasticsearch).

See: https://ddev.readthedocs.io/en/stable/users/extend/custom-compose-files/

## Resources

- **DDEV Docs**: https://ddev.readthedocs.io/
- **WP-CLI Docs**: https://wp-cli.org/
- **WordPress Developer Handbook**: https://developer.wordpress.org/

## Cleanup

```bash
# Stop and remove containers (keeps database)
ddev stop

# Delete everything (careful!)
ddev delete -y

# Remove DDEV's global database snapshots
ddev snapshot --cleanup
```

---

**Last Updated**: 2025-10-28
**DDEV Version**: 1.22+
**WordPress Version**: 6.4+
