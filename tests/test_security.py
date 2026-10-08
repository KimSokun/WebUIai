import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.tools.sandbox import LocalFilesSandboxTool
from backend.auth import OwnerAuthority
from backend.config import system_config

def test_sandbox_path_traversal_blocked():
    sandbox = LocalFilesSandboxTool()
    
    # Attack 1: Unix path traversal
    attack_1 = "../../../Windows/System32/calc.exe"
    blocked = False
    try:
        sandbox._resolve_and_validate(attack_1)
    except PermissionError as e:
        blocked = True
        assert "Security Alert: Path traversal blocked" in str(e)
    assert blocked, "Path traversal attack 1 was NOT blocked!"

    # Attack 2: Windows backslash traversal
    attack_2 = "..\\..\\..\\Windows\\System32\\cmd.exe"
    blocked_2 = False
    try:
        sandbox._resolve_and_validate(attack_2)
    except PermissionError as e:
        blocked_2 = True
        assert "Security Alert: Path traversal blocked" in str(e)
    assert blocked_2, "Path traversal attack 2 was NOT blocked!"
    print(" - Path traversal attacks successfully blocked [PASS]")

def test_sandbox_valid_access():
    sandbox = LocalFilesSandboxTool()
    valid_path = sandbox._resolve_and_validate("welcome.txt")
    assert valid_path.exists()
    assert valid_path.name == "welcome.txt"
    print(" - Sandboxed workspace access permitted [PASS]")

def test_owner_authority_validation():
    class MockRequest:
        def __init__(self, host, token=None):
            self.client = type("Client", (), {"host": host})()
            self.headers = {"X-Owner-Token": token} if token else {}

    # Valid localhost request
    local_req = MockRequest("127.0.0.1")
    assert OwnerAuthority.is_authenticated_owner(local_req) is True

    # Valid external request with token
    token_req = MockRequest("192.168.1.50", token=system_config.owner.auth_token)
    assert OwnerAuthority.is_authenticated_owner(token_req) is True

    # Unauthorized external request
    unauth_req = MockRequest("192.168.1.50")
    assert OwnerAuthority.is_authenticated_owner(unauth_req) is False
    print(" - Owner authority validation [PASS]")

if __name__ == "__main__":
    print("Running Security Tests...")
    test_sandbox_path_traversal_blocked()
    test_sandbox_valid_access()
    test_owner_authority_validation()
    print("ALL SECURITY TESTS PASSED [PASS]!")
