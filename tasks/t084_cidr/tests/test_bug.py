from contains import contains
from mask import ip_to_int, network_range


def test_broadcast_address():
    network, broadcast = network_range("192.168.1.0/24")
    assert network == ip_to_int("192.168.1.0")
    assert broadcast == ip_to_int("192.168.1.255")


def test_network_address_is_member():
    assert contains("10.0.0.0/24", "10.0.0.0") is True
