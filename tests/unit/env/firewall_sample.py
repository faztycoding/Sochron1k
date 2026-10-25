"""Fixture for parse_firewall_json: the output of host_report.FIREWALL_SCRIPT, the one PowerShell
command collect_facts runs (powershell.exe -NoProfile -NonInteractive -EncodedCommand), captured on
the owner's Windows 11 Pro PC (build 26200, Windows PowerShell 5.1) on 2026-10-25.

Trimmed to ten system rules plus the three profiles (contract ENV-001 v1.5, review r5 F53): no
program paths or app names. The only address in the capture, the link-local scope fe80::/64 of
CoreNet-ICMP6-RA-In, is replaced by the RFC 3849 documentation prefix 2001:db8::/64. Everything else
(key order, "RPC" as an ICMP local port, port lists and ranges, keywords) is as Windows returned it.
"""

SAMPLE = (
    '{"rules":['
    '{"name":"CoreNet-DHCP-In","protocol":"UDP","profiles":"Any","local_ports":["68"],"remote_addresses":["Any"]},'
    '{"name":"CoreNet-DHCPV6-In","protocol":"UDP","profiles":"Any","local_ports":["546"],"remote_addresses":["Any"]},'
    '{"name":"CoreNet-ICMP6-RA-In","protocol":"ICMPv6","profiles":"Any","local_ports":["RPC"],'
    '"remote_addresses":["2001:db8::/64"]},'
    '{"name":"CoreNet-ICMP4-DUFRAG-In","protocol":"ICMPv4","profiles":"Any","local_ports":["RPC"],"remote_addresses":["Any"]},'
    '{"name":"CoreNet-IGMP-In","protocol":"2","profiles":"Any","local_ports":["Any"],"remote_addresses":["Any"]},'
    '{"name":"CoreNet-IPv6-In","protocol":"41","profiles":"Any","local_ports":["Any"],"remote_addresses":["Any"]},'
    '{"name":"DeliveryOptimization-TCP-In","protocol":"TCP","profiles":"Any","local_ports":["7680"],'
    '"remote_addresses":["Any"]},'
    '{"name":"NVS-FrameServer-In-TCP-NoScope","protocol":"TCP","profiles":"Any","local_ports":["554","8554-8558"],'
    '"remote_addresses":["LocalSubnet"]},'
    '{"name":"MDNS-In-UDP-Private-Active","protocol":"UDP","profiles":"Private","local_ports":["5353"],'
    '"remote_addresses":["LocalSubnet"]},'
    '{"name":"WFDPRINT-SPOOL-In-Active","protocol":"Any","profiles":"Public","local_ports":["Any"],"remote_addresses":["Any"]}'
    '],"profiles":['
    '{"name":"Domain","enabled":"True","default_inbound_action":"Block"},'
    '{"name":"Private","enabled":"True","default_inbound_action":"Block"},'
    '{"name":"Public","enabled":"True","default_inbound_action":"Block"}'
    ']}'
)
