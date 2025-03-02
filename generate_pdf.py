import io
import os
import tempfile
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from sympy.printing.preview import preview
import qrcode

from derivatives import get_problem_pairs


class XMLTemplateParser:
    def __init__(self, xml_file):
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        self.pagesize = self._get_pagesize()

    def _get_pagesize(self):
        size = self.root.find('page').get('size', 'letter').lower()
        return {
            'letter': letter,
            'a4': (595.27, 841.89)
        }.get(size, letter)

    def parse_elements(self):
        elements = []
        for elem in self.root.iter():
            if elem.tag == 'text':
                elements.append(self._parse_text_element(elem))
            elif elem.tag == 'image':
                elements.append(self._parse_image_element(elem))
            elif elem.tag == 'qr':
                elements.append(self._parse_qr_element(elem))
            elif elem.tag == 'grid':
                elements.append(self._parse_grid_element(elem))
        return elements

    def _parse_text_element(self, elem):
        return {
            'type': 'text',
            'content': elem.text,
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'font': elem.get('font', 'Helvetica'),
            'size': int(elem.get('size', 12)),
            'color': elem.get('color', '#000000')
        }

    def _parse_image_element(self, elem):
        return {
            'type': 'image',
            'path': elem.get('path'),
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'width': float(elem.get('width', 1)) * inch,
            'height': float(elem.get('height', 1)) * inch
        }

    def _parse_qr_element(self, elem):
        return {
            'type': 'qr',
            'content': elem.get('content'),
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'size': float(elem.get('size', 1)) * inch
        }

    def _parse_grid_element(self, elem):
        return {
            'type': 'grid',
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'columns': int(elem.get('columns', 3)),
            'rows': int(elem.get('rows', 3)),
            'cell_width': float(elem.get('cell_width', 2.5)) * inch,
            'cell_height': float(elem.get('cell_height', 1)) * inch,
            'spacing': float(elem.get('spacing', 0.2)) * inch
        }


class PDFGenerator:
    def __init__(self, template_file):
        self.c = None
        self.parser = XMLTemplateParser(template_file)
        self.elements = self.parser.parse_elements()

    def generate_pdf(self, problems, answers, filename):
        self.c = canvas.Canvas(filename, pagesize=self.parser.pagesize)
        self._add_static_elements()
        self._add_math_grid(problems)
        self._add_math_grid(answers)
        self.c.save()

    def _add_static_elements(self):
        for element in self.elements:
            if element['type'] == 'text':
                self._draw_text(element)
            elif element['type'] == 'image':
                self._draw_image(element)
            elif element['type'] == 'qr':
                self._draw_qr(element)

    def _draw_text(self, element):
        self.c.setFont(element['font'], element['size'])
        self.c.setFillColor(element['color'])
        self.c.drawString(*element['position'], element['content'])

    def _draw_image(self, element):
        img = ImageReader(element['path'])
        self.c.drawImage(img, *element['position'],
                         width=element['width'],
                         height=element['height'])

    def _draw_qr(self, element):
        qr = qrcode.make(element['content'])
        with tempfile.NamedTemporaryFile(delete=False) as f:
            qr.save(f, format='PNG')
            img = ImageReader(f.name)
            self.c.drawImage(img, *element['position'],
                             width=element['size'],
                             height=element['size'])
        os.unlink(f.name)

    def _add_math_grid(self, problems):
        grid = next(e for e in self.elements if e['type'] == 'grid')
        buffers = self._render_expressions(problems)
        self._draw_grid(buffers, grid)
        self.c.showPage()

    def _draw_grid(self, buffers, grid):
        """Draw a 3x3 grid of equations on a canvas page"""
        page_width, page_height = self.parser.pagesize
        # Layout configuration
        left_margin = 50
        top_margin = 50
        cell_width = (page_width - 2 * left_margin) / 3
        cell_height = (page_height - 2 * top_margin) / 3
        max_image_width = cell_width - 20
        max_image_height = cell_height - 20

        text_shift = 14
        # Draw equations in grid
        for i in range(9):
            row = i // 3
            col = i % 3

            buffer = buffers[i]
            buffer.seek(0)
            img = ImageReader(buffer)
            img_width, img_height = img.getSize()

            # Calculate scaling factor
            scale_cap = 0.6
            scale = min(scale_cap, min(max_image_width / img_width, max_image_height / img_height))
            print(f"Current problem: {i}, Current scaling: {scale}")
            scaled_width = img_width * scale
            scaled_height = img_height * scale

            # Calculate position
            x = left_margin + col * (cell_width + text_shift) + (cell_width - scaled_width) / 2
            y = page_height - top_margin - (row + 1) * cell_height + (cell_height - scaled_height) / 2
            text_y = page_height - top_margin - (row + 1) * cell_height + cell_height / 2

            self.c.setFont('Helvetica', 10)
            self.c.drawString(x - text_shift, text_y, f'{i})')
            self.c.drawImage(img, x, y, scaled_width, scaled_height)

    def __draw_grid(self, buffers, grid_config):
        x, y = grid_config['position']
        col_count = grid_config['columns']

        for i in range(len(buffers)):
            row = i // col_count
            col = i % col_count

            x_pos = x + col * (grid_config['cell_width'] + grid_config['spacing'])
            y_pos = y - row * (grid_config['cell_height'] + grid_config['spacing'])

            buffer = buffers[i]
            img = ImageReader(buffer)
            self.c.drawImage(img, x_pos, y_pos,
                             width=grid_config['cell_width'],
                             height=grid_config['cell_height'])

    def _render_expressions(self, expressions):
        buffers = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for i, expr in enumerate(expressions):
                temp_png = os.path.join(tmpdir, f'eq_{i}.png')

                # Calculate complexity factor based on expression size
                complexity = len(str(expr))  # Simple complexity metric
                font_size = max(12, 16 - complexity//4)  # Adjust font size based on complexity

                # Generate LaTeX and process in temporary directory
                try:
                    preview(
                        expr,
                        output='png',
                        viewer='file',
                        filename=temp_png,
                        dvioptions=['-D', '300', '-T', 'tight'],
                        fontsize=font_size,
                        euler=False
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to render equation {i + 1}: {str(e)}") from e

                with open(temp_png, 'rb') as f:
                    buffers.append(io.BytesIO(f.read()))
        return buffers


# Example XML structure:
"""
<template>
    <page size="letter">
        <image path="logo.png" x="6" y="10" width="1.5" height="0.5"/>
        <text x="1" y="10.5" size="18" font="Helvetica-Bold" color="#000000">
            Math Worksheet
        </text>
        <qr content="https://example.com/answers" x="7" y="0.5" size="1"/>
        <grid x="1" y="9" columns="3" rows="3" 
              cell_width="2.5" cell_height="1.5" spacing="0.3"/>
    </page>
</template>
"""

if __name__ == "__main__":
    p, ans = get_problem_pairs(9, (4, 4), 2)
    generator = PDFGenerator('template.xml')
    generator.generate_pdf(p, ans, 'math_worksheet.pdf')