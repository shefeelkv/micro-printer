import os
import subprocess
import tempfile
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter, A5, landscape
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Spacer
from reportlab.lib import colors

from .font_manager import register_font_family, CORE_FONTS_FALLBACKS, prepare_fallback_fonts
from .parser import HTMLToFlowablesParser, get_color, safe_float, safe_int

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas renderer that computes the total page count before printing page numbers,
    and draws document-wide decorations like headers, footers, borders, and watermarks.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        # Save state dict for second pass
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        # Retrieve settings passed to this canvas
        pdf_settings = getattr(self, 'pdf_settings', {})
        
        # Dimensions
        page_width, page_height = self._pagesize
        
        # Margins (in points)
        margin_left = safe_float(pdf_settings.get('margin_left'), 36)
        margin_right = safe_float(pdf_settings.get('margin_right'), 36)
        margin_top = safe_float(pdf_settings.get('margin_top'), 36)
        margin_bottom = safe_float(pdf_settings.get('margin_bottom'), 36)

        # Typography style for headers/footers
        font_family = pdf_settings.get('font_family', 'Helvetica')
        registered_font = register_font_family(font_family)
        
        # Background and Watermark are now drawn in the first-pass 'onPage' callback (draw_background_and_watermark)
        # to prevent them from layering on top of and covering the text/content.

        # 3. Header Drawing
        header_text = pdf_settings.get('header_text', '').strip()
        author_name = pdf_settings.get('author_name', '').strip()
        date_str = pdf_settings.get('date_str', '').strip()
        
        header_components = []
        if header_text:
            header_components.append(header_text)
        if author_name:
            header_components.append(f"Author: {author_name}")
        if date_str:
            header_components.append(date_str)
            
        full_header_text = " | ".join(header_components)
        
        if full_header_text:
            self.saveState()
            self.setFont(registered_font, 8)
            self.setFillColor(get_color(pdf_settings.get('text_color', '#666666'), colors.HexColor('#666666')))
            # Centered or aligned above top margin
            self.drawString(margin_left, page_height - margin_top + 10, full_header_text)
            # Add thin header line
            self.setStrokeColor(get_color(pdf_settings.get('border_color', '#CCCCCC'), colors.HexColor('#CCCCCC')))
            self.setLineWidth(0.5)
            self.line(margin_left, page_height - margin_top + 5, page_width - margin_right, page_height - margin_top + 5)
            self.restoreState()

        # 4. Footer Drawing
        footer_text = pdf_settings.get('footer_text', '').strip()
        show_page_num = pdf_settings.get('show_page_numbers', True)
        
        if footer_text or show_page_num:
            self.saveState()
            self.setFont(registered_font, 8)
            self.setFillColor(get_color(pdf_settings.get('text_color', '#666666'), colors.HexColor('#666666')))
            
            # Left footer text
            if footer_text:
                self.drawString(margin_left, margin_bottom - 15, footer_text)
                
            # Right footer page numbers
            if show_page_num:
                page_str = f"Page {self._pageNumber} of {total_pages}"
                self.drawRightString(page_width - margin_right, margin_bottom - 15, page_str)
                
            # Thin footer line
            self.setStrokeColor(get_color(pdf_settings.get('border_color', '#CCCCCC'), colors.HexColor('#CCCCCC')))
            self.setLineWidth(0.5)
            self.line(margin_left, margin_bottom - 5, page_width - margin_right, margin_bottom - 5)
            self.restoreState()

        # 5. Page Border
        show_border = pdf_settings.get('show_page_border', False)
        if show_border:
            self.saveState()
            border_color_hex = pdf_settings.get('page_border_color', '#000000')
            border_color = get_color(border_color_hex, colors.black)
            self.setStrokeColor(border_color)
            self.setLineWidth(1)
            # Draw rectangle just inside the margins
            self.rect(margin_left - 4, margin_bottom - 4, 
                      page_width - margin_left - margin_right + 8, 
                      page_height - margin_top - margin_bottom + 8, 
                      fill=0, stroke=1)
            self.restoreState()

