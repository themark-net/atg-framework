import atg


def test_version_and_attribution():
    assert atg.__version__ == "0.1.0"
    assert "2607.01942" in atg.__attribution__
    assert "does not propose" in atg.__doc__.lower() or "not" in atg.__doc__.lower()
