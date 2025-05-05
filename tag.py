import json
import logging
import requests
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    print("Authenticating with DefaultAzureCredential...")
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Update this
    print(f"Using subscription: {subscription_id}")
    return ResourceManagementClient(credential, subscription_id)

def get_servicenow_metadata(ci_value):
    print(f"Fetching metadata from ServiceNow for CI: {ci_value}")
    # Replace this with actual ServiceNow API call
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
    print(f"Updating tags for resource: {resource_id}")
    resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
    existing_tags = resource.tags or {}
    print(f"Existing tags: {existing_tags}")
    existing_tags.update(new_tags)
    print(f"New tags to apply: {existing_tags}")

    result = resource_client.resources.update_by_id(
        resource_id=resource_id,
        api_version="2021-04-01",
        parameters={"tags": existing_tags}
    )
    print(f"Update result: {result.id if result else 'No result returned'}")

def process_event(event):
    print("Processing single event...")
    resource_id = event.get("data", {}).get("resourceUri")
    if not resource_id:
        print("No resourceUri found in event.")
        return

    print(f"Resource URI: {resource_id}")
    resource_client = get_resource_client()

    try:
        print(f"Fetching resource details for: {resource_id}")
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}
        print(f"Current tags: {tags}")

        ci_value = tags.get("syf:application:ci")
        if not ci_value:
            print(f"'syf:application:ci' tag not found on resource {resource_id}.")
            return

        additional_tags = get_servicenow_metadata(ci_value)
        additional_tags["syf:application:ci"] = ci_value  # Ensure CI tag remains

        update_tags(resource_client, resource_id, additional_tags)
        print(f"Tags successfully updated for resource {resource_id}.")

    except Exception as e:
        print(f"Error processing resource {resource_id}: {str(e)}")

# Main entry point for Azure Automation webhook
def runbook_main(req):
    try:
        print("Webhook triggered. Reading request body...")
        body = req.get_body().decode()
        print(f"Received body: {body}")
        events = json.loads(body)
        if not isinstance(events, list):
            events = [events]

        for event in events:
            process_event(event)
        print("Processing complete.")

    except Exception as e:
        print(f"Runbook execution error: {str(e)}")
