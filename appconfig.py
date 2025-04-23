from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.managementgroups import ManagementGroupsAPI
from azure.mgmt.subscription import SubscriptionClient
from azure.appconfiguration import AzureAppConfigurationClient, ConfigurationSetting
import os

# ENV Variables
mg_name = os.environ.get("AZURE_MANAGEMENT_GROUP")  # e.g. 'my-management-group'
app_config_endpoint = os.environ.get("AZURE_APPCONFIG_ENDPOINT")  # e.g. 'https://myconfig.azconfig.io'

# Auth
credential = DefaultAzureCredential()
mg_client = ManagementGroupsAPI(credential)
sub_client = SubscriptionClient(credential)
app_config_client = AzureAppConfigurationClient(app_config_endpoint, credential)

def get_subscriptions_from_mg(mg_name):
    """Get all subscriptions in a management group."""
    mg_response = mg_client.management_group_subscriptions.list(mg_name)
    return [sub.name for sub in mg_response]

def store_tags(subscription_id):
    """Fetch resources and store tags for a given subscription."""
    print(f"\nProcessing subscription: {subscription_id}")
    resource_client = ResourceManagementClient(credential, subscription_id)
    resources = resource_client.resources.list()

    for res in resources:
        resource_id = res.id.replace('/', '_')[1:]
        tags = res.tags or {}
        for k, v in tags.items():
            key = f"{resource_id}:tag:{k}"
            value = v or "null"
            try:
                app_config_client.set_configuration_setting(ConfigurationSetting(
                    key=key,
                    value=value,
                    content_type="text/plain",
                    tags={"subscriptionId": subscription_id}
                ))
                print(f"Stored: {key} -> {value}")
            except Exception as e:
                print(f"Failed to store {key}: {str(e)}")

def main():
    subscriptions = get_subscriptions_from_mg(mg_name)
    for sub_id in subscriptions:
        store_tags(sub_id)

if __name__ == "__main__":
    main()
