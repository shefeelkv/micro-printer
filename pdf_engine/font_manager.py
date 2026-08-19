import os
import requests
import logging
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.fonts import addMapping

logger = logging.getLogger(__name__)

# Cache directory for fonts
FONTS_DIR = os.path.join(settings.MEDIA_ROOT, 'fonts')
os.makedirs(FONTS_DIR, exist_ok=True)

# CRITICAL: Packaged local fonts directory to avoid runtime downloads on Vercel production
LOCAL_FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')

# CRITICAL: Google Fonts repository URLs used for downloading and registering required fallback/standard fonts.
GOOGLE_FONTS_MAP = {
    'Roboto': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-BoldItalic.ttf'
    },
    'Poppins': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-BoldItalic.ttf'
    },
    'Inter': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-BoldItalic.ttf'
    },
    'Open Sans': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/opensans/static/OpenSans-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/opensans/static/OpenSans-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/opensans/static/OpenSans-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/opensans/static/OpenSans-BoldItalic.ttf'
    },
    'Lato': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/lato/Lato-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/lato/Lato-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/lato/Lato-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/lato/Lato-BoldItalic.ttf'
    },
    'Montserrat': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-BoldItalic.ttf'
    },
    'Merriweather': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Bold.ttf',
        'italic': 'https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-Italic.ttf',
        'boldItalic': 'https://github.com/google/fonts/raw/main/ofl/merriweather/Merriweather-BoldItalic.ttf'
    },
    'Noto Sans': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf',
        'italic': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Italic.ttf',
        'boldItalic': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-BoldItalic.ttf'
    },
    'Noto Serif': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerif/NotoSerif-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerif/NotoSerif-Bold.ttf',
        'italic': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerif/NotoSerif-Italic.ttf',
        'boldItalic': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerif/NotoSerif-BoldItalic.ttf'
    },
    'Noto Sans Malayalam': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Bold.ttf'
    },
    'Noto Sans Devanagari': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf'
    },
    'Noto Sans Tamil': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Bold.ttf'
    },
    'Noto Sans Telugu': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTelugu/NotoSansTelugu-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTelugu/NotoSansTelugu-Bold.ttf'
    },
    'Noto Sans Kannada': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Bold.ttf'
    },
    'Noto Sans Arabic': {
        'normal': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf',
        'bold': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Bold.ttf'
    },
    'Noto Sans JP': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/sawarabigothic/SawarabiGothic-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/sawarabigothic/SawarabiGothic-Regular.ttf'
    },
    'Noto Sans SC': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/mashanzheng/MaShanZheng-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/mashanzheng/MaShanZheng-Regular.ttf'
    },
    'Meera': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/meera/Meera-Regular.ttf'
    },
    'Manjari': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/manjari/Manjari-Regular.ttf',
        'bold': 'https://github.com/google/fonts/raw/main/ofl/manjari/Manjari-Bold.ttf'
    },
    'Chilanka': {
        'normal': 'https://github.com/google/fonts/raw/main/ofl/chilanka/Chilanka-Regular.ttf'
    }
}

# Standard web safe fonts built into ReportLab
CORE_FONTS_FALLBACKS = {
    'Arial': 'Noto Sans-normal',
    'Times New Roman': 'Noto Serif-normal',
    'Georgia': 'Noto Serif-normal',
    'Courier New': 'Noto Sans-normal',
    'Helvetica': 'Noto Sans-normal',
    'Times-Roman': 'Noto Serif-normal',
    'Courier': 'Noto Sans-normal'
}

# Keep track of registered font families to avoid re-registering
_REGISTERED_FAMILIES = set()
_REGISTERED_NORMAL_VARIANTS = {}

def download_font_file(url, filename):
    """Downloads a font file from a URL and saves it to the cache directory."""
    # CRITICAL: First check if the font exists in our packaged local fonts directory
    local_path = os.path.join(LOCAL_FONTS_DIR, filename)
    if os.path.exists(local_path):
        return local_path

    dest_path = os.path.join(FONTS_DIR, filename)
    if os.path.exists(dest_path):
        return dest_path

    try:
        logger.info(f"Downloading font from {url} to {dest_path}")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(dest_path, 'wb') as f:
                f.write(response.content)
            return dest_path
        else:
            logger.error(f"Failed to download font from {url}. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error downloading font from {url}: {e}")
    
    return None

