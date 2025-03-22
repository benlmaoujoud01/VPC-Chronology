#!/usr/bin/env python3
import os
import json
import argparse
import datetime
import logging
import boto3
import yaml
import time
import sys
from botocore.exceptions import ClientError

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
def print_banner():
    banner = f"""
{Colors.MAGENTA}██╗   ██╗██████╗  ██████╗██╗  ██╗██████╗  ██████╗ ███╗   ██╗
██║   ██║██╔══██╗██╔════╝██║  ██║██╔══██╗██╔═══██╗████╗  ██║
██║   ██║██████╔╝██║     ███████║██████╔╝██║   ██║██╔██╗ ██║
╚██╗ ██╔╝██╔═══╝ ██║     ██╔══██║██╔══██╗██║   ██║██║╚██╗██║
 ╚████╔╝ ██║     ╚██████╗██║  ██║██║  ██║╚██████╔╝██║ ╚████║
  ╚═══╝  ╚═╝      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝{Colors.RESET}
                                                         
{Colors.WHITE}AWS VPC Configuration Backup and Restore Tool{Colors.RESET}
{Colors.WHITE}Version 1.0.0{Colors.RESET}
"""
    print(banner)
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('timelessvpc')


class VpcBackup:
    """Class to handle VPC configuration backup operations"""
    
    def __init__(self, region=None, profile=None, bucket=None, prefix=None):
        """Initialize the VPC backup with AWS credentials and settings"""
        self.region = region
        self.profile = profile
        self.bucket = bucket
        self.prefix = prefix or 'vpc-backups'
        self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        
        # Initialize AWS session
        session = boto3.Session(profile_name=profile, region_name=region)
        self.ec2 = session.client('ec2')
        self.s3 = session.client('s3')
        
        # Get account ID for naming
        self.account_id = session.client('sts').get_caller_identity()['Account']
        
        logger.info(f"Initialized VPC backup for account {self.account_id} in region {self.region or 'default'}")

    def list_vpcs(self):
        """List all VPCs in the account/region"""
        try:
            response = self.ec2.describe_vpcs()
            return response.get('Vpcs', [])
        except ClientError as e:
            logger.error(f"Error listing VPCs: {e}")
            return []

    def get_vpc_details(self, vpc_id):
        """Get comprehensive details about a specific VPC and its components"""
        vpc_data = {
            'vpc_id': vpc_id,
            'subnets': [],
            'route_tables': [],
            'security_groups': [],
            'network_acls': [],
            'internet_gateways': [],
            'nat_gateways': [],
            'vpc_endpoints': [],
            'vpc_peering_connections': []
        }
        
        # Get basic VPC info
        try:
            vpc_response = self.ec2.describe_vpcs(VpcIds=[vpc_id])
            if vpc_response['Vpcs']:
                vpc_data.update(vpc_response['Vpcs'][0])
        except ClientError as e:
            logger.error(f"Error getting VPC details for {vpc_id}: {e}")
        
        # Get subnets
        try:
            subnet_response = self.ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            vpc_data['subnets'] = subnet_response.get('Subnets', [])
        except ClientError as e:
            logger.error(f"Error getting subnets for VPC {vpc_id}: {e}")
        
        # Get route tables
        try:
            rt_response = self.ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            vpc_data['route_tables'] = rt_response.get('RouteTables', [])
        except ClientError as e:
            logger.error(f"Error getting route tables for VPC {vpc_id}: {e}")
        
        # Get security groups
        try:
            sg_response = self.ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            vpc_data['security_groups'] = sg_response.get('SecurityGroups', [])
        except ClientError as e:
            logger.error(f"Error getting security groups for VPC {vpc_id}: {e}")
        
        # Get NACLs
        try:
            nacl_response = self.ec2.describe_network_acls(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            vpc_data['network_acls'] = nacl_response.get('NetworkAcls', [])
        except ClientError as e:
            logger.error(f"Error getting network ACLs for VPC {vpc_id}: {e}")
        
        # Get Internet Gateways
        try:
            igw_response = self.ec2.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
            )
            vpc_data['internet_gateways'] = igw_response.get('InternetGateways', [])
        except ClientError as e:
            logger.error(f"Error getting internet gateways for VPC {vpc_id}: {e}")
        
        # Get NAT Gateways
        try:
            nat_response = self.ec2.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            vpc_data['nat_gateways'] = nat_response.get('NatGateways', [])
        except ClientError as e:
            logger.error(f"Error getting NAT gateways for VPC {vpc_id}: {e}")
        
        # Get VPC Endpoints
        try:
            endpoints_response = self.ec2.describe_vpc_endpoints(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            vpc_data['vpc_endpoints'] = endpoints_response.get('VpcEndpoints', [])
        except ClientError as e:
            logger.error(f"Error getting VPC endpoints for VPC {vpc_id}: {e}")
        
        # Get VPC Peering Connections
        try:
            peering_response = self.ec2.describe_vpc_peering_connections(
                Filters=[
                    {'Name': 'requester-vpc-info.vpc-id', 'Values': [vpc_id]},
                    {'Name': 'accepter-vpc-info.vpc-id', 'Values': [vpc_id]}
                ]
            )
            vpc_data['vpc_peering_connections'] = peering_response.get('VpcPeeringConnections', [])
        except ClientError as e:
            logger.error(f"Error getting VPC peering connections for VPC {vpc_id}: {e}")
        
        return vpc_data

    def backup_vpc_configuration(self):
        """Backup all VPC configurations in the specified region"""
        vpcs = self.list_vpcs()
        if not vpcs:
            logger.info(f"No VPCs found in region {self.region or 'default'}")
            return False
        
        logger.info(f"Found {len(vpcs)} VPCs to backup")
        
        backup_data = {
            'metadata': {
                'timestamp': self.timestamp,
                'account_id': self.account_id,
                'region': self.region or boto3.session.Session().region_name,
                'vpc_count': len(vpcs)
            },
            'vpcs': {}
        }
        
        # Get detailed configuration for each VPC
        for vpc in vpcs:
            vpc_id = vpc['VpcId']
            logger.info(f"Backing up configuration for VPC {vpc_id}")
            vpc_details = self.get_vpc_details(vpc_id)
            backup_data['vpcs'][vpc_id] = vpc_details
        
        # Save as JSON and YAML for flexibility
        self._save_to_s3(backup_data, 'json')
        self._save_to_s3(backup_data, 'yaml')
        
        return True
    
    def _save_to_s3(self, data, format_type):
        """Save the backup data to S3 in the specified format"""
        if not self.bucket:
            logger.warning("No S3 bucket specified, skipping S3 upload")
            return False
        
        try:
            # Create key with timestamp, account ID, and region for uniqueness
            key = f"{self.prefix}/{self.account_id}/{self.region or 'default'}/{self.timestamp}/vpc_config.{format_type}"
            
            # Convert data to the appropriate format
            if format_type == 'json':
                content = json.dumps(data, indent=2, default=str)  # default=str handles datetime objects
            elif format_type == 'yaml':
                content = yaml.dump(data, default_flow_style=False)
            else:
                logger.error(f"Unsupported format type: {format_type}")
                return False
            
            # Upload to S3
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=f"application/{format_type}",
                Metadata={
                    'Description': f'AWS VPC configuration backup for account {self.account_id}',
                    'CreatedBy': 'TimelessVPC',
                    'Timestamp': self.timestamp
                }
            )
            
            logger.info(f"Successfully uploaded VPC configuration to s3://{self.bucket}/{key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            return False


class VpcRestore:
    """Class to handle VPC restoration from backup"""
    
    def __init__(self, bucket, timestamp=None, vpc_id=None, region=None, profile=None):
        """Initialize the VPC restore process"""
        self.bucket = bucket
        self.timestamp = timestamp
        self.target_vpc_id = vpc_id
        self.region = region
        
        # Initialize AWS session
        session = boto3.Session(profile_name=profile, region_name=region)
        self.s3 = session.client('s3')
        self.ec2 = session.client('ec2')
        self.sts = session.client('sts')
        
        # Get account ID
        self.account_id = self.sts.get_caller_identity()['Account']
        self.current_region = session.region_name
        
        # Created resources mapping (for reference)
        self.created_resources = {
            'vpc': None,
            'subnets': {},
            'route_tables': {},
            'security_groups': {},
            'internet_gateways': {},
            'nat_gateways': {}
        }
        
        logger.info(f"Initialized VPC restore for account {self.account_id} in region {self.current_region}")
    
    def find_latest_backup(self):
        """Find the latest backup for the account/region in S3"""
        prefix = f"vpc-backups/{self.account_id}/{self.region or self.current_region}/"
        
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' not in response or not response['CommonPrefixes']:
                logger.error(f"No backups found with prefix: {prefix}")
                return None
            
            # Get the latest timestamp directory
            latest_prefix = sorted([p['Prefix'] for p in response['CommonPrefixes']])[-1]
            self.timestamp = latest_prefix.split('/')[-2]  # Extract timestamp from path
            logger.info(f"Found latest backup from {self.timestamp}")
            
            return latest_prefix
            
        except ClientError as e:
            logger.error(f"Error finding latest backup: {e}")
            return None
    
    def list_backups(self):
        """List all available backups for the account/region"""
        prefix = f"vpc-backups/{self.account_id}/{self.region or self.current_region}/"
        
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' not in response or not response['CommonPrefixes']:
                logger.info(f"No backups found with prefix: {prefix}")
                return []
            
            # Extract timestamp from each backup directory
            backups = []
            for p in response['CommonPrefixes']:
                timestamp = p['Prefix'].split('/')[-2]
                backups.append({
                    'timestamp': timestamp,
                    'prefix': p['Prefix']
                })
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except ClientError as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def load_backup_data(self):
        """Load VPC configuration data from S3 backup"""
        if not self.timestamp:
            prefix = self.find_latest_backup()
            if not prefix:
                return None
        else:
            prefix = f"vpc-backups/{self.account_id}/{self.region or self.current_region}/{self.timestamp}/"
        
        # Try to load JSON backup first, fallback to YAML
        try:
            s3_key = f"{prefix}vpc_config.json"
            logger.info(f"Loading backup from s3://{self.bucket}/{s3_key}")
            
            response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
            backup_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"Successfully loaded JSON backup from {self.timestamp}")
            
            return backup_data
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Try YAML format as fallback
                try:
                    s3_key = f"{prefix}vpc_config.yaml"
                    logger.info(f"JSON not found, trying YAML: s3://{self.bucket}/{s3_key}")
                    
                    response = self.s3.get_object(Bucket=self.bucket, Key=s3_key)
                    backup_data = yaml.safe_load(response['Body'].read().decode('utf-8'))
                    logger.info(f"Successfully loaded YAML backup from {self.timestamp}")
                    
                    return backup_data
                except ClientError as e2:
                    logger.error(f"Error loading YAML backup: {e2}")
                    return None
            else:
                logger.error(f"Error loading JSON backup: {e}")
                return None
    
    def restore_vpc(self, vpc_data):
        """Restore a VPC from backup data"""
        vpc_id = vpc_data['vpc_id']
        cidr_block = vpc_data.get('CidrBlock')
        
        if not cidr_block:
            logger.error(f"Missing CIDR block for VPC {vpc_id}")
            return None
        
        # Extract tags from the backup
        tags = []
        if 'Tags' in vpc_data:
            tags = vpc_data['Tags']
        
        # Create new VPC
        try:
            logger.info(f"Creating new VPC with CIDR {cidr_block}")
            response = self.ec2.create_vpc(CidrBlock=cidr_block)
            new_vpc_id = response['Vpc']['VpcId']
            
            # Wait for VPC to be available
            self.ec2.get_waiter('vpc_available').wait(VpcIds=[new_vpc_id])
            
            # Apply tags
            if tags:
                tag_specs = []
                for tag in tags:
                    if tag['Key'] != 'aws:cloudformation:stack-name':  # Skip CloudFormation tags
                        tag_specs.append(tag)
                
                if tag_specs:
                    self.ec2.create_tags(Resources=[new_vpc_id], Tags=tag_specs)
            
            # Enable DNS support & hostnames if they were enabled in the original
            if vpc_data.get('EnableDnsSupport', True):
                self.ec2.modify_vpc_attribute(
                    VpcId=new_vpc_id,
                    EnableDnsSupport={'Value': True}
                )
            
            if vpc_data.get('EnableDnsHostnames', False):
                self.ec2.modify_vpc_attribute(
                    VpcId=new_vpc_id,
                    EnableDnsHostnames={'Value': True}
                )
            
            logger.info(f"Successfully created new VPC: {new_vpc_id}")
            self.created_resources['vpc'] = new_vpc_id
            
            return new_vpc_id
            
        except ClientError as e:
            logger.error(f"Error creating VPC: {e}")
            return None
    
    def restore_internet_gateway(self, igw_data, new_vpc_id):
        """Restore Internet Gateway from backup data"""
        if not igw_data:
            return None
            
        try:
            # Create new Internet Gateway
            logger.info("Creating new Internet Gateway")
            response = self.ec2.create_internet_gateway()
            new_igw_id = response['InternetGateway']['InternetGatewayId']
            
            # Apply tags if they exist
            if 'Tags' in igw_data:
                tag_specs = [tag for tag in igw_data['Tags'] 
                            if not tag['Key'].startswith('aws:')]
                if tag_specs:
                    self.ec2.create_tags(Resources=[new_igw_id], Tags=tag_specs)
            
            # Attach to the new VPC
            logger.info(f"Attaching Internet Gateway {new_igw_id} to VPC {new_vpc_id}")
            self.ec2.attach_internet_gateway(
                InternetGatewayId=new_igw_id,
                VpcId=new_vpc_id
            )
            
            self.created_resources['internet_gateways'][new_igw_id] = igw_data
            return new_igw_id
            
        except ClientError as e:
            logger.error(f"Error restoring Internet Gateway: {e}")
            return None
    
    def restore_subnets(self, subnet_data_list, new_vpc_id):
        """Restore subnets from backup data"""
        for subnet_data in subnet_data_list:
            subnet_id = subnet_data.get('SubnetId')
            cidr_block = subnet_data.get('CidrBlock')
            az = subnet_data.get('AvailabilityZone')
            
            if not cidr_block:
                logger.error(f"Missing CIDR block for subnet {subnet_id}")
                continue
                
            try:
                logger.info(f"Creating new subnet with CIDR {cidr_block} in AZ {az}")
                create_args = {
                    'VpcId': new_vpc_id,
                    'CidrBlock': cidr_block
                }
                
                # Add AZ if specified
                if az:
                    create_args['AvailabilityZone'] = az
                
                response = self.ec2.create_subnet(**create_args)
                new_subnet_id = response['Subnet']['SubnetId']
                
                # Apply tags if they exist
                if 'Tags' in subnet_data:
                    tag_specs = [tag for tag in subnet_data['Tags'] 
                                if not tag['Key'].startswith('aws:')]
                    if tag_specs:
                        self.ec2.create_tags(Resources=[new_subnet_id], Tags=tag_specs)
                
                # Set MapPublicIpOnLaunch if it was enabled
                if subnet_data.get('MapPublicIpOnLaunch', False):
                    self.ec2.modify_subnet_attribute(
                        SubnetId=new_subnet_id,
                        MapPublicIpOnLaunch={'Value': True}
                    )
                
                logger.info(f"Created subnet {new_subnet_id}")
                self.created_resources['subnets'][subnet_id] = new_subnet_id
                
            except ClientError as e:
                logger.error(f"Error creating subnet: {e}")
    
    def restore_route_tables(self, rt_data_list, new_vpc_id, igw_id=None):
        """Restore route tables and routes from backup data"""
        for rt_data in rt_data_list:
            rt_id = rt_data.get('RouteTableId')
            
            try:
                logger.info(f"Creating new route table")
                response = self.ec2.create_route_table(VpcId=new_vpc_id)
                new_rt_id = response['RouteTable']['RouteTableId']
                
                # Apply tags if they exist
                if 'Tags' in rt_data:
                    tag_specs = [tag for tag in rt_data['Tags'] 
                                if not tag['Key'].startswith('aws:')]
                    if tag_specs:
                        self.ec2.create_tags(Resources=[new_rt_id], Tags=tag_specs)
                
                # Create routes
                if 'Routes' in rt_data:
                    for route in rt_data['Routes']:
                        # Skip the default local route (automatically created)
                        if route.get('GatewayId') == 'local':
                            continue
                            
                        dest_cidr = route.get('DestinationCidrBlock')
                        if not dest_cidr:
                            continue
                            
                        route_args = {
                            'RouteTableId': new_rt_id,
                            'DestinationCidrBlock': dest_cidr
                        }
                        
                        # Handle internet gateway routes
                        if route.get('GatewayId') and 'igw-' in route.get('GatewayId') and igw_id:
                            route_args['GatewayId'] = igw_id
                            
                            logger.info(f"Creating route to {dest_cidr} via Internet Gateway")
                            try:
                                self.ec2.create_route(**route_args)
                            except ClientError as e:
                                logger.error(f"Error creating route: {e}")
                
                # Associate with subnets
                if 'Associations' in rt_data:
                    for assoc in rt_data['Associations']:
                        if assoc.get('Main'):
                            continue  # Skip main route table association
                            
                        subnet_id = assoc.get('SubnetId')
                        if subnet_id and subnet_id in self.created_resources['subnets']:
                            new_subnet_id = self.created_resources['subnets'][subnet_id]
                            
                            logger.info(f"Associating route table {new_rt_id} with subnet {new_subnet_id}")
                            try:
                                self.ec2.associate_route_table(
                                    RouteTableId=new_rt_id,
                                    SubnetId=new_subnet_id
                                )
                            except ClientError as e:
                                logger.error(f"Error associating route table: {e}")
                
                self.created_resources['route_tables'][rt_id] = new_rt_id
                logger.info(f"Created route table {new_rt_id}")
                
            except ClientError as e:
                logger.error(f"Error creating route table: {e}")
    
    def restore_security_groups(self, sg_data_list, new_vpc_id):
        """Restore security groups from backup data"""
        for sg_data in sg_data_list:
            sg_id = sg_data.get('GroupId')
            sg_name = sg_data.get('GroupName')
            sg_desc = sg_data.get('Description', 'Restored security group')
            
            # Skip default security group
            if sg_name == 'default':
                continue
                
            try:
                logger.info(f"Creating security group {sg_name}")
                response = self.ec2.create_security_group(
                    GroupName=sg_name,
                    Description=sg_desc,
                    VpcId=new_vpc_id
                )
                new_sg_id = response['GroupId']
                
                # Apply tags if they exist
                if 'Tags' in sg_data:
                    tag_specs = [tag for tag in sg_data['Tags'] 
                                if not tag['Key'].startswith('aws:')]
                    if tag_specs:
                        self.ec2.create_tags(Resources=[new_sg_id], Tags=tag_specs)
                
                self.created_resources['security_groups'][sg_id] = new_sg_id
                
            except ClientError as e:
                logger.error(f"Error creating security group: {e}")
                continue
                
        # Second pass to add all the rules (after all groups exist)
        for sg_data in sg_data_list:
            sg_id = sg_data.get('GroupId')
            
            # Skip default or if we failed to create it
            if sg_data.get('GroupName') == 'default' or sg_id not in self.created_resources['security_groups']:
                continue
                
            new_sg_id = self.created_resources['security_groups'][sg_id]
            
            # Add ingress rules
            if 'IpPermissions' in sg_data:
                for rule in sg_data['IpPermissions']:
                    try:
                        # Convert the rule for the API
                        clean_rule = self._clean_sg_rule(rule)
                        if clean_rule:
                            logger.info(f"Adding ingress rule to security group {new_sg_id}")
                            self.ec2.authorize_security_group_ingress(
                                GroupId=new_sg_id,
                                IpPermissions=[clean_rule]
                            )
                    except ClientError as e:
                        # Ignore rule already exists errors
                        if 'InvalidPermission.Duplicate' not in str(e):
                            logger.error(f"Error adding ingress rule: {e}")
            
            # Add egress rules
            if 'IpPermissionsEgress' in sg_data:
                # First, revoke the default egress rule if we're adding specific ones
                try:
                    self.ec2.revoke_security_group_egress(
                        GroupId=new_sg_id,
                        IpPermissions=[{
                            'IpProtocol': '-1',
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                        }]
                    )
                except ClientError:
                    pass  # Ignore if it fails
                    
                for rule in sg_data['IpPermissionsEgress']:
                    try:
                        # Convert the rule for the API
                        clean_rule = self._clean_sg_rule(rule)
                        if clean_rule:
                            logger.info(f"Adding egress rule to security group {new_sg_id}")
                            self.ec2.authorize_security_group_egress(
                                GroupId=new_sg_id,
                                IpPermissions=[clean_rule]
                            )
                    except ClientError as e:
                        # Ignore rule already exists errors
                        if 'InvalidPermission.Duplicate' not in str(e):
                            logger.error(f"Error adding egress rule: {e}")
    
    def _clean_sg_rule(self, rule):
        """Clean security group rule for API compatibility"""
        clean_rule = {}
        
        # Copy basic properties
        if 'IpProtocol' in rule:
            clean_rule['IpProtocol'] = rule['IpProtocol']
        else:
            return None  # Skip rules without protocol
            
        if 'FromPort' in rule:
            clean_rule['FromPort'] = rule['FromPort']
        
        if 'ToPort' in rule:
            clean_rule['ToPort'] = rule['ToPort']
        
        # Handle IP ranges
        if 'IpRanges' in rule and rule['IpRanges']:
            clean_rule['IpRanges'] = []
            for ip_range in rule['IpRanges']:
                if 'CidrIp' in ip_range:
                    clean_ip_range = {'CidrIp': ip_range['CidrIp']}
                    if 'Description' in ip_range:
                        clean_ip_range['Description'] = ip_range['Description']
                    clean_rule['IpRanges'].append(clean_ip_range)
        
        # Handle IPv6 ranges
        if 'Ipv6Ranges' in rule and rule['Ipv6Ranges']:
            clean_rule['Ipv6Ranges'] = []
            for ip_range in rule['Ipv6Ranges']:
                if 'CidrIpv6' in ip_range:
                    clean_ip_range = {'CidrIpv6': ip_range['CidrIpv6']}
                    if 'Description' in ip_range:
                        clean_ip_range['Description'] = ip_range['Description']
                    clean_rule['Ipv6Ranges'].append(clean_ip_range)
        
        
        return clean_rule
    
    def restore_vpc_from_backup(self):
        """Restore a VPC and its components from a backup"""
        # Load the backup data
        backup_data = self.load_backup_data()
        if not backup_data:
            logger.error("Failed to load backup data")
            return False
        
        # Extract VPC data
        vpcs = backup_data.get('vpcs', {})
        if not vpcs:
            logger.error("No VPCs found in backup data")
            return False
        
        # If a specific VPC ID was provided, only restore that one
        if self.target_vpc_id and self.target_vpc_id not in vpcs:
            logger.error(f"VPC {self.target_vpc_id} not found in backup data")
            return False
        
        vpc_ids = [self.target_vpc_id] if self.target_vpc_id else list(vpcs.keys())
        
        # Restore each VPC
        for vpc_id in vpc_ids:
            vpc_details = vpcs[vpc_id]
            
            logger.info(f"Restoring VPC {vpc_id}...")
            new_vpc_id = self.restore_vpc(vpc_details)
            if not new_vpc_id:
                logger.error(f"Failed to restore VPC {vpc_id}")
                continue

            new_igw_id = None
            if vpc_details.get('internet_gateways'):
                igw_data = vpc_details['internet_gateways'][0] if vpc_details['internet_gateways'] else None
                if igw_data:
                    new_igw_id = self.restore_internet_gateway(igw_data, new_vpc_id)
            
            logger.info("Restoring subnets...")
            self.restore_subnets(vpc_details.get('subnets', []), new_vpc_id)
            
            logger.info("Restoring route tables...")
            self.restore_route_tables(vpc_details.get('route_tables', []), new_vpc_id, new_igw_id)
            
            logger.info("Restoring security groups...")
            self.restore_security_groups(vpc_details.get('security_groups', []), new_vpc_id)
            
            logger.info(f"VPC {vpc_id} has been restored to {new_vpc_id}")
            logger.info("Resource mappings (original ID -> new ID):")
            logger.info(f"  VPC: {vpc_id} -> {new_vpc_id}")
            for k, v in self.created_resources['subnets'].items():
                logger.info(f"  Subnet: {k} -> {v}")
            for k, v in self.created_resources['route_tables'].items():
                logger.info(f"  Route Table: {k} -> {v}")
            for k, v in self.created_resources['security_groups'].items():
                logger.info(f"  Security Group: {k} -> {v}")
        
        return True


