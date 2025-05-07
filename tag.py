import sys
import json
import traceback
import requests

from cloudevents.http import from_json
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

# ---------------------------
# CONFIGURATION
# ---------------------------
SERVICENOW_INSTANCE = "your_instance.service-now.com"
SERVICENOW_USERNAME = "your_username"
SERVICENOW_PASSWORD = "your_password"
SERVICENOW_API_PATH = "/api/now/table/cmdb_ci"
SERVICENOW_QUERY_TEMPLATE = "?sysparm_query=ci_identifier={ci_value}&sysparm_limit=1"
DEFAULT_API_VERSION = "2022-09-01"  # Use a generic API version
# ---------------------------

def parse_cloudevents(raw_json):
    """Parse CloudEvents from Event Grid."""
    events = json.loads(raw_json)
    return [from_json(json.dumps(evt)) for evt in events]

def get_resource_id(cloud_event):
    """Extract the Azure Resource ID from event."""
    data = cloud_event.data
    return data.get("resourceUri") or cloud_event["subject"]

def get_resource_tags(resource_id):
    """Get the current tags on the Azure resource."""
    subscription_id = resource_id.split("/")[2]
    credential = DefaultAzureCredential()
    client = ResourceManagementClient(credential, subscription_id)

    print("Fetching resource:", resource_id)

    resource = client.resources.get_by_id(resource_id, DEFAULT_API_VERSION)
    return client, resource.tags or {}

def get_ci_metadata(ci_value):
    """Fetch CI metadata from ServiceNow."""
    url = f"https://{SERVICENOW_INSTANCE}{SERVICENOW_API_PATH}{SERVICENOW_QUERY_TEMPLATE.format(ci_value=ci_value)}"
    print("Querying ServiceNow:", url)

    response = requests.get(
        url,
        auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        raise Exception(f"ServiceNow API error: {response.status_code} {response.text}")

    result = response.json()
    if not result.get("result"):
        raise Exception("No CI record found.")

    ci_data = result["result"][0]
    return {
        "syf:ci_type": ci_data.get("ci_type", "unknown"),
        "syf:azr:owner": ci_data.get("owner", "unknown"),
        "syf:application:short_name": ci_data.get("short_name", "unknown")
    }


def update_resource_tags(client, resource_id, updated_tags, resource):
    """Apply new tags to the resource."""
    print(f"Applying tags to {resource_id}: {updated_tags}")
    parameters = {
        "location": resource.location,
        "tags": updated_tags
    }
    result = client.resources.begin_update_by_id(
        resource_id=resource_id,
        api_version=DEFAULT_API_VERSION,
        parameters=parameters
    ).result()
    print("Update result:", result.as_dict())
    
def process_event(event):
    """Main logic for a single event."""
    resource_id = get_resource_id(event)
    client, tags = get_resource_tags(resource_id)

    ci_value = tags.get("syf:application:ci")
    if not ci_value:
        print(f"No CI tag found on {resource_id}. Skipping.")
        return

    print("CI tag found:", ci_value)
    ci_metadata = get_ci_metadata(ci_value)

    # Merge new tags
    new_tags = {**tags, **ci_metadata}
    update_resource_tags(client, resource_id, new_tags)

def main():
    try:
        raw_input = sys.argv[1]
        print("Received input (truncated):", raw_input[:300])

        events = parse_cloudevents(raw_input)
        for event in events:
            print("\n--- Processing Event ---")
            process_event(event)

    except Exception as e:
        print("Runbook failed:", str(e))
        traceback.print_exc()

main()
