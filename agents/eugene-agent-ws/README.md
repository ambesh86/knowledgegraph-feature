#C:\Users\Ambesh.Kumar\Downloads\CSL-Bio-informatics\knowledgegraph-feature-nextgen\agents\eugene-agent-ws
# EUGENE AGENT WEBSERVICE

Eugene chat agents exposed in a RESTFul webservices

## Setup

copy `env.template` to `.env`

populate the empty keys with the correct values

# Run

```
./bin/run-local.sh
```

## LLM Provider

The default provider is AWS Bedrock with `amazon.nova-lite-v1:0`. Configure
`LLM_PROVIDER=bedrock`, `BEDROCK_MODEL_ID`, and `AWS_REGION` (or
`AWS_DEFAULT_REGION`). AWS credentials are resolved through boto3's standard
credential chain; use an ECS task role, EC2 instance profile, or local AWS
profile rather than committing access keys. The role needs Bedrock model
invocation permissions for the selected model in that region.

OpenAI and Anthropic remain available by setting `LLM_PROVIDER=openai` or
`LLM_PROVIDER=anthropic` and providing the corresponding API key. An optional
`LLM_FALLBACK_PROVIDER` can name a different configured provider. Failover is
disabled by default because a failed Bedrock request may send the same prompt
to the alternate vendor. Events are buffered until the selected provider
finishes, so a failed provider's partial answer and tool calls are not emitted.

`GET /health/ready` checks provider configuration, the Bedrock credential
chain/region when selected, MCP reachability, and Eugene JWT configuration. It
does not invoke the model; issue a real query to validate Bedrock access and
model availability end to end.

