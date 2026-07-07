from contains import contains
from mask import ip_to_int, network_range


def test_ip_to_int_bounds():
    assert ip_to_int("0.0.0.0") == 0
    assert ip_to_int("255.255.255.255") == 0xFFFFFFFF


def test_network_address():
    network, _ = network_range("192.168.1.0/24")
    assert network == ip_to_int("192.168.1.0")


def test_member_in_middle():
    assert contains("10.0.0.0/24", "10.0.0.100") is True


def test_far_outside():
    assert contains("10.0.0.0/24", "10.0.5.5") is False
