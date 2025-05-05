import json
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

# Initialize resource client
def get_resource_client():
    print("Authenticating with managed identity...")
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Replace with your actual subscription ID
    print(f"Subscription ID: {subscription_id}")
    return ResourceManagementClient(credential, subscription_id)

# Simulated call to ServiceNow
def get_servicenow_metadata(ci_value):
    print(f"Retrieving metadata from ServiceNow for CI: {ci_value}")
    return {
        "syf:application": "example-app",
        "syf:application:short_name": "exapp",
        "syf:ci_type": "app",
        "syf:azr:owner": "owner@example.com",
        "syf:azr:financial_owner": "finance@example.com",
        "syf:azr:business_unit": "IT",
        "syf:environment": "prod"
    }

# Apply tags
def update_tags(resource_client, resource_id, new_tags):
    try:
        print(f"Getting resource: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        existing_tags = resource.tags or {}
        print(f"Existing tags: {existing_tags}")

        merged_tags = {**existing_tags, **new_tags}
        print(f"Final tags to apply: {merged_tags}")

        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": merged_tags}
        )
        print("Tags successfully updated.")
    except Exception as e:
        print(f"Error updating tags: {str(e)}")

# Main execution
try:
    print("Runbook triggered via webhook.")
    input_json = sys.stdin.read()
    print(f"Received input: {input_json}")

    events = json.loads(input_json)
    if not isinstance(events, list):
        events = [events]

    resource_client = get_resource_client()

    for event in events:
        print("Processing event...")
        resource_id = event.get("data", {}).get("resourceUri")
        if not resource_id:
            print("No resourceUri found in event.")
            continue

        print(f"Resource ID: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}
        print(f"Current tags: {tags}")

        ci_value = None
        for key, value in tags.items():
            if key.lower() == "syf:application:ci":
                ci_value = value
                break

        if not ci_value:
            print("CI tag not found. Skipping this resource.")
            continue

        print(f"CI value found: {ci_value}")
        new_tags = get_servicenow_metadata(ci_value)
        new_tags["syf:application:ci"] = ci_value

        update_tags(resource_client, resource_id, new_tags)

    print("Runbook execution completed.")

except Exception as ex:
    print(f"Unexpected error: {str(ex)}")
