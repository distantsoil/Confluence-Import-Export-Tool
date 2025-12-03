# Multi-Environment Support

The Confluence Export-Import Tool now supports working with multiple Confluence environments, allowing you to export from one environment and import to another, or synchronize content between different instances.

## Overview

This feature enables:

1. **Cross-environment export/import**: Export from one Confluence instance and import to another
2. **Content synchronization**: Keep spaces synchronized between different environments
3. **Environment comparison**: Compare spaces across different Confluence instances
4. **Backup and restore**: Use different environments for backup storage and restoration

## Configuration

### Single Environment (Original Method)

```yaml
# config.yaml
confluence:
  base_url: "https://company.atlassian.net"
  auth:
    username: "user@company.com"
    api_token: "your-api-token"
```

### Multiple Environment Setup

Create separate configuration files for each environment:

**source-config.yaml** (Production environment):
```yaml
confluence:
  base_url: "https://company-prod.atlassian.net"
  auth:
    username: "prod-user@company.com"
    api_token: "prod-api-token"

export:
  output_directory: "./prod-exports"
  format:
    html: true
    attachments: true
    comments: true

general:
  timeout: 60  # Longer timeout for production
  rate_limit: 5  # Conservative rate limiting
```

**target-config.yaml** (Staging/backup environment):
```yaml
confluence:
  base_url: "https://company-staging.atlassian.net"
  auth:
    username: "staging-user@company.com"
    api_token: "staging-api-token"

import:
  conflict_resolution: "overwrite"  # Allow overwriting in staging
  create_missing_parents: true

general:
  timeout: 30
  max_workers: 8  # Can use more workers in staging
```

## Usage Examples

### 1. Cross-Environment Export and Import

**Export from production:**
```bash
confluence-tool export \
  --source-config source-config.yaml \
  --space "CRITICAL-DOCS" \
  --output "./backups"
```

**Import to staging (Method 1: Using --target-config flag):**
```bash
confluence-tool import \
  --target-config target-config.yaml \
  "./backups/CRITICAL-DOCS_20231201_143022" \
  --space "CRITICAL-DOCS-BACKUP"
```

**Import to staging (Method 2: Interactive setup):**
```bash
confluence-tool import "./backups/CRITICAL-DOCS_20231201_143022"
```

When you don't specify `--target-config`, the tool will interactively ask:
1. Do you want to import to a DIFFERENT Confluence environment? [y/N]
2. If yes: Do you already have a target configuration file? [y/N]
3. If no existing config: The tool will guide you through creating a new target configuration

This interactive method is perfect for:
- First-time users who haven't set up multiple configs yet
- Quick imports to different environments
- Learning how to set up multi-environment configurations

### 2. Content Synchronization

**Sync missing pages only (default):**
```bash
confluence-tool sync \
  --source-config source-config.yaml \
  --target-config target-config.yaml \
  --source-space "DOCS" \
  --target-space "DOCS-BACKUP" \
  --mode missing_only
```

**Sync newer pages:**
```bash
confluence-tool sync \
  --source-config source-config.yaml \
  --target-config target-config.yaml \
  --source-space "DOCS" \
  --target-space "DOCS-BACKUP" \
  --mode newer_only
```

**Full synchronization (copy everything):**
```bash
confluence-tool sync \
  --source-config source-config.yaml \
  --target-config target-config.yaml \
  --source-space "DOCS" \
  --target-space "DOCS-BACKUP" \
  --mode full
```

**Dry run (see what would be synced):**
```bash
confluence-tool sync \
  --source-config source-config.yaml \
  --target-config target-config.yaml \
  --source-space "DOCS" \
  --target-space "DOCS-BACKUP" \
  --mode missing_only \
  --dry-run
```

### 3. Space Comparison

**Compare spaces between environments:**
```bash
confluence-tool compare \
  --source-config source-config.yaml \
  --target-config target-config.yaml \
  --source-space "DOCS" \
  --target-space "DOCS-BACKUP" \
  --output "comparison-report"
```

