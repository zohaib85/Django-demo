import json
import requests
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    print("Authenticating with Azure using managed identity...")
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Replace with your actual subscription ID
    print(f"Using subscription: {subscription_id}")
    return ResourceManagementClient(credential, subscription_id)

def get_servicenow_metadata(ci_value):
    print(f"Fetching metadata from ServiceNow for CI value: {ci_value}")
    # Simulated metadata from ServiceNow
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
    print(f"Preparing to update tags for: {resource_id}")
    try:
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        existing_tags = resource.tags or {}
        print(f"Existing tags on resource: {existing_tags}")

        combined_tags = {**existing_tags, **new_tags}
        print(f"Applying combined tags: {combined_tags}")

        resource_client.resources.update_by_id(
            resource_id=resource_id,
            api_version="2021-04-01",
            parameters={"tags": combined_tags}
        )
        print(f"Tags successfully updated for {resource_id}")
    except Exception as e:
        print(f"Failed to update tags: {str(e)}")

def process_event(event):
    print("Processing incoming Event Grid event...")
    resource_id = event.get("data", {}).get("resourceUri")
    if not resource_id:
        print("No resourceUri in event data.")
        return

    print(f"Resource ID from event: {resource_id}")
    resource_client = get_resource_client()

    try:
        print("Fetching current resource state...")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}
        print(f"Tags found on resource: {tags}")

        # Normalize keys (Azure stores tag keys case-insensitively)
        ci_value = None
        for key in tags:
            if key.lower() == "syf:application:ci":
                ci_value = tags[key]
                break

        if not ci_value:
            print(f"'syf:application:ci' tag not found on {resource_id}")
            return

        print(f"CI tag value: {ci_value}")

        additional_tags = get_servicenow_metadata(ci_value)
        additional_tags["syf:application:ci"] = ci_value

        update_tags(resource_client, resource_id, additional_tags)

    except Exception as e:
        print(f"Exception while processing resource: {str(e)}")

def runbook_main(req):
    try:
        print("Webhook triggered. Reading body...")
        body = req.get_body().decode()
        print(f"Received body: {body}")
        events = json.loads(body)
        if not isinstance(events, list):
            events = [events]

        for event in events:
            process_event(event)

        print("Runbook processing complete.")

    except Exception as e:
        print(f"Runbook execution error: {str(e)}")
