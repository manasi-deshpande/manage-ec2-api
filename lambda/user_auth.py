import boto3
import os

identitystore = boto3.client("identitystore", region_name="us-east-1")
IDENTITY_STORE_ID = "d-906785b77a"
REQUIRED_GROUP = "EC2UsersGroup"

def get_calling_username(event):
    print("Inside User Auth")
    print(event)
    user_arn = event.get("requestContext", {}).get("authorizer", {}).get("iam").get("userArn")
    return user_arn.split("/")[-1] if user_arn else "unknown@example.com"

def user_in_required_group(username):
    user_id = get_user_id(username)
    groups = identitystore.list_group_memberships_for_member(
        IdentityStoreId=IDENTITY_STORE_ID,
        MemberId={"UserId": user_id}
    )["GroupMemberships"]

    for group_ref in groups:
        group_id = group_ref["GroupId"]
        group = identitystore.describe_group(
            IdentityStoreId=IDENTITY_STORE_ID,
            GroupId=group_id
        )
        if group["DisplayName"] == REQUIRED_GROUP:
            return True

    return False

def get_user_id(username):
    users = identitystore.list_users(
        IdentityStoreId=IDENTITY_STORE_ID,
        Filters=[{
            "AttributePath": "UserName",
            "AttributeValue": username
        }]
    )["Users"]

    if not users:
        raise Exception(f"User '{username}' not found in Identity Center")

    return users[0]["UserId"]
