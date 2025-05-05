import json
import logging
import requests
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient

def get_resource_client():
    credential = DefaultAzureCredential()
    subscription_id = "<your-subscription-id>"  # Optionally extract from subject
    return ResourceManagementClient(credential, subscription_id)

def get_servicenow_metadata(ci_value):
    # Replace with real ServiceNow API call
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
    resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
    existing_tags = resource.tags or {}
    existing_tags.update(new_tags)

    resource_client.resources.update_by_id(
        resource_id=resource_id,
        api_version="2021-04-01",
        parameters={"tags": existing_tags}
    )

def process_event(event):
    resource_id = event.get("data", {}).get("resourceUri")
    if not resource_id:
        logging.warning("No resourceUri found in event.")
        return

    logging.info(f"Processing resource: {resource_id}")
    resource_client = get_resource_client()

    try:
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}

        ci_value = tags.get("syf:application:ci")
        if not ci_value:
            logging.info(f"Resource {resource_id} missing 'syf:application:ci' tag.")
            return

        additional_tags = get_servicenow_metadata(ci_value)
        additional_tags["syf:application:ci"] = ci_value  # Ensure CI stays

        update_tags(resource_client, resource_id, additional_tags)
        logging.info(f"Tags updated for resource {resource_id}.")

    except Exception as e:
        logging.error(f"Failed to process resource {resource_id}: {str(e)}")

# Main entry point for Azure Automation webhook
def runbook_main(req):
    try:
        events = json.loads(req.get_body().decode())
        for event in events:
            process_event(event)
    except Exception as e:
        logging.error(f"Runbook error: {str(e)}")
