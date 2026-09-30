"""Document presentation context shared by HTML and PDF rendering."""

from constance import config

from .nofo import get_cover_image, get_step_2_section


def get_nofo_document_context(nofo):
    # The theme is formatted like "landscape-cdc-blue".
    orientation, opdiv, colour = nofo.theme.split("-")
    return {
        "nofo_theme_base": "{}-{}".format(opdiv, colour),
        "nofo_opdiv": opdiv,
        "nofo_theme_orientation": orientation,
        "nofo_cover_image": get_cover_image(nofo),
        "step_2_section": get_step_2_section(nofo),
        "assistance_listing_on_cover_enabled": (
            config.HHS_NOFO_ASSISTANCE_LISTING_ENABLED
            and config.HHS_NOFO_ASSISTANCE_LISTING_ON_COVER_ENABLED
        ),
    }
