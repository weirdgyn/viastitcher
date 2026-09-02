# localization.py

import gettext
import locale
import os


DOMAIN = "viastitcher"


def _language_candidates():
    """Return locale names, preferring KiCad/wx's active UI locale."""
    override = os.environ.get("VIASTITCHER_LANGUAGE")
    if override:
        return [override]

    try:
        import wx

        get_locale = getattr(wx, "GetLocale", None)
        if get_locale:
            current_locale = get_locale()
            if current_locale:
                name = current_locale.GetCanonicalName()
                if name:
                    return [name]

        language_info = wx.Locale.GetLanguageInfo(wx.Locale.GetSystemLanguage())
        if language_info and language_info.CanonicalName:
            return [language_info.CanonicalName]
    except (AttributeError, ImportError, RuntimeError, TypeError):
        pass

    try:
        system_locale = locale.getlocale()[0]
    except locale.Error:
        system_locale = None
    return [system_locale] if system_locale else None


def setup_locale():
    """Initialize localization for ViaStitcher."""
    locale_dir = os.path.join(os.path.dirname(__file__), 'locale')
    languages = _language_candidates()
    
    try:
        # wxFormBuilder-generated Python calls gettext.gettext. Configure its
        # process-wide default domain before that module is imported.
        gettext.bindtextdomain(DOMAIN, locale_dir)
        gettext.textdomain(DOMAIN)
        if languages:
            os.environ["LANGUAGE"] = languages[0]

        translation = gettext.translation(
            DOMAIN,
            localedir=locale_dir,
            languages=languages,
            fallback=True,
        )
        translation.install()
        return translation.gettext
    except (OSError, ValueError):
        return gettext.NullTranslations().gettext

_ = setup_locale()
