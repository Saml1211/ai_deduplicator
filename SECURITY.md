# Security Considerations for AI Deduplicator

This document outlines important security considerations for using the AI Deduplicator tool, with a focus on transaction log file handling and sensitive path disclosure.

## Overview

The AI Deduplicator creates and maintains several files that contain file system paths from your system:
- Transaction logs (`.dedup_transaction.json`)
- Deduplication reports (`ai_deduplication_report.json`, `deduplication_report.json`)
- Log files (`ai_deduplication.log`, `deduplication.log`)

These files may contain:
- Full file paths from your system
- Directory structure information
- File metadata (sizes, modification times, hashes)
- Operational details about your files

While the tool does not intentionally collect sensitive file content, the paths themselves can reveal information about your system structure, projects, and organizational patterns.

## Transaction Log Security

### What Is Stored in Transaction Logs

The transaction log (`.dedup_transaction.json`) is created before any file operations are executed and contains:
- **Full file paths**: Both source and destination paths for move operations
- **Operation details**: Type of operation (move/remove) and timestamps
- **Completion status**: Whether operations were completed or rolled back

Example transaction log structure:
```json
{
  "timestamp": "2024-11-18T10:30:45.123456",
  "operations": [
    {
      "action": "move",
      "file": "/Users/username/Documents/file.txt",
      "destination": "/Users/username/Documents/Archive/file.txt"
    },
    {
      "action": "remove",
      "file": "/Users/username/Downloads/duplicate.txt",
      "reason": "duplicate"
    }
  ],
  "completed": true
}
```

### File Permissions (Critical)

Transaction log files contain sensitive path information and should be protected from unauthorized access:

#### Recommended Permissions
```bash
# Set restrictive permissions on transaction log
chmod 600 .dedup_transaction.json

# Verify permissions
ls -la .dedup_transaction.json
# Should show: -rw------- (read/write for owner only)
```

#### Why Restrictive Permissions Matter
- **Prevents Information Disclosure**: Only the file owner can read the paths and operations
- **Protects System Structure**: Prevents other users from learning about your directory structure
- **Compliance**: Required for security-conscious environments (development teams, enterprises)

#### For Multi-User Systems
On systems with multiple users, ensure:
1. Transaction logs are created with `600` permissions (owner read/write only)
2. Parent directories have appropriate permissions (`drwx------` or `drwxr-x---`)
3. Regularly audit file permissions: `find . -name ".dedup_transaction.json" -ls`

### Handling Multiple Transaction Logs

When multiple operations are performed:
- Only one transaction log exists at a time: `.dedup_transaction.json`
- Previous transaction logs are archived with rollback status: `.dedup_transaction.json.rolled_back_YYYYMMDD_HHMMSS`
- Archive old transaction logs when sensitive projects are completed:
  ```bash
  # Securely delete old transaction logs after operations are verified
  rm .dedup_transaction.json.rolled_back_*
  # Or use shred for secure deletion (macOS/Linux)
  shred -vfz .dedup_transaction.json.rolled_back_*
  ```

## Path Handling Recommendations

### Absolute vs Relative Paths

**Current Implementation**: The tool uses absolute file paths in transaction logs and reports.

**Why Absolute Paths Are Used**:
- Enables reliable rollback operations regardless of working directory
- Prevents ambiguity when files have been moved
- Works correctly with the archive system
- Supports operations across different directories

**Security Implications**:
- Absolute paths reveal complete directory structure
- Paths may contain usernames and home directory names
- Directory organization patterns are visible

**Mitigation Strategies**:

1. **Path Sanitization in Logs** (if using logging in untrusted environments):
   ```python
   # Example: Replace sensitive home directory with placeholder
   sanitized_path = filepath.replace(os.path.expanduser("~"), "~")
   logging.info(f"Processing {sanitized_path}")
   ```

2. **Selective Log Viewing**:
   - Restrict who can read log files
   - Use `head -c 1000` instead of `cat` to preview logs without full details
   - Share logs selectively and only when necessary

3. **Environment-Specific Configuration**:
   - Use `.deduplication_config.json` to specify when and where logs are created
   - Disable detailed logging in untrusted environments
   - Enable verbose logging only in secure, development environments

### Archive Directory Security

The archive directory (`.dedup-deleted/`) also requires protection:

