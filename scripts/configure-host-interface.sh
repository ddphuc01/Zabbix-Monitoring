#!/bin/bash
# Script to automatically configure Zabbix Server host interface
# This fixes the default host to use zabbix-agent2 container instead of 127.0.0.1

set -e

echo "🔧 Configuring Zabbix Server host interface..."

# Wait for Zabbix Server to be ready
echo "⏳ Waiting for Zabbix Server to be ready..."
sleep 30

# Database connection details
DB_HOST="postgres-server"
DB_NAME="zabbix"
DB_USER=$(cat /run/secrets/POSTGRES_USER 2>/dev/null || echo "zabbix")
DB_PASS=$(cat /run/secrets/POSTGRES_PASSWORD 2>/dev/null || echo "")

# Update the default "Zabbix server" host interface
# Change IP from 127.0.0.1 to DNS name zabbix-agent2
docker exec zabbix-postgres psql -U "$DB_USER" -d "$DB_NAME" -c "
UPDATE interface 
SET ip = '', 
    dns = 'zabbix-agent2', 
    useip = 0,
    port = 10050
WHERE hostid = (
    SELECT hostid FROM hosts WHERE host = 'Zabbix server'
) AND type = 1;
" 2>/dev/null || {
    echo "⚠️  Failed to update via postgres container, trying alternative method..."
    
    # Alternative: Use zabbix_server container
    docker exec -e PGPASSWORD="$DB_PASS" zabbix-server \
        psql -h postgres-server -U "$DB_USER" -d "$DB_NAME" -c "
        UPDATE interface 
        SET ip = '', 
            dns = 'zabbix-agent2', 
            useip = 0,
            port = 10050
        WHERE hostid = (
            SELECT hostid FROM hosts WHERE host = 'Zabbix server'
        ) AND type = 1;
    "
}

echo "✅ Host interface updated successfully!"
echo "   - Host: Zabbix server"
echo "   - Interface: zabbix-agent2:10050 (DNS)"
echo "   - Type: Zabbix Agent 2"

# Reload Zabbix Server configuration cache
echo "🔄 Reloading Zabbix Server configuration cache..."
docker exec zabbix-server zabbix_server -R config_cache_reload 2>/dev/null || true

echo ""
echo "✅ Configuration complete!"
echo "   The 'Zabbix server' host now uses zabbix-agent2 container via DNS."
echo "   Please check the web interface: Configuration → Hosts → Zabbix server"
