# Entra ID

This document captures information about EUGENE and CSL Entra ID configuration.

1/26/26 - To date the eugene development service is connected to the Entra ID production instance. No other configuration has been made for other instances


Reference ticket: `SCTASK1797631`


The following is a copy of the service now ticket application, requested by the Entra ID team.


Service Now ticket

```
General Information
Application Name:  Eugene AI
Application name and ID in CMDB: Eugene AI is not a production application yet, and has no CMDB ID
Application Owner:  Sterling Foster
Vendor Information:  
Vendor Name: CSL I & T
Vendor Contact Person: Sterling Foster
Point of Contact (Technical):  Damian Knopp, Sterling Foster
Name: Damian Knopp
Email: damianknopp@cslbehring.com
Name: Sterling Foster
Email: sterlingfoster@cslbehring.com
Application Details (For Staging)
Application URL:  https://eugene-staging.ai.cslg1.cslg.net/
Type of Application:  Web
Is the application currently live: Yes/No
If no, what is the expected go-live date? Q2 FY 27
Number of Environments Available: Staging 
User Base:  CSL
Application Details (For Development)
Application URL:  http://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/
Type of Application:  Web
Is the application currently live: Yes/No
If no, what is the expected go-live date? Q2 FY 27
Number of Environments Available: Development 
User Base:  CSL
SSO Integration Details
What is the SSO Protocol to be used:  OAuth
Will authorization be handled via Active Directory (AD) groups?  No     
Accessible Outside CSL network: No
Accessible Inside CSL network: Yes
If OAuth/OpenID, please share below details:

Environment
 Development/Staging
Client ID
 This should be supplied to Eugene AI, I do not have a client ID provided to us yet
Redirect URI
 /auth/callback
Grant Type
 AuthorizationCode or PKCE?
List attributes required
 I am unsure what to put here, if this refers to OAuth scope, we will need READ access. Perhaps we can review in a meeting
```


Email 2
```
Application 1
 
Step
Login as Admin to Azure Portal and open Azure Active Directory
Click on App Registrations (URL: http://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com)
Click on New Registration
Name: Eugene Difflabs Development
Account Types: Accounts in this organization directory only
Click Register
From the Azure app page, click View API permissions
Click Add a permission” – Read and Write
Click Graph and then Permissions
 
Permissions of type Application/Delegated
 
After saving provide Admin consent for the permissions
 
Click Add permissions and provide admin consent for Application permissions.
From the Azure app page, click Certificates & secrets
Click New client secret
Description: SCTASK1797631
Expires:
Click Add
Copy the new Secret Value along with the Directory (tenant) ID and the Application (client) ID. Provide these to the requestor in a secure manner.
```

Eugene was provide with the a client, tenant and secret. Eugene uses the following environment variables. See the values in secrets manager `eugene/dev/uspto/env`

```
ENTRA_SCOPE=email
ENTRA_AUTHORITY=https://login.microsoftonline.com/e9ea0366-82a4-4b75-ab01-780fabc4c3c9
REDIRECT_URI=https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/auth/callback
REDIRECT_PATH=/auth/callback
ENTRA_TENANT_ID=e9ea0366-82a4-4b75-ab01-780fabc4c3c9
ENTRA_CLIENT_SECRET=<redacted>
ENTRA_CLIENT_ID=76e3ed82-c161-4eaf-aa26-5b3ea7e2ab24
```


