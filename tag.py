import json
import requests
import logging
import azure.identity
from azure.mgmt.resource import ResourceManagementClient

def get_azure_credentials():
    return azure.identity.DefaultAzureCredential()

def get_resource_client():
    credentials = get_azure_credentials()
    subscription_id = "<your-subscription-id>"
    return ResourceManagementClient(credentials, subscription_id)

def get_servicenow_tags(ci_value):
    # Replace this with real ServiceNow API call
    # For demonstration, return mock tags
    return {
        "syf:application": "example-app",
        "syf:application:short_name": "exapp",
        "syf:ci_type": "app",
        "syf:azr:owner": "owner@example.com",
        "syf:azr:financial_owner": "finance@example.com",
        "syf:azr:business_unit": "IT",
        "syf:environment": "prod"
    }

def update_resource_tags(resource_client, resource_id, new_tags):
    resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
    existing_tags = resource.tags or {}
    existing_tags.update(new_tags)

    resource_client.resources.update_by_id(
        resource_id=resource_id,
        api_version="2021-04-01",
        parameters={"tags": existing_tags}
    )

def main(event: dict):
    try:
        event_data = event["data"]
        resource_id = event_data.get("resourceId")

        if not resource_id:
            logging.warning("Resource ID not found in event.")
            return

        resource_client = get_resource_client()

        # Fetch the resource to read existing tags
        resource = resource_client.resources.get_by_id(resource_id, api_version="2021-04-01")
        tags = resource.tags or {}

        ci_value = tags.get("syf:application:ci")
        if not ci_value:
            logging.info(f"Resource {resource_id} does not have 'syf:application:ci' tag.")
            return

        # Get metadata from ServiceNow
        new_tags = get_servicenow_tags(ci_value)
        new_tags["syf:application:ci"] = ci_value  # Preserve original CI tag

        # Update resource with new tags
        update_resource_tags(resource_client, resource_id, new_tags)
        logging.info(f"Successfully updated tags for {resource_id}.")

    except Exception as e:
        logging.error(f"Error processing event: {str(e)}")

# Entry point for Azure Automation Runbook
def runbook_main(req):
    body = req.get_body().decode('utf-8')
    event = json.loads(body)
    main(event)
