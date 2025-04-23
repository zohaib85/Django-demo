from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.managementgroups import ManagementGroupsAPI
from azure.appconfiguration import AzureAppConfigurationClient, ConfigurationSetting
import os

# Get environment variables
management_group_name = os.environ.get("AZURE_MANAGEMENT_GROUP")  # e.g. 'my-mg-name'
app_config_endpoint = os.environ.get("AZURE_APPCONFIG_ENDPOINT")  # e.g. 'https://myconfig.azconfig.io'

# Authenticate using managed identity or service principal
credential = DefaultAzureCredential()

# Initialize App Configuration client
app_config_client = AzureAppConfigurationClient(app_config_endpoint, credential)

# Initialize Management Groups client
mg_client = ManagementGroupsAPI(credential)

def get_subscription_ids(mg_name):
    """Fetch all subscription IDs under a management group."""
    print(f"Fetching subscriptions in management group: {mg_name}")
    subs = []
    descendants = mg_client.management_group_descendants.list(group_id=mg_name)
    for item in descendants:
        if item.type.lower() == "microsoft.resources/subscriptions":
            subs.append(item.name)
    return subs

def push_tags_to_app_config(subscription_id):
    """Push resource tags from a subscription to App Configuration."""
    print(f"Processing subscription: {subscription_id}")
    resource_client = ResourceManagementClient(credential, subscription_id)
    resources = resource_client.resources.list()

    for resource in resources:
        resource_id_clean = resource.id.replace('/', '_')[1:]
        tags = resource.tags or {}

        for tag_key, tag_value in tags.items():
            config_key = f"{resource_id_clean}:tag:{tag_key}"
            config_value = tag_value or "null"
            try:
                app_config_client.set_configuration_setting(ConfigurationSetting(
                    key=config_key,
                    value=config_value,
                    content_type="text/plain",
                    tags={"subscriptionId": subscription_id}
                ))
                print(f"Stored: {config_key} -> {config_value}")
            except Exception as e:
                print(f"Error storing {config_key}: {e}")

def main():
    subscription_ids = get_subscription_ids(management_group_name)
    for sub_id in subscription_ids:
        push_tags_to_app_config(sub_id)

if __name__ == "__main__":
    main()
