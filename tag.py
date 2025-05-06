import json
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client(subscription_id):
    return ResourceManagementClient(DefaultAzureCredential(), subscription_id)

def get_servicenow_metadata(ci_value):
    print(f"Mock ServiceNow lookup for CI: {ci_value}")
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
    print(f"Updating tags on: {resource_id}")
    resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
    current_tags = resource.tags or {}
    merged_tags = {**current_tags, **new_tags}
    print(f"Merged Tags: {merged_tags}")

    resource_client.resources.update_by_id(
        resource_id=resource_id,
        api_version="2021-04-01",
        parameters={"tags": merged_tags}
    )
    print("Update successful.")

# ---------------- MAIN ----------------
try:
    if len(sys.argv) < 2:
        print("Error: No input provided.")
        sys.exit(1)

    input_json_str = sys.argv[1]

    # Clean up bad quote issues (optional, for local testing)
    if input_json_str.startswith("'") and input_json_str.endswith("'"):
        input_json_str = input_json_str[1:-1]

    wrapper = json.loads(input_json_str)
    raw_event_str = wrapper.get("RequestBody")
    if not raw_event_str:
        print("Error: Missing RequestBody.")
        sys.exit(1)

    # Second layer parse
    event = json.loads(raw_event_str)
    print(f"Event type: {event.get('type')}")

    data = event.get("data", {})
    resource_uri = data.get("resourceUri") or data.get("scope")

    if not resource_uri:
        print("Error: No resourceUri or scope found.")
        sys.exit(0)

    print(f"Resource: {resource_uri}")
    subscription_id = resource_uri.split("/")[2]
    client = get_resource_client(subscription_id)

    resource = client.resources.get_by_id(resource_uri, api_version="2021-04-01")
    tags = resource.tags or {}
    print(f"Current Tags: {tags}")

    ci = tags.get("syf:application:ci")
    if not ci:
        print("CI tag not found. Exiting.")
        sys.exit(0)

    new_tags = get_servicenow_metadata(ci)
    new_tags["syf:application:ci"] = ci
    update_tags(client, resource_uri, new_tags)

except json.JSONDecodeError as e:
    print(f"JSON Decode Error: {str(e)}")
except Exception as e:
    print(f"Runbook failed: {str(e)}")