def register_font_family(family_name):
    """
    Downloads and registers a font family (Regular, Bold, Italic, BoldItalic) in ReportLab.
    Returns the name of the font to use (either the family_name or standard fallback).
    """
    if family_name in _REGISTERED_NORMAL_VARIANTS:
        return _REGISTERED_NORMAL_VARIANTS[family_name]

    if family_name in _REGISTERED_FAMILIES:
        return family_name

    # If it is a built-in standard font, map it and return
    if family_name in CORE_FONTS_FALLBACKS:
        target_family = CORE_FONTS_FALLBACKS[family_name]
        # We need to register the corresponding family name (e.g. 'Noto Sans' or 'Noto Serif')
        base_family = target_family.rsplit('-', 1)[0]
        register_font_family(base_family)
        return target_family

    # If it's a Google Font, download and register it
    if family_name in GOOGLE_FONTS_MAP:
        urls = GOOGLE_FONTS_MAP[family_name]
        registered_variants = {}
        
        for variant, url in urls.items():
            ext = os.path.splitext(url.split('?')[0])[1] or '.ttf'
            filename = f"{family_name.replace(' ', '')}-{variant}{ext}"
            font_path = download_font_file(url, filename)
            
            if font_path:
                variant_name = f"{family_name}-{variant}"
                try:
                    pdfmetrics.registerFont(TTFont(variant_name, font_path))
                    registered_variants[variant] = variant_name
                except Exception as e:
                    logger.error(f"Error registering font {variant_name} from {font_path}: {e}")

        # Check if we successfully registered the normal variant
        if 'normal' in registered_variants:
            normal = registered_variants['normal']
            bold = registered_variants.get('bold', normal)
            italic = registered_variants.get('italic', normal)
            boldItalic = registered_variants.get('boldItalic', bold)
            
            try:
                registerFontFamily(family_name, normal=normal, bold=bold, italic=italic, boldItalic=boldItalic)
                
                # Add mappings to ReportLab's internal fonts database
                addMapping(family_name, 0, 0, normal)
                addMapping(family_name, 1, 0, bold)
                addMapping(family_name, 0, 1, italic)
                addMapping(family_name, 1, 1, boldItalic)
                
                # Also add mappings for the variant names themselves to support direct lookup
                addMapping(normal, 0, 0, normal)
                addMapping(bold, 1, 0, bold)
                addMapping(italic, 0, 1, italic)
                addMapping(boldItalic, 1, 1, boldItalic)
                
                # Directly map family name in _ps2tt_map to prevent ps2tt splitting failures
                from reportlab.lib.fonts import _ps2tt_map
                _ps2tt_map[family_name.lower()] = (family_name.lower(), 0, 0)
                _ps2tt_map[normal.lower()] = (family_name.lower(), 0, 0)
                _ps2tt_map[bold.lower()] = (family_name.lower(), 1, 0)
                _ps2tt_map[italic.lower()] = (family_name.lower(), 0, 1)
                _ps2tt_map[boldItalic.lower()] = (family_name.lower(), 1, 1)
                
                _REGISTERED_FAMILIES.add(family_name)
                _REGISTERED_NORMAL_VARIANTS[family_name] = normal
                logger.info(f"Successfully registered font family: {family_name}")
                return normal
            except Exception as e:
                logger.error(f"Error registering font family structure for {family_name}: {e}")
        
    # If the font is a custom font uploaded by the user, we will load it from the database/media
    from projects.models import CustomFont
    try:
        custom_font = CustomFont.objects.filter(name=family_name).first()
        if custom_font and custom_font.ttf_file:
            font_path = custom_font.ttf_file.path
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(family_name, font_path))
                # For custom uploaded fonts, we might only have one style, so map all variants to it
                registerFontFamily(family_name, normal=family_name, bold=family_name, italic=family_name, boldItalic=family_name)
                
                # Add mapping for the custom font
                addMapping(family_name, 0, 0, family_name)
                addMapping(family_name, 1, 0, family_name)
                addMapping(family_name, 0, 1, family_name)
                addMapping(family_name, 1, 1, family_name)
                
                _REGISTERED_FAMILIES.add(family_name)
                _REGISTERED_NORMAL_VARIANTS[family_name] = family_name
                return family_name
    except Exception as e:
        logger.error(f"Error checking/registering custom uploaded font {family_name}: {e}")

    # Final fallback if nothing worked
    logger.warning(f"Could not load font '{family_name}', falling back to Noto Sans.")
    return 'Noto Sans-normal'




# CRITICAL: Fallback font families list for language support and text segmentation.
FALLBACK_FONTS = [
    'Noto Sans Malayalam',
    'Noto Sans Devanagari',
    'Noto Sans Tamil',
    'Noto Sans Telugu',
    'Noto Sans Kannada',
    'Noto Sans Arabic',
    'Noto Sans JP',
    'Noto Sans SC',
]

