# CSL AWS Accounts

This document is to capture information about logging into CSL AWS accounts.


To log into a CSL AWS account you will need to visit two sites.


First log into [Cyberark](https://csl.privilegecloud.cyberark.com/PasswordVault/v10/Accounts). Click the single sign on button. You will need to accept a 2FA (at this time ping)

Once you are in Cyberark use the copy button to copy your cslg aws account login password.

Next log into the [access portal](https://csl-cloud.awsapps.com/start/#/?tab=accounts). You will be prompted for a single signon, the user name is in the form `<first>.a.<last>@cslg1.cslg.net` e.g. damian.a.knopp@cslg1.cslg.net. Copy the password from cyberark.

Once logged in you will see this [access dashboard](./img/access_portal.png)

Click into the PowerUserAccess or what ever role to login into the AWS Console.


Note for the AI Accelorator account click the `SCOP-Console` link, you can see the AWS Console, but will have restricted and limited console privileges. Most actions will need to be done in the pipeline or thru logging into the SageMaker tool and using its CLI.



