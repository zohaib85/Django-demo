from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.appconfiguration import AzureAppConfigurationClient, ConfigurationSetting
import os

# Use DefaultAzureCredential for managed identity or service principal
credential = DefaultAzureCredential()

# Define your Azure subscription ID
subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")

# Azure App Configuration endpoint (e.g. "https://myconfig.azconfig.io")
app_config_endpoint = os.environ.get("AZURE_APPCONFIG_ENDPOINT")

# Initialize clients
resource_client = ResourceManagementClient(credential, subscription_id)
app_config_client = AzureAppConfigurationClient(app_config_endpoint, credential)

def main():
    # List all resources
    resources = resource_client.resources.list()

    for resource in resources:
        resource_id = resource.id.replace('/', '_')[1:]  # sanitize for key format
        tags = resource.tags or {}

        for key, value in tags.items():
            config_key = f"{resource_id}:tag:{key}"
            config_value = value or "null"
            try:
                app_config_client.set_configuration_setting(ConfigurationSetting(
                    key=config_key,
                    value=config_value,
                    content_type="text/plain",
                    tags={"resourceId": resource.id}
                ))
                print(f"Stored: {config_key} -> {config_value}")
            except Exception as e:
                print(f"Error storing tag for {resource.id}: {str(e)}")

if __name__ == "__main__":
    main()
