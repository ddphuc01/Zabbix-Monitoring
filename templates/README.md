# Linux Server Monitoring Template

This directory will contain Zabbix monitoring templates that can be imported via the web interface.

## Available Templates

### 1. Linux Servers (Built-in)
Use the built-in template: "Linux by Zabbix agent active"

Monitors:
- CPU utilization
- Memory usage
- Disk space
- Network interfaces
- System load
- Processes

### 2. Docker Containers (Built-in)
Use the built-in template: "Docker by Zabbix agent 2"

Requires Agent 2 with Docker plugin enabled.

### 3. Custom Templates

To create custom templates:

1. **Via Web Interface:**
   - Configuration → Templates → Create template
   - Add items, triggers, graphs
   - Export as YAML/XML

2. **Via API:**
   ```python
   # See docs/API_GUIDE.md for examples
   ```

3. **Import Template:**
   - Configuration → Templates → Import
   - Select file
   - Choose import rules
   - Import

## Template Best Practices

1. **Use Inheritance:** Base template → Specific template
2. **Use Macros:** For thresholds and parameters
3. **Tag Properly:** For organization and filtering
4. **Version Control:** Export templates regularly
5. **Test First:** On non-production hosts

## Example Custom Template Structure

```yaml
zabbix_export:
  version: '7.4'
  templates:
    - uuid: custom-uuid
      template: Custom Linux Extended
      name: Custom Linux Extended
      groups:
        - name: Templates/Operating systems
      items:
        - uuid: item-uuid
          name: Custom metric
          key: custom.metric
          delay: 1m
      triggers:
        - uuid: trigger-uuid
          expression: 'last(/Custom Linux Extended/custom.metric)>100'
          name: 'Custom metric too high'
```

## Recommended Templates to Import

1. **Official Zabbix Templates:**
   - https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates

2. **Community Templates:**
   - https://github.com/zabbix/community-templates
   - https://share.zabbix.com/

## Quick Start

```bash
# 1. Access web interface
http://localhost:8080

# 2. Go to Configuration → Templates

# 3. Select pre-installed templates to link to hosts

# 4. For custom templates:
#    - Create/import template
#    - Link to host group or individual hosts
#    - Verify data collection
```

## Template Examples

### Simple HTTP Check
```yaml
items:
  - name: Website Response Time
    type: SIMPLE
    key: web.page.perf[https://example.com]
    delay: 1m
    value_type: FLOAT
    units: s
```

### SNMP Network Interface
```yaml
items:
  - name: Interface {#IFNAME} inbound traffic
    type: SNMP_AGENT
    snmp_oid: 'IF-MIB::ifInOctets.{#SNMPINDEX}'
    key: 'net.if.in[{#IFNAME}]'
    delay: 1m
    preprocessing:
      - type: CHANGE_PER_SECOND
```

## Further Reading

- [Zabbix Template Guidelines](https://www.zabbix.com/documentation/current/en/manual/config/templates)
- [Template Macros](https://www.zabbix.com/documentation/current/en/manual/config/macros/user_macros)
- [Low-Level Discovery](https://www.zabbix.com/documentation/current/en/manual/discovery/low_level_discovery)
