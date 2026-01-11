# Extend official Zabbix Server image with curl and jq for alert scripts
ARG ZABBIX_ALPINE_IMAGE_TAG=alpine-7.4
ARG ZABBIX_IMAGE_TAG_POSTFIX=-latest

FROM zabbix/zabbix-server-pgsql:${ZABBIX_ALPINE_IMAGE_TAG}${ZABBIX_IMAGE_TAG_POSTFIX}

# Install curl and jq for Telegram alert script
USER root
RUN apk add --no-cache curl jq bc

# Switch back to zabbix user for security
USER zabbix

LABEL description="Zabbix Server with curl/jq for Telegram alerts"
