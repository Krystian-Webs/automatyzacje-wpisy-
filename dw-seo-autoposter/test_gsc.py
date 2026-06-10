import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds_json = os.environ["GSC_SERVICE_ACCOUNT"]
creds_data = json.loads(creds_json)
creds = service_account.Credentials.from_service_account_info(
    creds_data,
    scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
)
service = build("searchconsole", "v1", credentials=creds)
response = service.sites().list().execute()
print("Strony w Search Console:")
for site in response.get("siteEntry", []):
    print(f"  - {site['siteUrl']} ({site['permissionLevel']})")
