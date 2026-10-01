# Next Steps

This document captures tech debt and high value next steps as I see them on 1/27/26.

* ✅ DONE. Pass oauth jwt token from ui -> agent ws -> mcp -> eugene_ws
To [add HS256 JWT verification](https://gofastmcp.com/servers/auth/token-verification#symmetric-key-verification-hmac) to the MCP server
To pass the JWT token to the downstream endpoint from MCP

* Agentic coworker using Claude Desktop
Example of moving from chat prompts to “task queues”
https://youtu.be/h7dbkDcb3hA?t=1691

* Fix AIA deployment. Right now the AIA cannot be deployed due to some ECS IAM permission issue (probably an easy fix, not sure how the permission was retracted or when things stopped working). Also, it does not make sense to deploy the latest code, until the latest data model is ingested into neo4j using the latest ingest notebook (expecting updates to pubmed, organization, clinical trial nodes at least)

* Scale the MCP server to > 2. First, change the `eugene_agent_ws` to use a `S3SessionManager` vs a `FileSessionManager` backed conversation session manager. This will allow the conversation to work across multiple instance of the ECS deployment.

* Merge the `qa` branch into `main`. Currently the `qa` and `main` branches are out of sync and should be fixed.

Try these commands. It will preserve git commit history. I did not merge for fear I would mess the repo up right before leaving.
```
 git checkout qa
 git merge -Xours origin/main
 git add .
 git merge --continue
 ```

* The `difflabs` deployed `agent-ui` and `agent-ws` does not work because difflabs cannot reach the openai model or a claude model. The error in the logs says

```
January 29, 2026, 21:13
	
WARNING:query.agent.eugene_data_agent:Error occurred while streaming conversation 5cdd113c-8eb3-4d26-bf8a-f3ee2b38b8fc: Connection error.
	
agent_ws
January 29, 2026, 21:13
	
WARNING:query.agent.eugene_data_agent:Connection error.
	
agent_ws
January 29, 2026, 21:13
	
INFO:query.router.chat_query_agent_router:Completed streaming response for conversation 5cdd113c-8eb3-4d26-bf8a-f3ee2b38b8fc
	
agent_ws
January 29, 2026, 21:13
	
INFO:openai._base_client:Retrying request to /chat/completions in 0.855668 seconds
	
agent_ws
January 29, 2026, 21:13
	
INFO:openai._base_client:Retrying request to /chat/completions in 0.479309 seconds
```

Where `/chat/completions` is an OpenAI ChatGPT endpoint.

* The initial [ingest](../eugene/README.md) has three steps. We could merge the data from these three steps to reduce inital load time for the "foundational" nodes. 
