FROM docker.io/library/alpine@sha256:5b02b42e375f7426f8d65c3af331ca05d9878f9989230354504e0b9dfd431f60

RUN apk add --no-cache bash curl openssl jq ca-certificates

COPY kms-get-secret.sh /usr/local/bin/kms-get-secret.sh
RUN chmod +x /usr/local/bin/kms-get-secret.sh

RUN adduser -D -u 10001 app
USER 10001

ENTRYPOINT ["/usr/local/bin/kms-get-secret.sh"]