This creates `comparison-report.html` and `comparison-report.json` with detailed analysis.

## Sync Modes

### missing_only (default)
- Copies pages that exist in source but not in target
- Safe option that won't overwrite existing content
- Ideal for keeping environments up-to-date with new content

### newer_only  
- Copies pages that are newer in the source environment
- Compares page modification dates
- Updates target with latest versions while preserving unique content

### full
- Copies all pages from source to target
- Overwrites existing pages in target
- Use with caution as it can overwrite target-specific changes

## Advanced Usage Scenarios

### 1. Disaster Recovery Setup

**Daily backup from production to backup environment:**
```bash
#!/bin/bash
# backup-daily.sh

SPACES=("CRITICAL" "POLICIES" "PROCEDURES")
DATE=$(date +%Y%m%d)

for space in "${SPACES[@]}"; do
    echo "Backing up $space..."
    
    # Export from production
    confluence-tool export \
        --source-config prod-config.yaml \
        --space "$space" \
        --output "/backups/$DATE"
    
    # Import to backup environment
    confluence-tool import \
        --target-config backup-config.yaml \
        "/backups/$DATE/${space}_*" \
        --space "$space"
done
```

### 2. Development to Production Promotion

**Sync approved content from development to production:**
```bash
# Dry run first to see what would be promoted
confluence-tool sync \
  --source-config dev-config.yaml \
  --target-config prod-config.yaml \
  --source-space "APPROVED-DOCS" \
  --target-space "LIVE-DOCS" \
  --mode missing_only \
  --dry-run

# After review, perform actual sync
confluence-tool sync \
  --source-config dev-config.yaml \
  --target-config prod-config.yaml \
  --source-space "APPROVED-DOCS" \
  --target-space "LIVE-DOCS" \
  --mode missing_only
```

### 3. Multi-Site Content Distribution

**Distribute content from headquarters to regional sites:**
```bash
# sites.conf
SITES=("us-west" "us-east" "europe" "asia")
HQ_CONFIG="hq-config.yaml"
SOURCE_SPACE="GLOBAL-POLICIES"

for site in "${SITES[@]}"; do
    echo "Syncing to $site..."
    confluence-tool sync \
        --source-config "$HQ_CONFIG" \
        --target-config "${site}-config.yaml" \
        --source-space "$SOURCE_SPACE" \
        --target-space "$SOURCE_SPACE" \
        --mode newer_only
done
```

## Comparison Reports

The `compare` command generates detailed HTML and JSON reports showing:

- **Statistics**: Page counts, common pages, differences
- **Missing Pages**: Pages that exist in one environment but not the other  
- **Version Differences**: Pages that are newer in source or target
- **Visual Overview**: Color-coded sections for easy analysis

### Report Structure

**HTML Report Features:**
- Executive summary with key statistics
- Detailed lists of pages in each category
- Color-coded sections (missing=red, newer=blue, same=green)
- Clickable sections for easy navigation

**JSON Report Features:**
- Machine-readable format for automation
- Complete page lists for each category
- Timestamps and environment details
- Suitable for integration with other tools

## Security Considerations

### API Token Management
- Use separate API tokens for each environment
- Implement token rotation policies
- Use least-privilege access (read-only for source, write for target)

### Configuration Security
- Store configuration files securely
- Don't commit configs with tokens to version control
- Consider environment variables for sensitive data:

```yaml
confluence:
  base_url: "${CONFLUENCE_URL}"
  auth:
    username: "${CONFLUENCE_USER}"
    api_token: "${CONFLUENCE_TOKEN}"
```

### Network Security
- Use HTTPS for all connections
- Consider VPN access for cross-environment operations
- Implement network restrictions where possible

## Troubleshooting

### Common Issues

