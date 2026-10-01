# Diffusion Labs
DIFFLABS_HOSTNAME = "internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com"

# AI Accelerator
AIA_STAGING_HOSTNAME = "eugene-staging.ai.cslg1.cslg.net"
AIA_PROD_HOSTNAME = "eugene.ai.cslg1.cslg.net"


DIFFLABS_URL_BASE = f"https://{DIFFLABS_HOSTNAME}"
AIA_STAGING_URL_BASE = f"https://{AIA_STAGING_HOSTNAME}"
AIA_PROD_URL_BASE = f"https://{AIA_PROD_HOSTNAME}"


URL_BASE_MAP = {
    "PROD_DIFFLABS": DIFFLABS_URL_BASE,
    "STAGING_DIFFLABS": DIFFLABS_URL_BASE,
    "PROD_AIA": AIA_PROD_URL_BASE,
    "STAGING_AIA": AIA_STAGING_URL_BASE,
}
