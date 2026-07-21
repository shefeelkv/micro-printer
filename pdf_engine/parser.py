import os
import re
from bs4 import BeautifulSoup
from django.conf import settings
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from .font_manager import register_font_family, apply_font_fallback

def safe_float(val, default=0.0):
    if val is None or str(val).strip() == '':
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    if val is None or str(val).strip() == '':
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def get_color(color_hex_or_rgb, default=colors.black):
    """Converts hex, rgb, or color names to ReportLab Color objects."""
    if not color_hex_or_rgb:
        return default
    
    # Check if ReportLab color object already
    if isinstance(color_hex_or_rgb, colors.Color):
        return color_hex_or_rgb
        
    s = str(color_hex_or_rgb).strip().lower()
    
    # Handle transparent
    if s == 'transparent' or s == 'none':
        return None
        
    # Handle hex colors (e.g., #ffffff or #fff)
    if s.startswith('#'):
        try:
            return colors.HexColor(s)
        except Exception:
            return default
            
    # Handle rgb/rgba colors (e.g., rgb(255, 255, 255) or rgba(255, 255, 255, 1))
    rgb_match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)', s)
    if rgb_match:
        try:
            r, g, b = map(int, rgb_match.groups()[:3])
            a = float(rgb_match.group(4)) if rgb_match.group(4) else 1.0
            return colors.Color(r/255.0, g/255.0, b/255.0, alpha=a)
        except Exception:
            return default

    # Predefined colors
    color_map = {
        'yellow': colors.yellow,
        'green': colors.green,
        'pink': colors.pink,
        'blue': colors.blue,
        'orange': colors.orange,
        'purple': colors.purple,
        'red': colors.red,
        'black': colors.black,
        'white': colors.white,
        'gray': colors.gray,
        'lightgray': colors.lightgrey
    }
    return color_map.get(s, default)

def clean_inline_html(element, primary_font='Helvetica'):
    """
    Recursively converts BeautifulSoup HTML elements to ReportLab compatible markup string.
    Supported ReportLab tags: <b>, <i>, <u>, <font>, <a href="...">, <br/>.
    """
    if element is None:
        return ""
    
    if isinstance(element, str):
        return apply_font_fallback(element, primary_font)

    # If it is a tag, process its children and wrap them in appropriate XML markup
    inner_markup = "".join(clean_inline_html(child, primary_font) for child in element.children)
    tag_name = element.name.lower()

    if tag_name in ['strong', 'b']:
        return f"<b>{inner_markup}</b>"
    elif tag_name in ['em', 'i']:
        return f"<i>{inner_markup}</i>"
    elif tag_name in ['u', 'ins']:
        return f"<u>{inner_markup}</u>"
    elif tag_name == 'br':
        return "<br/>"
    elif tag_name == 'a':
        href = element.get('href', '#')
        return f'<a href="{href}" color="blue"><u>{inner_markup}</u></a>'
    elif tag_name in ['span', 'mark']:
        # Extract style or class for coloring / highlighting
        style = element.get('style', '')
        color_val = None
        bg_val = None
        
        # Simple inline CSS style parser
        if style:
            styles = dict(item.split(':', 1) for item in style.split(';') if ':' in item)
            styles = {k.strip().lower(): v.strip().lower() for k, v in styles.items()}
            
            color_val = styles.get('color')
            bg_val = styles.get('background-color') or styles.get('background')
            
        # Check standard highlight classes if present (e.g. from CKEditor markers)
        cls = element.get('class', [])
        if any('marker' in c for c in cls):
            for c in cls:
                if 'yellow' in c: bg_val = '#FFFF00'
                elif 'green' in c: bg_val = '#00FF00'
                elif 'pink' in c: bg_val = '#FFC0CB'
                elif 'blue' in c: bg_val = '#ADD8E6'
                elif 'orange' in c: bg_val = '#FFA500'
                elif 'purple' in c: bg_val = '#800080'
                
        font_attrs = []
        if color_val:
            # We must convert to hex format for ReportLab font tag
            rl_color = get_color(color_val)
            if rl_color:
                font_attrs.append(f'color="{rl_color.hexval()}"')
        if bg_val:
            rl_bg = get_color(bg_val)
            if rl_bg:
                font_attrs.append(f'backColor="{rl_bg.hexval()}"')
                
        if font_attrs:
            return f'<font {" ".join(font_attrs)}>{inner_markup}</font>'
        
        return inner_markup
    
    # Default fallback: just return child contents
    return inner_markup

