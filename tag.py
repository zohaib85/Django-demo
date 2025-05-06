import json
import sys
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Replace with real ID
    return ResourceManagementClient(credential, subscription_id)

def get_servicenow_metadata(ci_value):
    print(f"Calling ServiceNow for CI: {ci_value}")
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
        print(f"Updating tags on {resource_id} with: {merged_tags}")
        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": merged_tags}
        )
        print("Tag update successful.")
    except Exception as e:
        print(f"Error updating tags: {str(e)}")

# Main runbook logic
try:
    if len(sys.argv) < 2:
        print("No input argument passed. Exiting.")
        sys.exit(1)

    print("Reading input argument...")
    raw_input = sys.argv[1]
    print(f"Raw sys.argv[1]: {raw_input}")

    wrapper = json.loads(raw_input)
    request_body = wrapper.get("RequestBody", "")

    if not request_body:
        print("Missing 'RequestBody' in webhook data.")
        sys.exit(1)

    print(f"Raw RequestBody: {request_body}")

    # Make sure the RequestBody uses double quotes, then parse
    try:
        events = json.loads(request_body)
    except json.JSONDecodeError as je:
        print(f"JSON parsing error in RequestBody: {str(je)}")
        sys.exit(1)

    if not isinstance(events, list):
        events = [events]

    resource_client = get_resource_client()

    for event in events:
        print("Processing one event...")
        resource_id = event.get("data", {}).get("resourceUri")
        if not resource_id:
            print("No resourceUri found in event. Skipping.")
            continue

        print(f"Target resource: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}
        print(f"Existing tags: {tags}")

        ci_value = None
        for key, value in tags.items():
            if key.lower() == "syf:application:ci":
                ci_value = value
                break

        if not ci_value:
            print("CI tag not found. Skipping this resource.")
            continue

        print(f"CI value: {ci_value}")
        new_tags = get_servicenow_metadata(ci_value)
        new_tags["syf:application:ci"] = ci_value

        update_tags(resource_client, resource_id, new_tags)

    print("Runbook completed.")

except Exception as e:
    print(f"Unhandled error: {str(e)}")
