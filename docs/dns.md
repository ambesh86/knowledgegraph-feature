# DNS

This document captures information about DNS setup for EUGENE

A service now ticket was created requesting an internal DNS entry to an existing AWS Application Load Balancer. Two IPs were provided

See ticket, `SCTASK1651731`

```
Hi Ibrahim,

The DNS entry is required for internal DNS only.

Current IP address for application load balancer (***NOTE: the IP address could change):
internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com. 60 IN A 10.12.152.60
internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com. 60 IN A 10.12.152.99
 

Sterling


From: Tapal, Ibrahim IN/GLB EXT <Ibrahim.Tapal@cslbehring.com>
Date: Wednesday, August 6, 2025 at 1:22 PM
To: Knopp, Damian US/GLB EXT <Damian.Knopp@cslbehring.com>, Foster, Sterling US/KOP <Sterling.Foster@cslbehring.com>
Cc: DL I&T cslnetwork_gccin <DLITcslnetwork_gccin@cslbehring.com>
Subject: SCTASK1651731 | Add DNS entry eugene.ai.cslg1.cslg.net to route to internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com (A Record)

Hi Damian & Sterling,

As per your request, you have mentioned the "A record" DNS entry. Could you please confirm if this DNS entry is required for both internal DNS or External DNS for the cslg.net domain?

Also, since it's an A record, kindly share the IP address and the corresponding hostname so we can proceed.


Thanks & Regards, 
Ibrahim Tapal
Network Data Admin 
CSL I&T 
Service Portal: https://csl.service-now.com/sp 

```


## Verified

Note: an ALB ip address can change, and appears to have changed from the original email

Note: The AIA staging and prod dns entries point to the same entry as there was only one system deployment for that VPC.

```
dig +noall +answer eugene-staging.ai.cslg1.cslg.net
eugene-staging.ai.cslg1.cslg.net. 3600 IN CNAME	internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com.
internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com. 38 IN A 10.12.152.36
internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com. 38 IN A 10.12.152.124
```

```
dig +noall +answer eugene-prod.ai.cslg1.cslg.net
eugene-prod.ai.cslg1.cslg.net. 3600 IN	CNAME	internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com.
internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com. 12 IN A 10.12.152.36
internal-ai-accelerator-lb-2047437672.eu-central-1.elb.amazonaws.com. 12 IN A 10.12.152.124
```