import io
from django.test import TestCase
from reportlab.platypus import Paragraph, Table, Spacer

from .font_manager import register_font_family
from .parser import HTMLToFlowablesParser, get_color
from .generator import generate_pdf

class TestFontManager(TestCase):
    def test_font_fallbacks(self):
        """Verify that built-in standard web-safe fonts return correctly mapped names."""
        self.assertEqual(register_font_family('Arial'), 'Noto Sans-normal')
        self.assertEqual(register_font_family('Times New Roman'), 'Noto Serif-normal')
        self.assertEqual(register_font_family('Georgia'), 'Noto Serif-normal')
        self.assertEqual(register_font_family('Courier New'), 'Noto Sans-normal')

    def test_invalid_font_fallback(self):
        """Verify that an unrecognized font family falls back safely to Noto Sans."""
        self.assertEqual(register_font_family('SomeUnknownRandomFont'), 'Noto Sans-normal')



class TestHTMLToFlowablesParser(TestCase):
    def setUp(self):
        self.default_settings = {
            'font_family': 'Helvetica',
            'font_size': 9,
            'line_height': 1.2,
            'paragraph_spacing': 4,
            'text_align': 'justify',
            'text_color': '#000000',
            'heading_font': 'Helvetica',
            'heading_size': 12,
            'heading_style': 'none',
            'heading_color': '#111111'
        }
        self.col_width = 150.0

    def test_parse_simple_paragraph(self):
        """Verify standard paragraph translation with nested bold and italic tags."""
        html = "<p>This is a <strong>bold</strong> and <em>italic</em> text.</p>"
        parser = HTMLToFlowablesParser(html, self.default_settings, self.col_width)
        story = parser.parse()
        
        self.assertEqual(len(story), 1)
        self.assertTrue(isinstance(story[0], Paragraph))
        # Checks that XML formatting markup for ReportLab is generated correctly
        self.assertIn("This is a <b>bold</b> and <i>italic</i> text.", story[0].text)

    def test_parse_headings(self):
        """Verify heading levels and different border/background style decorators."""
        # Plain heading
        html_plain = "<h1>Introduction</h1>"
        parser_plain = HTMLToFlowablesParser(html_plain, self.default_settings, self.col_width)
        story_plain = parser_plain.parse()
        self.assertEqual(len(story_plain), 3) # Spacer + Paragraph + Spacer
        self.assertTrue(isinstance(story_plain[1], Paragraph))
        self.assertIn("Introduction", story_plain[1].text)

        # Underlined heading (should generate a Table layout wrapper)
        settings_underline = self.default_settings.copy()
        settings_underline['heading_style'] = 'underline'
        parser_underline = HTMLToFlowablesParser(html_plain, settings_underline, self.col_width)
        story_underline = parser_underline.parse()
        self.assertEqual(len(story_underline), 3) # Spacer + KeepTogether(Table) + Spacer
        
    def test_parse_lists(self):
        """Verify bullets and checklists prefix characters mapping."""
        html = "<ul><li>Normal Item</li><li>[ ] Checkbox Item</li></ul>"
        parser = HTMLToFlowablesParser(html, self.default_settings, self.col_width)
        story = parser.parse()
        
        self.assertEqual(len(story), 2)
        self.assertTrue(isinstance(story[0], Paragraph))
        self.assertTrue(isinstance(story[1], Paragraph))
        self.assertTrue(story[0].text.startswith("• "))
        self.assertTrue(story[1].text.startswith("☐ "))

    def test_parse_tables(self):
        """Verify table cells get wrapped in Paragraph components for auto-wrap."""
        html = """
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Cell A</td><td>Cell B</td></tr>
        </table>
        """
        parser = HTMLToFlowablesParser(html, self.default_settings, self.col_width)
        story = parser.parse()
        
        self.assertEqual(len(story), 3) # Spacer + KeepTogether(Table) + Spacer
        table_flowable = story[1]._content[0] # Inside KeepTogether wrapper
        self.assertTrue(isinstance(table_flowable, Table))
        
        # Verify table internal shapes and contents
        cell_data = table_flowable._cellvalues
        self.assertEqual(len(cell_data), 2) # 2 rows
        self.assertEqual(len(cell_data[0]), 2) # 2 columns
        self.assertTrue(isinstance(cell_data[0][0], Paragraph)) # Wrapped in paragraph


class TestPDFGenerator(TestCase):
    def test_pdf_generation(self):
        """Run PDF generation end-to-end to verify layout frame coordinate computations."""
        html = "<h1>Test Doc</h1><p>This is a column text flow test to A4 Letter A5 templates.</p>"
        settings = {
            'paper_size': 'A4',
            'orientation': 'portrait',
            'columns': 3,
            'column_spacing': 10,
            'margin_top': 36,
            'margin_bottom': 36,
            'margin_left': 36,
            'margin_right': 36,
            'show_page_border': True,
            'page_border_color': '#FF0000',
            'font_family': 'Helvetica',
            'font_size': 9,
            'line_height': 1.2,
            'watermark_text': 'TEST RUN',
            'header_text': 'Doc Header',
            'footer_text': 'Doc Footer',
            'show_page_numbers': True
        }
        
        buffer = io.BytesIO()
        try:
            generate_pdf(html, settings, buffer)
            pdf_data = buffer.getvalue()
            buffer.close()
            
            # PDF header indicator
            self.assertTrue(pdf_data.startswith(b'%PDF-'))
            self.assertTrue(len(pdf_data) > 100)
        except Exception as e:
            self.fail(f"PDF generation failed with exception: {e}")


class TestMalayalamPDFShaping(TestCase):
    def test_malayalam_character_preservation(self):
        """Verify that Malayalam characters are fully preserved and shaped without corruption in the PDF."""
        from pypdf import PdfReader
        
        html = "<p>By the way അതിനിടയിൽ / ഓർമ്മ വന്നു</p>"
        settings = {
            'paper_size': 'A4',
            'orientation': 'portrait',
            'columns': 1,
            'margin_top': 36,
            'margin_bottom': 36,
            'margin_left': 36,
            'margin_right': 36,
            'font_family': 'Manjari',
            'font_size': 10,
            'line_height': 1.3,
            'text_color': '#000000'
        }
        
        buffer = io.BytesIO()
        generate_pdf(html, settings, buffer)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Read using pypdf
        reader = PdfReader(io.BytesIO(pdf_data))
        text = reader.pages[0].extract_text()
        
        # Normalize whitespace (collapsing multiple spaces and newlines to a single space)
        normalized_text = " ".join(text.split())
        
        # Verify that major Malayalam Unicode chunks are present and unaltered
        self.assertIn("അതിനിടയിൽ", normalized_text)
        self.assertIn("ഓർമ്മ വന്നു", normalized_text)