def draw_background_and_watermark(canvas, doc):
    """Draws background color and watermark on the page. Must be drawn in the first pass (behind text)."""
    pdf_settings = getattr(canvas, 'pdf_settings', {})
    
    # 1. Background Color
    bg_color_hex = pdf_settings.get('bg_color')
    if bg_color_hex and bg_color_hex != 'transparent':
        bg_color = get_color(bg_color_hex)
        if bg_color:
            canvas.saveState()
            canvas.setFillColor(bg_color)
            canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
            canvas.restoreState()

    # 2. Watermark Drawing
    watermark_text = pdf_settings.get('watermark_text', '').strip()
    if watermark_text:
        canvas.saveState()
        font_family = pdf_settings.get('font_family', 'Helvetica')
        registered_font = register_font_family(font_family)
        canvas.setFont(registered_font, 48)
        watermark_color_hex = pdf_settings.get('watermark_color', '#E5E5E5')
        watermark_color = get_color(watermark_color_hex, colors.HexColor('#E5E5E5'))
        opacity = safe_float(pdf_settings.get('watermark_opacity'), 0.15)
        
        # Create a transparent color
        r, g, b = watermark_color.rgb()
        canvas.setFillColor(colors.Color(r, g, b, alpha=opacity))
        
        angle = safe_float(pdf_settings.get('watermark_angle'), 45)
        
        # Centered rotation
        canvas.translate(doc.pagesize[0] / 2.0, doc.pagesize[1] / 2.0)
        canvas.rotate(angle)
        canvas.drawCentredString(0, 0, watermark_text)
        canvas.restoreState()

def generate_pdf(html_content, pdf_settings, output_stream):
    """
    Renders HTML content to PDF using headless Chrome.
    Fully supports complex text layout (CTL) and OpenType shaping for Malayalam Unicode.
    """
    # Pre-register/download fallback fonts to media/fonts/ cached directory
    prepare_fallback_fonts()

    # 1. Map settings to CSS variables/rules
    paper_size = pdf_settings.get('paper_size', 'A4').upper()
    is_landscape = pdf_settings.get('orientation', 'portrait').lower() == 'landscape'
    orientation = 'landscape' if is_landscape else 'portrait'
    
    margin_left = safe_float(pdf_settings.get('margin_left'), 36)
    margin_right = safe_float(pdf_settings.get('margin_right'), 36)
    margin_top = safe_float(pdf_settings.get('margin_top'), 36)
    margin_bottom = safe_float(pdf_settings.get('margin_bottom'), 36)
    
    columns = safe_int(pdf_settings.get('columns'), 1)
    # Cap column count between 1 and 6 for sanity
    columns = max(1, min(6, columns))
    
    column_spacing = safe_float(pdf_settings.get('column_spacing'), 12)
    
    bg_color = pdf_settings.get('bg_color', 'transparent')
    if bg_color == 'transparent':
        bg_color = '#ffffff'
        
    text_color = pdf_settings.get('text_color', '#000000')
    font_family = pdf_settings.get('font_family', 'Noto Sans')
    font_size = safe_float(pdf_settings.get('font_size'), 10)
    line_height = safe_float(pdf_settings.get('line_height'), 1.3)
    
    # Border
    show_border = pdf_settings.get('show_page_border', False)
    border_color = pdf_settings.get('page_border_color', '#000000')
    
    # Watermark
    watermark_text = pdf_settings.get('watermark_text', '').strip()
    watermark_color = pdf_settings.get('watermark_color', '#E5E5E5')
    watermark_opacity = safe_float(pdf_settings.get('watermark_opacity'), 0.15)
    watermark_angle = safe_float(pdf_settings.get('watermark_angle'), 45)
    
    # Headers/Footers
    header_text = pdf_settings.get('header_text', '').strip()
    author_name = pdf_settings.get('author_name', '').strip()
    date_str = pdf_settings.get('date_str', '').strip()
    
    header_components = []
    if header_text:
        header_components.append(header_text)
    if author_name:
        header_components.append(f"Author: {author_name}")
    if date_str:
        header_components.append(date_str)
    full_header_text = " | ".join(header_components)
    
    footer_text = pdf_settings.get('footer_text', '').strip()
    show_page_numbers = pdf_settings.get('show_page_numbers', True)
    
    # 2. Build local font @font-face rules
    font_faces = []
    from .font_manager import GOOGLE_FONTS_MAP, FONTS_DIR
    from projects.models import CustomFont
    
    # Add Google Fonts
    for fam, variants in GOOGLE_FONTS_MAP.items():
        for variant, url in variants.items():
            ext = os.path.splitext(url.split('?')[0])[1] or '.ttf'
            filename = f"{fam.replace(' ', '')}-{variant}{ext}"
            font_path = os.path.join(FONTS_DIR, filename).replace('\\', '/')
            if os.path.exists(font_path):
                # Map regular, bold, italic
                weight = 'bold' if 'bold' in variant.lower() else 'normal'
                style = 'italic' if 'italic' in variant.lower() else 'normal'
                font_faces.append(f"""
                @font-face {{
                    font-family: '{fam}';
                    font-weight: {weight};
                    font-style: {style};
                    src: url('file:///{font_path}');
                }}
                """)
                
    # Add Custom Uploaded Fonts
    for custom_font in CustomFont.objects.all():
        if custom_font.ttf_file:
            font_path = custom_font.ttf_file.path.replace('\\', '/')
            if os.path.exists(font_path):
                font_faces.append(f"""
                @font-face {{
                    font-family: '{custom_font.name}';
                    src: url('file:///{font_path}');
                }}
                """)
                
    font_faces_css = "\n".join(font_faces)
    
    # 3. Construct HTML wrapper with CSS paged media
    border_css = ""
    if show_border:
        border_css = f"""
        .page-border {{
            position: fixed;
            top: calc({margin_top}pt - 4pt);
            bottom: calc({margin_bottom}pt - 4pt);
            left: calc({margin_left}pt - 4pt);
            right: calc({margin_right}pt - 4pt);
            border: 1px solid {border_color};
            pointer-events: none;
            z-index: 9999;
        }}
        """
        
    watermark_css = ""
    if watermark_text:
        watermark_css = f"""
        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate({watermark_angle}deg);
            font-size: 48pt;
            color: {watermark_color};
            opacity: {watermark_opacity};
            font-family: '{font_family}', 'Manjari', 'Chilanka', 'Noto Sans Malayalam', sans-serif;
            white-space: nowrap;
            pointer-events: none;
            z-index: -1000;
        }}
        """
        
    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{font_faces_css}

