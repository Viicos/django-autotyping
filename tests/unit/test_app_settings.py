from django_autotyping.app_settings import AutotypingSettings


class MockSettings:
    """A mock class that supports getattr."""

    AUTOTYPING = {
        "IGNORE": ["DJA001"],
        "STUBS_GENERATION": {
            "ALLOW_PLAIN_MODEL_REFERENCES": False,  # Default is `True`
        },
        "CODE_GENERATION": {
            "TYPE_CHECKING_BLOCK": False,  # Default is `True`
        },
    }


def test_autotyping_settings():
    settings = AutotypingSettings.from_django_settings(MockSettings())

    assert settings.IGNORE == ["DJA001"]
    assert settings.STUBS_GENERATION.ALLOW_PLAIN_MODEL_REFERENCES is False
    assert settings.CODE_GENERATION.TYPE_CHECKING_BLOCK is False