def cmd_backup(args):
    """Command handler for backup operation"""
    try:
        backup = VpcBackup(
            region=args.region,
            profile=args.profile,
            bucket=args.bucket,
            prefix=args.prefix
        )
        
        success = backup.backup_vpc_configuration()
        if success:
            logger.info("VPC backup completed successfully")
            return 0
        else:
            logger.error("VPC backup failed")
            return 1
            
    except Exception as e:
        logger.exception(f"Unexpected error during backup: {e}")
        return 1


def cmd_restore(args):
    try:
        restore = VpcRestore(
            bucket=args.bucket,
            timestamp=args.timestamp,
            vpc_id=args.vpc_id,
            region=args.region,
            profile=args.profile
        )
        
        success = restore.restore_vpc_from_backup()
        if success:
            logger.info("VPC restore completed successfully")
            return 0
        else:
            logger.error("VPC restore failed")
            return 1
            
    except Exception as e:
        logger.exception(f"Unexpected error during restore: {e}")
        return 1


def cmd_list(args):
    try:
        restore = VpcRestore(
            bucket=args.bucket,
            region=args.region,
            profile=args.profile
        )
        
        backups = restore.list_backups()
        
        if not backups:
            logger.info("No backups found")
            return 0
        
        # Print backups in a table format
        print("\nAvailable VPC Backups:")
        print("=" * 80)
        print(f"{'Timestamp':<25} {'Date':<12} {'Time':<10} {'Region':<15} {'VPC Count'}")
        print("-" * 80)
        
        for backup in backups:
            restore.timestamp = backup['timestamp']
            backup_data = restore.load_backup_data()
            
            if backup_data and 'metadata' in backup_data:
                metadata = backup_data['metadata']
                vpc_count = metadata.get('vpc_count', 'N/A')
                region = metadata.get('region', 'unknown')
                
                try:
                    ts = backup['timestamp']
                    date_part = ts.split('-')[0:3]
                    time_part = ts.split('-')[3:6]
                    date_str = "-".join(date_part)
                    time_str = ":".join(time_part)
                except:
                    date_str = "N/A"
                    time_str = "N/A"
                
                print(f"{backup['timestamp']:<25} {date_str:<12} {time_str:<10} {region:<15} {vpc_count}")
        
        print("=" * 80)
        print(f"\nTo restore a specific backup: timelessvpc restore --bucket {args.bucket} --timestamp TIMESTAMP")
        logger.info("Backup listing completed successfully")
        return 0
            
    except Exception as e:
        logger.exception(f"Unexpected error during list: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='TimelessVPC - AWS VPC Configuration Backup and Restore Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    backup_parser = subparsers.add_parser('backup', help='Backup VPC configurations to S3')
    backup_parser.add_argument('--region', help='AWS region (defaults to AWS_DEFAULT_REGION env var or ~/.aws/config)')
    backup_parser.add_argument('--profile', help='AWS profile name (defaults to AWS_PROFILE env var)')
    backup_parser.add_argument('--bucket', required=True, help='S3 bucket name for storing backups')
    backup_parser.add_argument('--prefix', default='vpc-backups', help='S3 key prefix for backups (default: vpc-backups)')
    
    restore_parser = subparsers.add_parser('restore', help='Restore VPC configurations from S3')
    restore_parser.add_argument('--bucket', required=True, help='S3 bucket name containing backups')
    restore_parser.add_argument('--timestamp', help='Backup timestamp to restore (default: latest)')
    restore_parser.add_argument('--vpc-id', help='Specific VPC ID to restore (default: all VPCs in backup)')
    restore_parser.add_argument('--region', help='AWS region (defaults to AWS_DEFAULT_REGION)')
    restore_parser.add_argument('--profile', help='AWS profile name (defaults to AWS_PROFILE env var)')
    

    list_parser = subparsers.add_parser('list', help='List available VPC backups')
    list_parser.add_argument('--bucket', required=True, help='S3 bucket name containing backups')
    list_parser.add_argument('--region', help='AWS region (defaults to AWS_DEFAULT_REGION)')
    list_parser.add_argument('--profile', help='AWS profile name (defaults to AWS_PROFILE env var)')
    
    args = parser.parse_args()
    print_banner()
    if args.command == 'backup':
        return cmd_backup(args)
    elif args.command == 'restore':
        return cmd_restore(args)
    elif args.command == 'list':
        return cmd_list(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())