# Cache for character to font supports checking
_FONT_GLYPH_CACHE = {}

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RTL_SUPPORT = True
except ImportError:
    HAS_RTL_SUPPORT = False

def prepare_fallback_fonts():
    """Download and pre-register all fallback fonts."""
    for font_name in FALLBACK_FONTS:
        register_font_family(font_name)
    # Ensure default Noto Sans / Noto Serif are also loaded
    register_font_family('Noto Sans')
    register_font_family('Noto Serif')

def get_registered_font_name_for_checking(family_name):
    """Retrieve the actual TTFont name variant to check character mapping."""
    variant_name = f"{family_name}-normal"
    try:
        pdfmetrics.getFont(variant_name)
        return variant_name
    except Exception:
        try:
            pdfmetrics.getFont(family_name)
            return family_name
        except Exception:
            return None

def font_supports_char(font_family_name, char):
    """Checks if the given font supports the unicode character."""
    cache_key = (font_family_name, char)
    if cache_key in _FONT_GLYPH_CACHE:
        return _FONT_GLYPH_CACHE[cache_key]

    supports = False
    font_name = get_registered_font_name_for_checking(font_family_name)
    if font_name:
        try:
            font = pdfmetrics.getFont(font_name)
            if hasattr(font, 'face') and hasattr(font.face, 'charToGlyph'):
                supports = ord(char) in font.face.charToGlyph
            else:
                # Built-in Type1 standard fonts support Latin-1
                supports = ord(char) < 256
        except Exception:
            supports = False
    else:
        # If font not registered, check if we mapped it or if it is standard Latin
        supports = ord(char) < 256

    _FONT_GLYPH_CACHE[cache_key] = supports
    return supports

def get_font_for_char(char, primary_font, current_run_font=None):
    """Resolves the best font family that supports the given character."""
    # CRITICAL: Explicitly check for Malayalam Unicode characters (U+0D00 to U+0D7F)
    # and map them directly to a Malayalam font to avoid fallback/shaping issues.
    if 0x0D00 <= ord(char) <= 0x0D7F:
        if primary_font in ['Noto Sans Malayalam', 'Meera', 'Manjari', 'Chilanka']:
            return primary_font
        if current_run_font in ['Noto Sans Malayalam', 'Meera', 'Manjari', 'Chilanka']:
            return current_run_font
        return 'Noto Sans Malayalam'

    # Spaces and common punctuation can inherit current run font to prevent text splitting
    is_neutral = char.isspace() or char in ".,;:!?()[]{}-_+=*/\\|'\"`@#$%-^&~<>\xa0"
    
    if is_neutral and current_run_font:
        if font_supports_char(current_run_font, char):
            return current_run_font
        if font_supports_char(primary_font, char):
            return primary_font

    # Check if primary font supports it
    if font_supports_char(primary_font, char):
        return primary_font

    # Check if current run font supports it (if it is a fallback)
    if current_run_font and font_supports_char(current_run_font, char):
        return current_run_font

    # Search other fallback fonts
    for fallback_font in FALLBACK_FONTS:
        if font_supports_char(fallback_font, char):
            return fallback_font

    return primary_font

def apply_font_fallback(text, primary_font):
    """
    Segments plain text into runs, wrapping characters not supported by primary_font
    into <font name="FALLBACK_FONT">...</font> tags.
    """
    if not text:
        return ""

    # Shape and reorder RTL text if Arabic characters are present
    # (Arabic block: 0x0600 - 0x06FF, 0x0750 - 0x077F, etc.)
    has_arabic = any(0x0600 <= ord(c) <= 0x06FF for c in text)
    if has_arabic and HAS_RTL_SUPPORT:
        try:
            reshaped = arabic_reshaper.reshape(text)
            text = get_display(reshaped)
        except Exception as e:
            logger.error(f"Error reshaping RTL text: {e}")

    runs = []
    current_font = None
    current_text = []

    # Map core font name to registered name
    base_font = CORE_FONTS_FALLBACKS.get(primary_font, primary_font)

    for char in text:
        font_name = get_font_for_char(char, base_font, current_font)
        if font_name == current_font:
            current_text.append(char)
        else:
            if current_text:
                runs.append((current_font, "".join(current_text)))
            current_font = font_name
            current_text = [char]

    if current_text:
        runs.append((current_font, "".join(current_text)))

    # Assemble output with font tags
    output = []
    for font_name, run_text in runs:
        # Escape XML entities
        escaped_run = run_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if font_name == base_font:
            output.append(escaped_run)
        else:
            output.append(f'<font name="{font_name}">{escaped_run}</font>')

    return "".join(output)
