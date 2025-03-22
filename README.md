# VPChron

VPChron is a powerful utility for backing up and restoring AWS VPC configurations. This tool allows you to:

1. **Backup** entire VPC configurations to S3, including all associated resources
2. **Restore** VPCs from previous backups for disaster recovery or environment replication
3. **List** available backups in your S3 bucket with timestamps

## Installation

1. Save the script as `vpchron.py`:

2. Install required dependencies:
   ```
   pip install boto3 pyyaml
   ```


## AWS Credentials

TimelessVPC uses the AWS SDK for Python (boto3) and supports all standard AWS authentication methods:

- Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- AWS credentials file (~/.aws/credentials)
- IAM instance profiles (when running on EC2)

You can also specify profiles using the `--profile` option.

## Required AWS Permissions

The IAM user or role running TimelessVPC needs the following permissions:

- EC2 read permissions (describe resources)
- S3 read/write permissions for the backup bucket
- EC2 create permissions for restore operations

## Usage Examples

### Setup S3 Bucket

First, create an S3 bucket to store your VPC backups:

```
aws s3 mb s3://your-vpc-backup-bucket
```

### Backing Up VPCs

Backup all VPCs in the default region:

```
./vpchron.py backup --bucket your-vpc-backup-bucket
```

Backup VPCs in a specific region:

```
./vpchron.py backup --region us-west-2 --bucket your-vpc-backup-bucket
```

Using a specific AWS profile:

```
./vpchron.py backup --profile production --bucket your-vpc-backup-bucket
```

### Listing Available Backups

List all available backups in your S3 bucket:

```
./vpchron.py list --bucket your-vpc-backup-bucket
```

### Restoring from Backup

Restore the most recent backup:

```
./vpchron.py restore --bucket your-vpc-backup-bucket
```

Restore a specific backup by timestamp:

```
./vpchron.py restore --bucket your-vpc-backup-bucket --timestamp 2025-03-22-10-45-30
```

Restore a specific VPC from a backup:

```
./vpchron.py restore --bucket your-vpc-backup-bucket --vpc-id vpc-0abc123def456789
```

### Coming Soon

- Incremental Backups: Only backup what's changed since last backup
- VPC Flow Logs Support: Include VPC Flow Logs in backups
- Resource Dependency Tracking: Support for Lambda functions, EC2 instances, and other VPC-dependent resources
- Elastic IP Preservation: Maintain IP address reservations during restoration
- Cross-Account Restoration: Restore configurations across AWS accounts
- Backup Scheduling: Automated regular backups

### Contributing
Contributions are welcome! Please feel free to submit a Pull Request.