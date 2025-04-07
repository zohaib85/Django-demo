# -------------------------
# IMPORTS
# -------------------------

import json
import re
import datetime
from contextlib import suppress

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.resource import ResourceManagementClient
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError

# -------------------------
# CONFIGURATION CONSTANTS
# -------------------------

# The name of the Azure Storage Account (must already exist)
STORAGE_ACCOUNT_NAME = "tagdetect"

# The name of the Azure Table to store resource tag data
TABLE_NAME = "resourceTags"

# -------------------------
# AUTHENTICATION
# -------------------------

def get_azure_credential():
    """
    Authenticates using the system-assigned Managed Identity
    provided by the Azure Automation account. This method leverages
    DefaultAzureCredential which automatically selects the right identity.
    
    Returns:
        DefaultAzureCredential: An authenticated credential object.
    """
    print("INFO: Acquiring Azure credential using Managed Identity...")
    credential = DefaultAzureCredential()
    print("INFO: Azure credential acquired successfully.")
    return credential

# -------------------------
# TABLE STORAGE CONNECTION
# -------------------------

def initialize_table_client(credential, storage_account_name, table_name):
    """
    Connects to Azure Table Storage and ensures the specified table exists.
    If the table does not exist, it will be created.

    Args:
        credential: Authenticated credential for accessing the storage account.
        storage_account_name (str): Name of the target storage account.
        table_name (str): Name of the table to read/write tag data.

    Returns:
        TableClient: A client for interacting with the Azure Table.
    """
    endpoint = f"https://{storage_account_name}.table.core.windows.net"
    print(f"INFO: Connecting to Table Storage at endpoint: {endpoint}")

    table_service = TableServiceClient(endpoint=endpoint, credential=credential)

    print(f"INFO: Ensuring table '{table_name}' exists...")
    with suppress(ResourceExistsError):
        table_service.create_table(table_name)
        print(f"INFO: Table '{table_name}' created successfully.")

    print(f"INFO: Accessing table client for table '{table_name}'")
    return table_service.get_table_client(table_name)

# -------------------------
# SUBSCRIPTION ENUMERATION
# -------------------------

def get_all_subscription_ids(credential):
    """
    Retrieves a list of all subscription IDs the credential has access to.

    Args:
        credential: Authenticated Azure credential.

    Returns:
        List[str]: A list of subscription IDs.
    """
    print("INFO: Retrieving list of accessible subscriptions...")
    subscription_client = SubscriptionClient(credential)
    subscription_ids = [sub.subscription_id for sub in subscription_client.subscriptions.list()]
    print(f"INFO: Found {len(subscription_ids)} subscription(s).")
    return subscription_ids

# -------------------------
# RESOURCE FORMATTING
# -------------------------

def sanitize_row_key(text):
    """
    Sanitizes a text string to make it a valid Azure Table Storage RowKey.
    Disallowed characters such as '/', '\\', '#', and '?' are replaced.

    Args:
        text (str): Original text.

    Returns:
        str: Sanitized text.
    """
    clean_text = re.sub(r'[\/\\#\?]', '_', text)
    return clean_text[:1024]  # RowKey max length is 1024 characters

def build_entity_from_resource(subscription_id, resource, tags):
    """
    Constructs a dictionary representing the resource's metadata and tags
    to be stored in Azure Table Storage.

    Args:
        subscription_id (str): Subscription ID the resource belongs to.
        resource (GenericResource): The Azure resource object.
        tags (dict or None): Tags dictionary for the resource.

    Returns:
        dict: Entity to upsert into Azure Table Storage.
    """
    resource_id = resource.id
    resource_name = resource.name
    resource_type = resource.type.replace("/", "_")
    resource_group = resource_id.split("/")[4] if "/resourceGroups/" in resource_id else "unknown"
    location = resource.location or "unknown"

    row_key = sanitize_row_key(f"{resource_group}_{resource_name}_{resource_type}")
    tag_data = json.dumps(tags) if tags else None

    entity = {
        "PartitionKey": subscription_id,
        "RowKey": row_key,
        "resourceId": resource_id,
        "resourceType": resource.type,
        "resourceName": resource_name,
        "resourceGroup": resource_group,
        "location": location,
        "tags": tag_data
    }

    return entity

# -------------------------
# RESOURCE PROCESSING
# -------------------------

def collect_and_store_tags_for_subscription(table_client, subscription_id, credential):
    """
    Collects tags from all resources in a subscription and stores them in Table Storage.

    Args:
        table_client: Azure Table client.
        subscription_id (str): Subscription ID.
        credential: Authenticated credential for accessing resources.
    """
    print(f"INFO: Collecting resources for subscription: {subscription_id}")
    resource_client = ResourceManagementClient(credential, subscription_id)

    try:
        resource_list = resource_client.resources.list()
        count = 0
        for resource in resource_list:
            try:
                tags = resource.tags or None
                entity = build_entity_from_resource(subscription_id, resource, tags)
                table_client.upsert_entity(entity=entity)
                print(f"INFO: Stored tags for resource: {resource.id}")
                count += 1
            except HttpResponseError as e:
                print(f"WARNING: Could not store entity for resource {resource.id}: {e.message}")
            except Exception as e:
                print(f"ERROR: Unexpected failure for resource {resource.id}: {str(e)}")

        print(f"INFO: Finished storing tags for {count} resource(s) in subscription {subscription_id}")

    except Exception as ex:
        print(f"ERROR: Failed to enumerate resources in subscription {subscription_id}: {str(ex)}")

# -------------------------
# SUBSCRIPTION PROCESSING
# -------------------------

def process_all_subscriptions_and_store_tags(credential, table_client):
    """
    Main loop that processes each accessible subscription and stores tag data
    for all its resources into the specified Azure Table.

    Args:
        credential: Authenticated Azure credential.
        table_client: Azure Table client.
    """
    subscription_ids = get_all_subscription_ids(credential)

    for sub_id in subscription_ids:
        print(f"INFO: Starting tag extraction for subscription: {sub_id}")
        collect_and_store_tags_for_subscription(table_client, sub_id, credential)
        print(f"INFO: Completed tag extraction for subscription: {sub_id}")

# -------------------------
# MAIN ENTRY POINT
# -------------------------

def main():
    """
    Main entry point for the Azure Automation runbook script.
    It performs authentication, connects to the storage account,
    and begins collecting and storing resource tag metadata.
    """
    start_time = datetime.datetime.utcnow()
    print("INFO: === Azure Tag Collector Runbook Started ===")
    print(f"INFO: Start time: {start_time.isoformat()}")

    # Authenticate with Azure
    credential = get_azure_credential()

    # Connect to Azure Table Storage
    table_client = initialize_table_client(
        credential,
        storage_account_name=STORAGE_ACCOUNT_NAME,
        table_name=TABLE_NAME
    )

    # Process all subscriptions and store tag data
    process_all_subscriptions_and_store_tags(credential, table_client)

    end_time = datetime.datetime.utcnow()
    print(f"INFO: End time: {end_time.isoformat()}")
    print("INFO: === Azure Tag Collector Runbook Finished ===")

# -------------------------
# RUN SCRIPT
# -------------------------

if __name__ == "__main__":
    main()