**1. Authentication errors across environments**
- Verify each configuration file separately
- Test connections: `confluence-tool config validate --config source-config.yaml`

**2. Rate limiting with multiple environments**
- Reduce `rate_limit` in configurations
- Increase `timeout` for slower connections
- Use fewer `max_workers` for concurrent operations

**3. Sync conflicts**
- Use `--dry-run` first to preview changes
- Choose appropriate sync mode for your use case
- Review comparison reports before syncing

**4. Large space synchronization**
- Sync in smaller batches if needed
- Use `missing_only` mode for initial sync
- Monitor disk space during operations

### Performance Optimization

**For large environments:**
```yaml
general:
  max_workers: 3      # Fewer workers to avoid overwhelming servers
  timeout: 180        # Longer timeout for large operations
  rate_limit: 3       # Conservative rate limiting

export:
  format:
    versions: false   # Skip version history for faster sync
    comments: false   # Skip comments if not needed
```

**For fast networks:**
```yaml
general:
  max_workers: 10     # More concurrent operations
  timeout: 60         # Standard timeout
  rate_limit: 15      # Higher rate limit if supported
```

## Best Practices

1. **Always use dry-run first** for sync operations
2. **Test with small spaces** before syncing large ones
3. **Create comparison reports** to understand differences
4. **Use appropriate sync modes** for your use case
5. **Monitor logs** for errors and performance issues
6. **Backup before major sync operations**
7. **Use separate configs** for clear environment separation
8. **Implement proper access controls** for each environment
9. **Save target configs for reuse** - After using interactive import setup, keep the generated config files for future use
10. **Validate configurations** - Use `confluence-tool config validate --config <file>` to test each config before operations

## Interactive Import Setup

The tool now includes an interactive setup wizard for importing to different environments. This is especially useful when:

- You're new to multi-environment setups
- You need to quickly import to a different instance
- You want to avoid manually creating configuration files

**How it works:**

1. Run import without `--target-config`: `confluence-tool import /path/to/export`
2. Answer the prompts about target environment
3. Either provide an existing config or create a new one interactively
4. The tool saves the config for future reuse

**Example interactive session:**
```
🌍 Multi-Environment Import

You can import to:
  1. The SAME Confluence environment (using your default config.yaml)
  2. A DIFFERENT Confluence environment (using a separate target config)

Do you want to import to a DIFFERENT Confluence environment? [y/N]: y
Do you already have a target configuration file? [y/N]: n

--- Target Confluence Instance ---
Target Confluence URL: https://staging.atlassian.net
Target username/email: staging-user@example.com
Use API token (recommended)? [Y/n]: y
API token: ********

✓ Target configuration created: target-config.yaml
```

## Integration Examples

### Jenkins Pipeline
```groovy
pipeline {
    agent any
    
    stages {
        stage('Sync Documentation') {
            steps {
                script {
                    sh '''
                        confluence-tool sync \
                            --source-config ${WORKSPACE}/configs/dev-config.yaml \
                            --target-config ${WORKSPACE}/configs/staging-config.yaml \
                            --source-space "DEV-DOCS" \
                            --target-space "STAGING-DOCS" \
                            --mode newer_only
                    '''
                }
            }
        }
    }
}
```

### Monitoring Script
```bash
#!/bin/bash
# monitor-sync.sh - Check sync status

confluence-tool compare \
    --source-config prod-config.yaml \
    --target-config backup-config.yaml \
    --source-space "CRITICAL" \
    --target-space "CRITICAL" \
    --output "daily-comparison"

# Check if sync is needed
MISSING=$(grep -o '"only_in_source": \[[^]]*\]' daily-comparison.json | wc -c)

if [ "$MISSING" -gt 20 ]; then
    echo "Sync needed - $MISSING pages missing in backup"
    # Trigger sync or send alert
fi
```

This multi-environment support makes the Confluence Export-Import Tool suitable for enterprise scenarios where content needs to be managed across multiple Confluence instances.