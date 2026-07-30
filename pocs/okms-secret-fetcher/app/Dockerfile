FROM docker.io/library/alpine@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc

RUN apk add --no-cache bash curl openssl jq ca-certificates

COPY kms-get-secret.sh /usr/local/bin/kms-get-secret.sh
RUN chmod +x /usr/local/bin/kms-get-secret.sh

RUN adduser -D -u 10001 app
USER 10001

ENTRYPOINT ["/usr/local/bin/kms-get-secret.sh"]
