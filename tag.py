import json
import requests
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    print("Authenticating with Azure using managed identity...")
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Replace this
    return ResourceManagementClient(credential, subscription_id)

def get_servicenow_metadata(ci_value):
    print(f"Fetching metadata from ServiceNow for CI: {ci_value}")
    return {
        "syf:application": "example-app",
        "syf:application:short_name": "exapp",
        "syf:ci_type": "app",
        "syf:azr:owner": "owner@example.com",
        "syf:azr:financial_owner": "finance@example.com",
        "syf:azr:business_unit": "IT",
        "syf:environment": "prod"
    }

def update_tags(resource_client, resource_id, new_tags):
    try:
        print(f"Updating tags for: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        existing_tags = resource.tags or {}
        print(f"Existing tags: {existing_tags}")

        updated_tags = {**existing_tags, **new_tags}
        print(f"New tags to apply: {updated_tags}")

        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": updated_tags}
        )
        print(f"Tags updated for resource: {resource_id}")
    except Exception as e:
        print(f"Failed to update tags for {resource_id}: {str(e)}")

# ---- Main script starts here (for webhook) ----

try:
    print("Webhook triggered. Reading request body...")
    import azure.functions as func  # Optional: For local testing
    import sys
    req = sys.stdin.read()
    print(f"Raw input: {req}")
    events = json.loads(req)
    if not isinstance(events, list):
        events = [events]

    resource_client = get_resource_client()

    for event in events:
        print("Processing event...")
        resource_id = event.get("data", {}).get("resourceUri")
        if not resource_id:
            print("No resourceUri found.")
            continue

        print(f"Resource URI: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}
        print(f"Tags on resource: {tags}")

        ci_value = None
        for key in tags:
            if key.lower() == "syf:application:ci":
                ci_value = tags[key]
                break

        if not ci_value:
            print(f"'syf:application:ci' tag not found on resource {resource_id}.")
            continue

        metadata_tags = get_servicenow_metadata(ci_value)
        metadata_tags["syf:application:ci"] = ci_value
        update_tags(resource_client, resource_id, metadata_tags)

    print("Runbook finished.")

except Exception as e:
    print(f"Runbook error: {str(e)}")
