import pytest

#this is a test that will always pass, used to test the github actions
@pytest.fixture(scope="module")

def test_always_true():
    x = 0
    assert x == 0

