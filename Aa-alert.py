from datetime import datetime, timedelta, timezone
from azure.identity import AzureCliCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from azure.communication.email import EmailClient, EmailContent, EmailMessage, EmailRecipients, EmailAddress
import os

# === CONFIGURATION ===
SUBSCRIPTION_ID = "<your-subscription-id>"
ACS_CONNECTION_STRING = "<your-acs-connection-string>"
ALERT_RECIPIENT_EMAIL = "<recipient@example.com>"
SENDER_EMAIL = "<verified-acs-sender@example.com>"

# === Step 1: Run Resource Graph Query ===
def get_recent_automation_accounts():
    credential = AzureCliCredential()
    client = ResourceGraphClient(credential)
    query = """
    resources
    | where type == "microsoft.automation/automationaccounts"
    | extend creationTime = todatetime(properties.creationTime)
    | where creationTime > ago(24h)
    | project name, location, resourceGroup, subscriptionId, creationTime
    """
    request = QueryRequest(
        subscriptions=[SUBSCRIPTION_ID],
        query=query
    )
    response = client.resources(request)
    return response.data

# === Step 2: Send Alert via Email ===
def send_email_alert(accounts):
    email_client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)

    account_list = "\n".join(
        [f"- {acct['name']} (Created: {acct['creationTime']})" for acct in accounts]
    )

    content = EmailContent(
        subject="🚨 Azure Automation Account Created in Last 24 Hours",
        plain_text=f"The following Automation Accounts were created recently:\n\n{account_list}"
    )

    recipients = EmailRecipients(
        to=[EmailAddress(email=ALERT_RECIPIENT_EMAIL, display_name="Security Admin")]
    )

    message = EmailMessage(
        sender=SENDER_EMAIL,
        content=content,
        recipients=recipients
    )

    poller = email_client.begin_send(message)
    result = poller.result()

    print(f"✔ Alert email sent. Message ID: {result['messageId']}")

# === MAIN ===
if __name__ == "__main__":
    recent_accounts = get_recent_automation_accounts()
    if recent_accounts and len(recent_accounts) > 0:
        print(f"🚨 Found {len(recent_accounts)} Automation Account(s) created in last 24 hours.")
        send_email_alert(recent_accounts)
    else:
        print("✅ No recent Automation Account creation detected.")
