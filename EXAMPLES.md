# Usage Examples

This document provides practical examples of using the Confluence Export-Import Tool for common scenarios.

## Basic Workflow Examples

### Example 1: First-Time Setup and Export

This example shows a complete workflow from setup to export:

```bash
# Step 1: Create configuration file
confluence-tool config create

# Step 2: Edit config.yaml with your details
# (Use your favorite text editor to edit the file)

# Step 3: Test your configuration
confluence-tool config validate

# Step 4: List available spaces to see what you can export
confluence-tool list-spaces

# Step 5: Export a space (will prompt for space selection)
confluence-tool export

# Step 6: Check the export results in the exports/ directory
```

### Example 2: Export Specific Space to Custom Directory

```bash
# Export a specific space by key to a custom directory
confluence-tool export --space "MYPROJECT" --output "/backup/confluence"
```

### Example 3: Import with Different Conflict Resolution

First, edit your `config.yaml` to set the conflict resolution strategy:

```yaml
import:
  conflict_resolution: "overwrite"  # Options: skip, overwrite, rename
  create_missing_parents: true
  import_attachments: true
```

Then import:

```bash
# Import to a specific target space
confluence-tool import "/backup/confluence/MYPROJECT_20231201_143022" --space "NEWPROJECT"
```

## Advanced Configuration Examples

### Example 1: High-Performance Configuration

For large spaces or fast networks, use this configuration:

```yaml
confluence:
  base_url: "https://yourcompany.atlassian.net"
  auth:
    username: "admin@yourcompany.com"
    api_token: "your-api-token"

export:
  output_directory: "/fast-ssd/confluence-exports"
  format:
    html: true
    attachments: true
    comments: false    # Skip comments for faster export
    versions: false    # Skip versions for faster export

general:
  max_workers: 10      # Increase concurrent operations
  timeout: 60          # Longer timeout for large files
  rate_limit: 20       # Higher rate limit if your instance supports it

logging:
  level: "INFO"
  file: "/var/log/confluence-tool.log"
```

### Example 2: Conservative Configuration

For slower networks or rate-limited instances:

```yaml
confluence:
  base_url: "https://yourcompany.atlassian.net"
  auth:
    username: "user@yourcompany.com"
    api_token: "your-api-token"

general:
  max_workers: 2       # Fewer concurrent operations
  timeout: 120         # Longer timeout for slow connections
  rate_limit: 5        # Lower rate limit to avoid throttling
  retry:
    max_attempts: 5    # More retry attempts
    backoff_factor: 3  # Longer waits between retries
```

### Example 3: Detailed Logging Configuration

For debugging or audit purposes:

```yaml
logging:
  level: "DEBUG"
  file: "confluence-audit.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
```

## Real-World Scenarios

### Scenario 1: Migrating Between Confluence Instances

**Goal**: Move a space from one Confluence instance to another.

1. **Export from source instance**:
   ```yaml
   # config-source.yaml
   confluence:
     base_url: "https://old-instance.atlassian.net"
     auth:
       username: "migration@company.com"
       api_token: "source-api-token"
   ```

   ```bash
   confluence-tool --config config-source.yaml export --space "PROJECT"
   ```

2. **Import to target instance**:
   ```yaml
   # config-target.yaml
   confluence:
     base_url: "https://new-instance.atlassian.net"
     auth:
       username: "migration@company.com"
       api_token: "target-api-token"
   ```

   ```bash
   confluence-tool --config config-target.yaml import "./exports/PROJECT_20231201_143022" --space "PROJECT"
   ```

### Scenario 1b: Migration with Space Key Remapping

**Goal**: Migrate a space but use a different space key in the target instance (for space key conflicts or organizational reasons).

1. **Export from source**:
   ```bash
   confluence-tool --config config-source.yaml export --space "DOCS"
   ```

2. **Import with space key remapping**:
   ```bash
   confluence-tool --config config-target.yaml import "./exports/DOCS_20251002_123456" \
     --remap-space-key DOCS:DOCS-PROD \
     --create-space \
     --new-space-key DOCS-PROD \
     --space-name "Production Documentation"
   ```

   This will:
   - Create a new space with key "DOCS-PROD"
   - Automatically rewrite all internal links from "DOCS" to "DOCS-PROD"
   - Maintain link integrity throughout the imported content

### Scenario 1c: Confluence Cloud Space Key Bug Workaround

**Goal**: Import a space that was previously deleted, but Confluence Cloud won't allow recreating with the same key.

**Background**: Confluence Cloud has a known issue where deleted space keys are retained and cannot be reused.

**Solution**:
```bash
# Export the space (from backup or another instance)
confluence-tool export --space "KB"

# Import with a modified space key
confluence-tool import ./exports/KB_20251002_123456 \
  --remap-space-key KB:KB2 \
  --create-space \
  --new-space-key KB2 \
  --space-name "Knowledge Base"
```

The `--remap-space-key` option will automatically rewrite all internal references from "KB" to "KB2", including:
- Confluence XML links
- Wiki-style links  
- HTML anchor URLs
- Macro space references
- Attachment references

### Scenario 2: Regular Backup Automation

**Goal**: Create automated daily backups of critical spaces.

Create a backup script (`backup-confluence.sh`):

```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/backups/confluence/$(date +%Y-%m-%d)"
SPACES=("CRITICAL" "DOCS" "POLICIES")
CONFIG_FILE="/etc/confluence-tool/backup-config.yaml"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Export each space
for space in "${SPACES[@]}"; do
    echo "Backing up space: $space"
    confluence-tool --config "$CONFIG_FILE" export \
        --space "$space" \
        --output "$BACKUP_DIR" || {
        echo "Failed to backup $space" >&2
    }
done

# Clean up old backups (keep last 30 days)
find /backups/confluence -type d -mtime +30 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
```

