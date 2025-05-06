import json
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    credential = DefaultAzureCredential()
    # Extract subscription ID from resource URI dynamically later
    return ResourceManagementClient(credential, "<REPLACE-WITH-YOUR-SUBSCRIPTION-ID>")

def get_servicenow_metadata(ci_value):
    print(f"Calling ServiceNow API for CI: {ci_value}")
    # Dummy example; replace with actual ServiceNow call
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
        print(f"Fetching resource: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        existing_tags = resource.tags or {}
        print(f"Existing tags: {existing_tags}")

        merged_tags = {**existing_tags, **new_tags}
        print(f"Merged tags: {merged_tags}")

        print("Updating tags...")
        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": merged_tags}
        )
        print("Tags updated successfully.")
    except Exception as e:
        print(f"Error while tagging resource: {str(e)}")

# --- MAIN ---
try:
    if len(sys.argv) < 2:
        print("No webhook data provided.")
        sys.exit(1)

    raw_input = sys.argv[1]
    print(f"Raw sys.argv[1]: {raw_input}")

    # Parse CloudEvent envelope
    event = json.loads(raw_input)
    if isinstance(event, list):
        event = event[0]

    print(f"Parsed CloudEvent: {event}")

    data = event.get("data", {})
    resource_uri = data.get("resourceUri")
    if not resource_uri:
        print("Missing resourceUri in event data.")
        sys.exit(1)

    print(f"Resource URI: {resource_uri}")

    # Extract subscription ID from the URI dynamically
    subscription_id = resource_uri.split("/")[2]
    print(f"Detected subscription ID: {subscription_id}")

    resource_client = ResourceManagementClient(DefaultAzureCredential(), subscription_id)
    resource = resource_client.resources.get_by_id(resource_uri, api_version="2021-04-01")
    tags = resource.tags or {}
    print(f"Resource tags: {tags}")

    ci_value = tags.get("syf:application:ci")
    if not ci_value:
        print("syf:application:ci tag not found. Skipping.")
        sys.exit(0)

    print(f"Found CI value: {ci_value}")

    new_tags = get_servicenow_metadata(ci_value)
    new_tags["syf:application:ci"] = ci_value

    update_tags(resource_client, resource_uri, new_tags)

    print("Automation completed.")

except Exception as e:
    print(f"Unhandled error: {str(e)}")
