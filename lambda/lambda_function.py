import boto3
import json
import os
from user_auth import get_calling_username, user_in_required_group

ec2 = boto3.client("ec2", region_name="us-east-1")

TAG_KEY = "ManagedBy"
TAG_VALUE = "LambdaAPI"

with open("config.json") as f:
    CONFIG = json.load(f)

def lambda_handler(event, context):
    try:
        username = get_calling_username(event)
        if not user_in_required_group(username):
            return response(403, f"Access denied: {username} is not in required group.")

        body = json.loads(event.get("body", "{}"))
        action = body.get("action")
        instance_id = body.get("instance_id")
        if action == "create":
            return create_instance(body, username)
        elif action in {"start", "stop", "delete"} and instance_id:
            return manage_instance(action, instance_id, username)
        elif action == "get_metadata":
            return get_metadata(username)
        else:
            return response(400, "Invalid action or missing instance_id")

    except Exception as e:
        return response(500, f"Error: {str(e)}")

def get_metadata(username):
    try:
        instance_list = ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:Owner',
                        'Values': [username]
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['pending', 'running', 'stopping', 'stopped']
                    }
                ]
            )
        instances = []
        for reservation in instance_list['Reservations']:
            for instance in reservation['Instances']:
                instances.append({
                    'instance_id': instance['InstanceId'],
                    'private_ip': instance.get('PrivateIpAddress'),
                    'public_ip': instance.get('PublicIpAddress'),
                    'state': instance['State']['Name'],
                    'type': instance['InstanceType'],
                    'launch_time': str(instance['LaunchTime'])
                })
        return {
            "statusCode": 200,
            "body": json.dumps(instances),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        return response(500, f"Error retrieving instances: {e}")


def create_instance(params, username):
    for field in ["ami_id", "instance_type", "key_name", "security_group_id", "subnet_id"]:
        if params.get(field) not in CONFIG[field + "s"]:
            return response(400, f"Invalid {field}: {params.get(field)}")

    instance = ec2.run_instances(
        ImageId=params["ami_id"],
        InstanceType=params["instance_type"],
        KeyName=params["key_name"],
        MaxCount=1,
        MinCount=1,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': TAG_KEY, 'Value': TAG_VALUE},
                {'Key': 'Owner', 'Value': username},
                {'Key': 'Name', 'Value': 'ec2-' + str(username)}
            ]
        }],
         NetworkInterfaces=[{
                "SubnetId": params["subnet_id"],
                "DeviceIndex": 0,
                "AssociatePublicIpAddress": True,
                "Groups": [params["security_group_id"]]
            }]
    )['Instances'][0]

    instance_id = instance['InstanceId']
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])

    public_ip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0].get('PublicIpAddress')

    return response(200, {
        "instance_id": instance_id,
        "public_ip": public_ip,
        "ssh_command": f"ssh -i /path/to/{params['key_name']}.pem ec2-user@{public_ip}"
    })


def manage_instance(action, instance_id, username):
    users_instances =  json.loads(get_metadata(username)['body'])
    valid_instance_id = False
    for user_instance in users_instances:
        if instance_id == user_instance["instance_id"]:
            valid_instance_id = True
    if valid_instance_id:
        if not is_managed(instance_id, username):
            return response(403, "Unauthorized instance")

        if action == "start":
            ec2.start_instances(InstanceIds=[instance_id])
            return response(200, f"Instance {instance_id} started")
        elif action == "stop":
            ec2.stop_instances(InstanceIds=[instance_id])
            return response(200, f"Instance {instance_id} stopped")
        elif action == "delete":
            ec2.terminate_instances(InstanceIds=[instance_id])
            return response(200, f"Instance {instance_id} terminated")
        else:
            return response(400, "Invalid action")
    else:
        return response(500, "No instances found with this instance id")

def is_managed(instance_id, username):
    instance = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
    return tags.get(TAG_KEY) == TAG_VALUE and tags.get("Owner") == username


def response(status, message):
    return {
        "statusCode": status,
        "body": json.dumps({"message": message}),
        "headers": {"Content-Type": "application/json"}
    }
