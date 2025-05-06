import json
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client(subscription_id):
    return ResourceManagementClient(DefaultAzureCredential(), subscription_id)

def get_servicenow_metadata(ci_value):
    print(f"Calling ServiceNow API for CI: {ci_value}")
    # Dummy mock response — replace with real call if needed
    return {
        "syf:application": "demo-app",
        "syf:application:short_name": "demo",
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
        print(f"Final tags to apply: {merged_tags}")

        print("Updating resource tags...")
        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": merged_tags}
        )
        print("Tags updated successfully.")
    except Exception as e:
        print(f"Tagging failed: {str(e)}")

# --- MAIN ---
try:
    if len(sys.argv) < 2:
        print("No input data provided to runbook.")
        sys.exit(1)

    raw_param = sys.argv[1]
    print(f"Raw input: {raw_param[:100]}...")  # Only show first 100 chars

    # Step 1: Deserialize outer JSON
    wrapper = json.loads(raw_param)
    raw_event = wrapper.get("RequestBody")
    if not raw_event:
        print("Missing RequestBody.")
        sys.exit(1)

    # Step 2: Deserialize embedded event body
    event = json.loads(raw_event)
    if isinstance(event, list):
        event = event[0]

    print(f"Parsed event type: {event.get('type')}")
    data = event.get("data", {})
    resource_uri = data.get("resourceUri") or data.get("scope")

    if not resource_uri:
        print("Missing resourceUri or scope in event data.")
        sys.exit(1)

    print(f"Resource URI: {resource_uri}")
    subscription_id = resource_uri.split("/")[2]
    print(f"Detected subscription ID: {subscription_id}")

    resource_client = get_resource_client(subscription_id)
    resource = resource_client.resources.get_by_id(resource_uri, api_version="2021-04-01")
    tags = resource.tags or {}
    print(f"Existing resource tags: {tags}")

    ci_value = tags.get("syf:application:ci")
    if not ci_value:
        print("Missing syf:application:ci tag. Skipping.")
        sys.exit(0)

    print(f"Found CI: {ci_value}")
    new_tags = get_servicenow_metadata(ci_value)
    new_tags["syf:application:ci"] = ci_value

    update_tags(resource_client, resource_uri, new_tags)

except Exception as e:
    print(f"Runbook failed: {str(e)}")
