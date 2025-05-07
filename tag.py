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
DEFAULT_API_VERSION = "2022-09-01"  # You can customize per resource type
# ---------------------------

def parse_cloudevents(raw_json):
    """
    Parse a list of CloudEvents received via Event Grid webhook.
    Returns a list of cloudevent objects.
    """
    try:
        events = json.loads(raw_json)
        cloud_events = [from_json(json.dumps(evt)) for evt in events]
        return cloud_events
    except Exception as e:
        raise ValueError(f"Failed to parse CloudEvent input: {str(e)}")

def extract_ci_tag(cloud_event):
    """
    Extract syf:application:ci tag from CloudEvent data.
    """
    data = cloud_event.data
    tags = data.get("tags", {})
    return tags.get("syf:application:ci")

def get_resource_id(cloud_event):
    """
    Get the Azure Resource ID from the CloudEvent.
    """
    # Prefer 'resourceUri' from data; fallback to CloudEvent subject
    data = cloud_event.data
    return data.get("resourceUri") or cloud_event["subject"]

def get_ci_metadata(ci_value):
    """
    Call ServiceNow API to retrieve metadata based on CI tag.
    """
    url = f"https://{SERVICENOW_INSTANCE}{SERVICENOW_API_PATH}{SERVICENOW_QUERY_TEMPLATE.format(ci_value=ci_value)}"
    print("Calling ServiceNow:", url)

    response = requests.get(
        url,
        auth=(SERVICENOW_USERNAME, SERVICENOW_PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        raise Exception(f"ServiceNow API call failed: {response.status_code} {response.text}")

    result = response.json()
    if not result.get("result"):
        raise Exception("No matching CI record found in ServiceNow.")

    ci_data = result["result"][0]
    return {
        "syf:ci_type": ci_data.get("ci_type", "unknown"),
        "syf:azr:owner": ci_data.get("owner", "unknown"),
        "syf:application:short_name": ci_data.get("short_name", "unknown")
    }

def tag_resource(resource_id, tags_to_add):
    """
    Apply tags to the Azure resource using managed identity.
    """
    try:
        subscription_id = resource_id.split("/")[2]
        credential = DefaultAzureCredential()
        client = ResourceManagementClient(credential, subscription_id)

        # Get current tags
        resource = client.resources.get_by_id(resource_id, DEFAULT_API_VERSION)
        current_tags = resource.tags or {}

        # Merge tags
        updated_tags = {**current_tags, **tags_to_add}
        print(f"Tagging resource: {resource_id}")
        print("New Tags:", updated_tags)

        # Apply tags
        client.resources.update_by_id(
            resource_id=resource_id,
            api_version=DEFAULT_API_VERSION,
            parameters={"tags": updated_tags}
        )
    except Exception as e:
        raise Exception(f"Failed to tag resource: {str(e)}")

def main():
    try:
        raw_input = sys.argv[1]
        print("Raw input received (truncated):", raw_input[:300])

        # Parse CloudEvents
        cloud_events = parse_cloudevents(raw_input)

        for event in cloud_events:
            print("\n--- Processing Event ---")
            resource_id = get_resource_id(event)
            print("Resource ID:", resource_id)

            ci_value = extract_ci_tag(event)
            if not ci_value:
                print("syf:application:ci tag is missing. Skipping resource.")
                continue

            print("CI Tag Value:", ci_value)

            # Get CI metadata from ServiceNow
            metadata_tags = get_ci_metadata(ci_value)
            print("Metadata received:", metadata_tags)

            # Apply the tags to the Azure resource
            tag_resource(resource_id, metadata_tags)
            print("Tagging complete.")

    except Exception as e:
        print("Runbook failed with error:", str(e))
        traceback.print_exc()

main()
