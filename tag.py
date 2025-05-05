import json
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Replace this
    print(f"Using subscription: {subscription_id}")
    return ResourceManagementClient(credential, subscription_id)

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

def update_tags(resource_client, resource_id, new_tags):
    try:
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        existing_tags = resource.tags or {}
        merged_tags = {**existing_tags, **new_tags}
        print(f"Updating tags: {merged_tags}")
        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": merged_tags}
        )
        print("Tags updated successfully.")
    except Exception as e:
        print(f"Error updating tags: {str(e)}")

try:
    print("Runbook started. Reading input...")
    input_json = sys.stdin.read()

    if not input_json.strip():
        print("No input received. Exiting.")
        sys.exit(0)

    print(f"Raw input: {input_json}")

    # Decode top-level webhook structure
    wrapper = json.loads(input_json)
    request_body_str = wrapper.get("RequestBody", "")
    print(f"RequestBody (string): {request_body_str}")

    if not request_body_str:
        print("Empty RequestBody in webhook payload.")
        sys.exit(1)

    # Decode the actual Event Grid payload (it's a stringified JSON list)
    events = json.loads(request_body_str)
    print(f"Parsed Event Grid events: {events}")

    resource_client = get_resource_client()

    for event in events:
        print("Processing event...")
        resource_id = event.get("data", {}).get("resourceUri")
        if not resource_id:
            print("No resourceUri found.")
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
            print("CI tag not found. Skipping resource.")
            continue

        print(f"Found CI: {ci_value}")
        new_tags = get_servicenow_metadata(ci_value)
        new_tags["syf:application:ci"] = ci_value

        update_tags(resource_client, resource_id, new_tags)

    print("Runbook completed.")

except Exception as e:
    print(f"Unexpected error: {str(e)}")
