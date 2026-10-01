host_name=eugene-development.ai.cslg1.cslg.net
openssl req -new -x509 -key private_key.pem -out certificate.pem -days 365 -subj "/CN=${host_name}"