@page {{
    size: {paper_size} {orientation};
    margin-top: {margin_top}pt;
    margin-bottom: {margin_bottom}pt;
    margin-left: {margin_left}pt;
    margin-right: {margin_right}pt;
}}

body {{
    font-family: '{font_family}', 'Manjari', 'Chilanka', 'Noto Sans Malayalam', sans-serif;
    font-size: {font_size}pt;
    line-height: {line_height};
    color: {text_color};
    background-color: {bg_color};
    margin: 0;
    padding: 0;
}}

.content-container {{
    column-count: {columns};
    column-gap: {column_spacing}pt;
    width: 100%;
}}

/* Ensure headings, images, and tables break cleanly */
h1, h2, h3, h4, h5, h6, table, img, tr, td, th {{
    break-inside: avoid;
}}

{border_css}
{watermark_css}
</style>
</head>
<body>
{ '<div class="page-border"></div>' if show_border else '' }
{ f'<div class="watermark">{watermark_text}</div>' if watermark_text else '' }
<div class="content-container">
    {html_content}
</div>
</body>
</html>
"""
    
    # 4. Save HTML to temp files under MEDIA_ROOT
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_html_fd, temp_html_path = tempfile.mkstemp(suffix='.html', dir=temp_dir)
    temp_pdf_fd, temp_pdf_path = tempfile.mkstemp(suffix='.pdf', dir=temp_dir)
    
    try:
        with os.fdopen(temp_html_fd, 'w', encoding='utf-8') as f:
            f.write(html_template)
        os.close(temp_pdf_fd) # Close descriptor so Chrome can write to it
        
        # 5. Build Headless Chrome print command
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--allow-file-access-from-files",
            f"--print-to-pdf={temp_pdf_path}"
        ]
        
        # Print headers and footers using Chrome's template engine
        if full_header_text or footer_text or show_page_numbers:
            cmd.append("--display-header-footer")
            
            # Header template
            if full_header_text:
                header_html = f"<div style='font-size: 8px; font-family: sans-serif; color: {text_color}; width: 100%; margin-left: {margin_left}pt; margin-right: {margin_right}pt; border-bottom: 0.5px solid #CCCCCC; padding-bottom: 3px; display: flex; justify-content: space-between;'><span>{full_header_text}</span></div>"
                cmd.append(f"--header-template={header_html}")
            else:
                cmd.append("--header-template=<div style='display:none;'></div>")
                
            # Footer template
            footer_components = []
            if footer_text:
                footer_components.append(f"<span>{footer_text}</span>")
            else:
                footer_components.append("<span></span>")
            if show_page_numbers:
                footer_components.append("<span>Page <span class='pageNumber'></span> of <span class='totalPages'></span></span>")
            
            footer_html = f"<div style='font-size: 8px; font-family: sans-serif; color: {text_color}; width: 100%; margin-left: {margin_left}pt; margin-right: {margin_right}pt; border-top: 0.5px solid #CCCCCC; padding-top: 3px; display: flex; justify-content: space-between;'>{''.join(footer_components)}</div>"
            cmd.append(f"--footer-template={footer_html}")
            
        cmd.append(temp_html_path)
        
        # Run subprocess to compile PDF
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Read the generated PDF into Django output stream
        with open(temp_pdf_path, 'rb') as f:
            output_stream.write(f.read())
            
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        except Exception:
            pass