```bash
# Set restrictive permissions on archive directory
chmod 700 .dedup-deleted/

# Verify archive permissions
ls -la .dedup-deleted
# Should show: drwx------ (read/write/execute for owner only)
```

**Important**: Archive directories may contain sensitive files that were deduplicated. Treat them with the same security level as live data.

## Best Practices for Secure Operation

### 1. Run in Secure Environment
- Execute the tool only in private, trusted directories
- Avoid running in shared or multi-user systems without careful consideration
- Use dry-run mode (`--dry-run`) to verify operations before execution

### 2. Manage Operational Artifacts
```bash
# After successful deduplication:

# 1. Review the transaction log (before rollback)
cat .dedup_transaction.json | jq '.' # if jq is available
less .dedup_transaction.json

# 2. If satisfied with results, optionally archive the transaction log
mv .dedup_transaction.json .dedup_transaction.json.archive_$(date +%Y%m%d)

# 3. Securely delete old transaction logs when no longer needed
# On macOS/Linux:
find . -name ".dedup_transaction.json.*" -exec shred -vfz {} \;

# 4. Clean up old archive directories when restores are no longer needed
rm -rf .dedup-deleted  # After verifying no recovery is needed
```

### 3. Protect Configuration Files
```bash
# .deduplication_config.json may contain API keys or custom settings
chmod 600 .deduplication_config.json

# Never commit to version control
echo ".deduplication_config.json" >> .gitignore
```

### 4. Audit Logging
Enable audit logging in secure environments:
```bash
# Keep detailed logs for compliance/recovery purposes
# But ensure logs are stored securely
chmod 600 ai_deduplication.log
chmod 600 deduplication.log
```

### 5. Version Control Considerations
**IMPORTANT**: Never commit transaction logs or detailed reports to version control:

```bash
# Add to .gitignore
cat >> .gitignore << 'EOF'
.dedup_transaction.json*
.dedup_transaction.json.rolled_back_*
ai_deduplication_report.json
deduplication_report.json
ai_deduplication.log
deduplication.log
.dedup-deleted/
EOF
```

## Compliance and Regulatory Considerations

### GDPR and Data Protection
If handling files containing personal data:
1. **Data Retention**: Transaction logs are operational data. Define retention policies.
2. **Data Minimization**: Consider periodically deleting old logs and archived files
3. **Access Control**: Limit access to logs containing file paths of sensitive data
4. **Documentation**: Maintain records of deduplication operations for audit trails

### Privacy in Shared Environments
- Use unique archive directories per project: `.dedup-deleted-projectname/`
- Separate transaction logs per project for better audit trails
- Consider using relative path tracking for sensitive environments

### Enterprise Deployments
1. **Centralized Logging**: Redirect logs to a secure central logging system
2. **Encryption**: Encrypt transaction logs at rest
3. **Access Control**: Use OS-level ACLs or SELinux policies for access control
4. **Monitoring**: Alert on unexpected deduplication operations
5. **Retention Policies**: Define and enforce log retention schedules

## Security Checklist

Before using AI Deduplicator in production or sensitive environments:

- [ ] Reviewed this SECURITY.md document
- [ ] Tested with `--dry-run` mode first
- [ ] Set transaction log permissions to 600: `chmod 600 .dedup_transaction.json`
- [ ] Set archive directory permissions to 700: `chmod 700 .dedup-deleted`
- [ ] Added `.dedup_transaction.json*` to `.gitignore`
- [ ] Added `.dedup-deleted/` to `.gitignore`
- [ ] Reviewed and secured `.deduplication_config.json` if used
- [ ] Established a log retention and deletion policy
- [ ] Determined appropriate log access restrictions
- [ ] For enterprises: Configured centralized logging if required
- [ ] For shared systems: Planned isolation strategy

## Reporting Security Issues

If you discover a security vulnerability in the AI Deduplicator:

1. **Do not** create a public GitHub issue
2. Contact the maintainers privately with details about the vulnerability
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

Security vulnerabilities will be addressed promptly in a coordinated disclosure process.

## Additional Resources

- [Python pathlib Security Considerations](https://docs.python.org/3/library/pathlib.html)
- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [CWE-434: Unrestricted Upload of File with Dangerous Type](https://cwe.mitre.org/data/definitions/434.html)
- [File Permissions Best Practices](https://en.wikipedia.org/wiki/File_system_permissions)

## Version History

- **v1.0** (2024-11-18): Initial security documentation covering transaction log handling and path disclosure risks.
