FROM docker.io/library/alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6

RUN apk add --no-cache bash curl openssl jq ca-certificates

COPY kms-get-secret.sh /usr/local/bin/kms-get-secret.sh
RUN chmod +x /usr/local/bin/kms-get-secret.sh

RUN adduser -D -u 10001 app
USER 10001

ENTRYPOINT ["/usr/local/bin/kms-get-secret.sh"]
