from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.subscription import SubscriptionClient
from azure.appconfiguration import AzureAppConfigurationClient, ConfigurationSetting
import os

# ENV Vars: configure these in your automation environment
app_config_endpoint = os.environ.get("AZURE_APPCONFIG_ENDPOINT")  # e.g. https://myconfig.azconfig.io

# Auth
credential = DefaultAzureCredential()
app_config_client = AzureAppConfigurationClient(app_config_endpoint, credential)
subscription_client = SubscriptionClient(credential)

def get_all_subscription_ids():
    """Get all subscriptions the identity has access to."""
    subs = subscription_client.subscriptions.list()
    return [sub.subscription_id for sub in subs if sub.state.lower() == 'enabled']

def store_tags(subscription_id):
    """Fetch and store tags for all resources in a subscription."""
    print(f"Processing subscription: {subscription_id}")
    resource_client = ResourceManagementClient(credential, subscription_id)
    resources = resource_client.resources.list()

    for res in resources:
        res_id_clean = res.id.replace("/", "_")[1:]
        tags = res.tags or {}

        for tag_key, tag_val in tags.items():
            key = f"{res_id_clean}:tag:{tag_key}"
            value = tag_val or "null"
            try:
                app_config_client.set_configuration_setting(ConfigurationSetting(
                    key=key,
                    value=value,
                    content_type="text/plain",
                    tags={"subscriptionId": subscription_id}
                ))
                print(f"Stored: {key} -> {value}")
            except Exception as e:
                print(f"Failed to store {key}: {e}")

def main():
    subscription_ids = get_all_subscription_ids()
    for sub_id in subscription_ids:
        store_tags(sub_id)

if __name__ == "__main__":
    main()
