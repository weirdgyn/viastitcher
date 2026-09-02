# localization.py

import gettext
import os

def setup_locale():
    """Initialize localization for ViaStitcher."""
    locale_dir = os.path.join(os.path.dirname(__file__), 'locale')
    
    try:
        translation = gettext.translation(
            'viastitcher',
            localedir=locale_dir,
            fallback=True
        )
        translation.install()
        return translation.gettext
    except Exception:
        # Fallback to English (no translation)
        return gettext.gettext

_ = setup_locale()
