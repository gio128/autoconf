# TEMPLATE DE CONFIGURAÇÃO DO SWITCH

# VLANs

VLAN_COMMANDS = [
    "vlan 10 name VLAN_DADOS",
    "vlan 20 name VLAN_VOZ",
    "vlan 50 name VLAN_SEGURANCA",
]


CONFIG_COMMANDS = [

    "hostname SW-AUTOCONF-01",

    # INTERFACES

    "interface range FastEthernet1/3 - 9",
    "description ACCESS E VOICE",
    "switchport mode access",
    "switchport access vlan 10",
    "switchport voice vlan 20",
    "spanning-tree portfast",
    "no shutdown",
    "exit",

    "interface range FastEthernet1/10 - 11",
    "description SEGURANCA",
    "switchport mode access",
    "switchport access vlan 50",
    "spanning-tree portfast",
    "no shutdown",
    "exit",

    "interface range FastEthernet1/12 - 13",
    "shutdown",
    "exit",

    "interface range FastEthernet1/14 - 15",
    "description UPLINK",
    "switchport mode trunk",
    "switchport trunk allowed vlan 1,2,10,20,50,1002-1005",
    "no shutdown",
    "exit",

    "ip default-gateway 192.168.99.1",
    "no ip domain lookup",
    "service password-encryption",
    "username admin privilege 15 secret 0 12345678",

]