### Scenario 3: Content Audit and Review

**Goal**: Export spaces for content review without importing.

Configuration for audit export:

```yaml
export:
  output_directory: "/audit/confluence"
  format:
    html: true
    attachments: false   # Skip attachments for audit
    comments: true       # Include comments for review
    versions: true       # Include history for audit trail
  naming:
    include_page_id: true    # Include IDs for tracking
    include_space_key: true
```

Export command:
```bash
# Export all spaces for audit (script to loop through all spaces)
confluence-tool list-spaces | grep -E "^[0-9]+" | while read -r num key name type desc; do
    echo "Auditing space: $key"
    confluence-tool export --space "$key" --output "/audit/confluence/$(date +%Y-%m-%d)"
done
```

### Scenario 4: Recovering from Failed Import

**Goal**: Clean a partially imported space and retry the import.

This scenario is common when:
- Import fails due to attachment errors
- Network issues interrupt the import
- Need to retry with different settings

**Step 1: Preview what would be deleted**
```bash
confluence-tool clean-space KB --dry-run

# For multi-environment setup, specify target config
confluence-tool clean-space KB --dry-run --target-config staging-config.yaml
```

This shows all pages that would be deleted without actually deleting them.

**Step 2: Clean the space**
```bash
confluence-tool clean-space KB

# For multi-environment setup
confluence-tool clean-space KB --target-config staging-config.yaml
```

The tool will:
- Display all pages to be deleted
- Ask for confirmation (Yes/No)
- Require typing "I CONFIRM" as final confirmation
- Show progress bar during deletion
- Provide a summary report

**Step 3: Retry the import with adjusted settings**
```bash
# If attachments were the issue, disable them temporarily
confluence-tool import ./exports/KB_20240115 --space KB --target-config adjusted-config.yaml
```

**adjusted-config.yaml** example:
```yaml
confluence:
  base_url: "https://yourcompany.atlassian.net"
  auth:
    username: "your-email@example.com"
    api_token: "your-token"

import:
  import_attachments: false  # Disable if attachments caused failure
  conflict_resolution: "overwrite"

general:
  timeout: 300  # Increase timeout
  retry:
    max_attempts: 5
```

**Important Safety Notes**:
- Always use `--dry-run` first to preview
- The clean-space operation cannot be undone
- Make sure you have a backup before cleaning
- Consider using `--conflict-resolution skip` instead if you only want to add missing pages

## Troubleshooting Examples

### Example 1: Handling Large Attachments

If you encounter timeouts with large attachments:

```yaml
general:
  timeout: 300         # 5 minutes for large files
  max_workers: 2       # Reduce concurrent downloads
```

### Example 2: Debugging Connection Issues

Enable detailed logging to troubleshoot connection problems:

```bash
# Run with maximum verbosity
confluence-tool --verbose config validate

# Or check logs with debug level
confluence-tool --config debug-config.yaml list-spaces
```

Debug configuration:
```yaml
logging:
  level: "DEBUG"
  file: "debug.log"

general:
  timeout: 10          # Short timeout to fail fast
  retry:
    max_attempts: 1    # Don't retry for debugging
```

### Example 3: Handling Rate Limiting

If you're being rate limited:

```yaml
general:
  rate_limit: 2        # Very conservative rate
  retry:
    max_attempts: 10   # More retries
    backoff_factor: 5  # Longer backoff
```

## Integration Examples

### Example 1: Jenkins CI/CD Pipeline

```groovy
pipeline {
    agent any
    
    stages {
        stage('Backup Confluence') {
            steps {
                script {
                    sh '''
                        confluence-tool --config /jenkins/confluence-config.yaml \
                            export --space "DOCS" --output "${WORKSPACE}/backup"
                    '''
                }
                archiveArtifacts artifacts: 'backup/**/*', fingerprint: true
            }
        }
    }
}
```

### Example 2: Docker Usage

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN pip install -e .

CMD ["confluence-tool", "help-guide"]
```

Build and run:
```bash
docker build -t confluence-tool .
docker run -v $(pwd)/config.yaml:/app/config.yaml -v $(pwd)/exports:/app/exports confluence-tool export
```

### Example 3: Cron Job for Regular Backups

Add to crontab (`crontab -e`):

```cron
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/confluence-tool --config /etc/confluence-backup.yaml export --space "CRITICAL" --output /backups/daily

# Weekly full backup on Sundays at 1 AM
0 1 * * 0 /home/user/scripts/backup-all-spaces.sh
```

## Tips and Best Practices

1. **Test with small spaces first** before backing up large spaces
2. **Use --verbose flag** when troubleshooting
3. **Monitor disk space** when exporting large spaces with attachments
4. **Set appropriate timeouts** based on your network and space size
5. **Use API tokens** instead of passwords for better security
6. **Keep configuration files secure** and don't commit them to version control
7. **Regularly test your backups** by doing test imports
8. **Document your backup procedures** for your team

## Performance Optimization

### For Large Spaces (1000+ pages)

```yaml
general:
  max_workers: 8       # Increase parallelism
  timeout: 180         # Longer timeout
  rate_limit: 15       # Higher rate if allowed

export:
  format:
    versions: false    # Skip versions to save time and space
```

### For Slow Networks

```yaml
general:
  max_workers: 2       # Reduce concurrent requests
  timeout: 300         # Much longer timeout
  rate_limit: 3        # Conservative rate limiting
  retry:
    max_attempts: 5
    backoff_factor: 3
```