FROM docker.io/library/alpine@sha256:71e9b7bae160ba167fa17414401b94cbcdaf3c32feeab9298bd794a2a0614c35

RUN apk add --no-cache bash curl openssl jq ca-certificates

COPY kms-get-secret.sh /usr/local/bin/kms-get-secret.sh
RUN chmod +x /usr/local/bin/kms-get-secret.sh

RUN adduser -D -u 10001 app
USER 10001

ENTRYPOINT ["/usr/local/bin/kms-get-secret.sh"]