class HTMLToFlowablesParser:
    def __init__(self, html_content, settings_dict, column_width):
        self.html_content = html_content
        self.settings = settings_dict
        self.column_width = column_width
        self.story = []
        
        # Setup styles
        self._init_styles()

    def _init_styles(self):
        """Initializes ParagraphStyle objects based on user settings."""
        # 1. Base Font family registration
        font_family = self.settings.get('font_family', 'Helvetica')
        registered_font = register_font_family(font_family)
        
        heading_font = self.settings.get('heading_font', font_family)
        registered_heading_font = register_font_family(heading_font)

        # 2. Map alignments
        align_map = {
            'left': TA_LEFT,
            'center': TA_CENTER,
            'right': TA_RIGHT,
            'justify': TA_JUSTIFY
        }
        alignment = align_map.get(self.settings.get('text_align', 'left'), TA_LEFT)

        # 3. Colors
        text_color = get_color(self.settings.get('text_color', '#000000'))
        heading_color = get_color(self.settings.get('heading_color', '#000000'))

        # 4. Dimension Settings
        font_size = safe_float(self.settings.get('font_size'), 9)
        line_height = safe_float(self.settings.get('line_height'), 1.2) * font_size
        paragraph_spacing = safe_float(self.settings.get('paragraph_spacing'), 6)
        letter_spacing = safe_float(self.settings.get('letter_spacing'), 0)
        word_spacing = safe_float(self.settings.get('word_spacing'), 0)

        # Define body style
        self.body_style = ParagraphStyle(
            name='CustomBody',
            fontName=registered_font,
            fontSize=font_size,
            leading=line_height,
            textColor=text_color,
            alignment=alignment,
            spaceAfter=paragraph_spacing,
            # ReportLab doesn't support wordSpacing or letterSpacing directly in ParagraphStyle attributes
            # but we can apply spacing inside text if needed, or rely on standard layout.
        )
        
        # Store configurations for headings, to be built dynamically
        self.heading_font = registered_heading_font
        self.heading_color = heading_color
        self.heading_base_size = safe_float(self.settings.get('heading_size'), 14)
        self.heading_style_type = self.settings.get('heading_style', 'none') # none, rounded, box, underline, filled
        self.heading_bg_color = get_color(self.settings.get('heading_bg', 'transparent'))
        self.heading_border_color = get_color(self.settings.get('heading_border', '#000000'))

    def parse(self):
        """Main entry point to parse HTML and generate story elements."""
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        # Traverse top level elements of the body
        body = soup.body if soup.body else soup
        
        for element in body.children:
            if element.name is None:
                # Text node outside tags
                text = element.strip()
                if text:
                    self.story.append(Paragraph(text, self.body_style))
                continue
                
            name = element.name.lower()
            if name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                self._parse_heading(element)
            elif name == 'p':
                self._parse_paragraph(element)
            elif name in ['ul', 'ol']:
                self._parse_list(element)
            elif name == 'table':
                self._parse_table(element)
            elif name == 'img':
                self._parse_image(element)
            elif name == 'hr':
                # Add a divider line
                self.story.append(Spacer(self.column_width, 2))
                # ReportLab HR can be drawn via table border
                divider = Table([['']], colWidths=[self.column_width], rowHeights=[1])
                divider.setStyle(TableStyle([
                    ('LINEBELOW', (0,0), (-1,-1), 1, get_color(self.settings.get('border_color', '#CCCCCC'))),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                ]))
                self.story.append(divider)
                self.story.append(Spacer(self.column_width, 4))
            elif name in ['div', 'section']:
                # Recursively parse children inside div
                div_parser = HTMLToFlowablesParser(str(element), self.settings, self.column_width)
                div_parser._init_styles()
                div_parser.parse()
                self.story.extend(div_parser.story)
                
        return self.story

    def _parse_heading(self, element):
        """Parses headings and applies custom box, rounded, underline, or filled styles."""
        tag_name = element.name.lower()
        level = int(tag_name[1]) # h1 -> 1, h2 -> 2, etc.
        
        # Calculate heading font size based on level
        # Level 1 is maximum size, decreases slightly for subheadings
        scale_factor = {1: 1.2, 2: 1.1, 3: 1.0, 4: 0.95, 5: 0.9, 6: 0.85}
        size = self.heading_base_size * scale_factor.get(level, 1.0)
        
        heading_text = clean_inline_html(element, self.heading_font)
        if not heading_text:
            return

        # Prepare base style for the heading text
        heading_p_style = ParagraphStyle(
            name=f'HeadingStyle_{tag_name}_{id(element)}',
            fontName=self.heading_font,
            fontSize=size,
            leading=size * 1.25,
            textColor=self.heading_color,
            alignment=TA_LEFT,
            spaceAfter=4,
        )

        p = Paragraph(heading_text, heading_p_style)
        
        # Apply styles like: Rounded, Box, Underline, Filled
        style_type = self.heading_style_type.lower()
        
        if style_type in ['rounded', 'box', 'filled']:
            bg = self.heading_bg_color
            border_color = self.heading_border_color
            
            if style_type == 'filled' and not bg:
                bg = colors.lightgrey
                
            # If box or rounded, set a default border color if none specified
            if not border_color:
                border_color = self.heading_color
                
            border_w = 0.5
            radius = 4 if style_type == 'rounded' else 0
            
            # Use a 1x1 table to draw a beautiful boxed heading
            heading_table = Table([[p]], colWidths=[self.column_width])
            t_style = [
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]
            
            if bg:
                t_style.append(('BACKGROUND', (0,0), (-1,-1), bg))
            
            if style_type in ['box', 'rounded']:
                # Draw lines
                t_style.append(('BOX', (0,0), (-1,-1), border_w, border_color))
                
            heading_table.setStyle(TableStyle(t_style))
            
            # Wrapper to keep heading layout intact
            self.story.append(Spacer(self.column_width, 4))
            self.story.append(KeepTogether([heading_table]))
            self.story.append(Spacer(self.column_width, 4))
            
        elif style_type == 'underline':
            border_color = self.heading_border_color or self.heading_color
            
            # Use table with bottom border
            heading_table = Table([[p]], colWidths=[self.column_width])
            heading_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('LINEBELOW', (0,0), (-1,-1), 1.5, border_color),
            ]))
            self.story.append(Spacer(self.column_width, 4))
            self.story.append(KeepTogether([heading_table]))
            self.story.append(Spacer(self.column_width, 4))
        else:
            # Standard, plain heading
            self.story.append(Spacer(self.column_width, 4))
            self.story.append(p)
            self.story.append(Spacer(self.column_width, 2))

    def _parse_paragraph(self, element):
        """Parses a standard paragraph element."""
        text = clean_inline_html(element, self.body_style.fontName)
        if text.strip():
            self.story.append(Paragraph(text, self.body_style))

    def _parse_list(self, element, indent_level=1, list_num=None):
        """Recursively parses unordered, ordered, and nested lists."""
        name = element.name.lower()
        items = element.find_all('li', recursive=False)
        
        counter = 1
        for li in items:
            # Extract content of the list item
            li_text = ""
            sub_lists = []
            
            # Separate text contents from sub-lists
            for child in li.children:
                if child.name in ['ul', 'ol']:
                    sub_lists.append(child)
                else:
                    li_text += clean_inline_html(child, self.body_style.fontName)

            # Determine bullet/number styling based on list type
            left_indent = indent_level * 12
            
            # Check checklist pattern (e.g. starts with [ ] or [x] or checkbox symbols)
            checklist_prefix = None
            if li_text.startswith('[ ]'):
                checklist_prefix = "☐ "
                li_text = li_text[3:]
            elif li_text.startswith('[x]') or li_text.startswith('[X]'):
                checklist_prefix = "☑ "
                li_text = li_text[3:]
            
            # Render item prefix
            if checklist_prefix:
                bullet_char = checklist_prefix
            elif name == 'ul':
                # Alternate bullet style by nesting level
                bullet_char = "• " if indent_level % 2 != 0 else "◦ "
            else: # ol
                bullet_char = f"{counter}. "
                counter += 1

            # Format the text with the list indentation
            li_style = ParagraphStyle(
                name=f'ListItemStyle_{id(li)}',
                parent=self.body_style,
                leftIndent=left_indent,
                firstLineIndent=-8, # Hanging indent
                spaceAfter=2,
            )
            
            full_li_text = f"{bullet_char}{li_text}"
            self.story.append(Paragraph(full_li_text, li_style))
            
            # Parse nested list children
            for sub_list in sub_lists:
                self._parse_list(sub_list, indent_level + 1)

    def _parse_table(self, element):
        """Parses an HTML table and maps it to a ReportLab Table component."""
        rows = element.find_all('tr', recursive=False)
        if not rows:
            return

        table_data = []
        border_color = get_color(self.settings.get('border_color', '#CCCCCC'))
        highlight_color = get_color(self.settings.get('highlight_color', '#FFFACD'))

        # Standard cell text style inside tables
        table_cell_style = ParagraphStyle(
            name=f'TableCellStyle_{id(element)}',
            parent=self.body_style,
            fontSize=self.body_style.fontSize - 1,
            leading=self.body_style.fontSize * 1.15,
            spaceAfter=0,
        )
        
        table_header_style = ParagraphStyle(
            name=f'TableHeaderStyle_{id(element)}',
            parent=table_cell_style,
            fontName=self.heading_font,
            textColor=self.heading_color,
        )

        max_cols = 0
        for row in rows:
            row_data = []
            cells = row.find_all(['td', 'th'], recursive=False)
            max_cols = max(max_cols, len(cells))
            
            for cell in cells:
                cell_font = self.heading_font if cell.name == 'th' else self.body_style.fontName
                cell_text = clean_inline_html(cell, cell_font)
                # Apply header or cell text style
                cell_style = table_header_style if cell.name == 'th' else table_cell_style

                
                # ReportLab Table cells must contain Flowables to auto-wrap
                p_cell = Paragraph(cell_text or "&nbsp;", cell_style)
                row_data.append(p_cell)
            table_data.append(row_data)

        if not table_data or max_cols == 0:
            return

        # Distribute available column width evenly among cells
        col_width_size = self.column_width / max_cols
        col_widths = [col_width_size] * max_cols

        # Pad shorter rows to avoid IndexError
        for row in table_data:
            while len(row) < max_cols:
                row.append(Paragraph("", table_cell_style))

        # Default clean styling
        t_style = [
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]
        
        # Style headers specifically if present in the first row
        first_row_cells = rows[0].find_all(['td', 'th'], recursive=False)
        if any(c.name == 'th' for c in first_row_cells):
            t_style.append(('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F5F5F5')))
            t_style.append(('LINEBELOW', (0,0), (-1,0), 1.5, border_color))

        rl_table = Table(table_data, colWidths=col_widths)
        rl_table.setStyle(TableStyle(t_style))
        
        self.story.append(Spacer(self.column_width, 4))
        self.story.append(KeepTogether([rl_table]))
        self.story.append(Spacer(self.column_width, 4))

    def _parse_image(self, element):
        """Parses images, downloads or resolves local paths, and scales to column bounds."""
        src = element.get('src', '')
        if not src:
            return
            
        local_path = None
        
        # Resolve Media URL to Local Path
        if src.startswith(settings.MEDIA_URL):
            relative_path = src[len(settings.MEDIA_URL):]
            local_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        # Check if local absolute/relative path
        elif os.path.exists(src):
            local_path = src
            
        if not local_path or not os.path.exists(local_path):
            # If it's a URL, we could download it locally, but for now we skip or log
            logger.warning(f"Could not load image file: {src}")
            return
            
        try:
            # Use Pillow to read image aspect ratio
            from PIL import Image as PILImage
            with PILImage.open(local_path) as pil_img:
                orig_width, orig_height = pil_img.size
                
            # Scale image width to fit column width
            scaled_width = self.column_width
            scaled_height = (orig_height / orig_width) * scaled_width
            
            # Wrap image in KeepTogether to ensure it doesn't break columns weirdly
            img_flowable = Image(local_path, width=scaled_width, height=scaled_height)
            self.story.append(Spacer(self.column_width, 4))
            self.story.append(KeepTogether([img_flowable]))
            self.story.append(Spacer(self.column_width, 4))
        except Exception as e:
            logger.error(f"Error loading image {local_path} into ReportLab: {e}")
