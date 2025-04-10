import io
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from enum import Enum

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from sys import stderr
from sympy.printing.preview import preview
import qrcode
from sympy import Basic
from sympy.simplify.simplify import bottom_up

from derivatives import Derivative
from volumes import Volumes


class GridTypes(Enum):
    VOLUME = 'volumes'
    DERIVATIVE = 'derivatives'

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
        grid = None
        for elem in self.root.iter():
            if elem.tag == 'text':
                elements.append(self._parse_text_element(elem))
            elif elem.tag == 'image':
                elements.append(self._parse_image_element(elem))
            elif elem.tag == 'qr':
                elements.append(self._parse_qr_element(elem))
            elif elem.tag == 'grid':
                grid = self._parse_grid_element(elem)
        return elements, grid

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
        left = elem.get('x_left', -25)
        right = elem.get('x_right', 25)
        return {
            'type': 'grid',
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'columns': int(elem.get('columns', 3)),
            'rows': int(elem.get('rows', 3)),
            'cell_width': float(elem.get('cell_width', 2.5)) * inch,
            'cell_height': float(elem.get('cell_height', 1)) * inch,
            'spacing': float(elem.get('spacing', 0.2)) * inch,
            'n': int(elem.get('n', 9)),
            'grid_type': GridTypes(elem.get('type', None)),
            'difficulty': elem.get('difficulty', 'simple'),
            'x_range': (int(left), int(right)),
            'tm': int(elem.get('tm', 0)),
            'bm': int(elem.get('bm', 0)),
            'lm': int(elem.get('lm', 0)),
            'scale_cap': float(elem.get('scale_cap', 0.6)),
        }


class PDFGenerator:
    def __init__(self, template_file):
        self.c = None
        self.base_name = os.path.splitext(os.path.basename(template_file))[0]
        self.parser = XMLTemplateParser(template_file)
        self.elements, self.grid = self.parser.parse_elements()

    def generate_pdf(self, problems, answers, filename=None):
        if filename is None:
            filename = 'output/' + self.base_name + '.pdf'
        self.c = canvas.Canvas(filename, pagesize=self.parser.pagesize)
        self._add_static_elements()
        if self.grid is not None:
            self._process_grid(problems, answers)
        self.c.save()

    def _process_grid(self, problems, answers):
        if self.grid['grid_type'] == GridTypes.VOLUME:
            new_problems = []
            for i in range(len(problems)):
                new_problems.append(f'output/{self.base_name}_{i}.jpg')
            self._add_math_problems(new_problems)
        elif self.grid['grid_type'] == GridTypes.DERIVATIVE:
            self._add_math_problems(problems)
        self._add_math_problems(answers)

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
        self.c.setFont('Helvetica', 12)

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

    def _add_math_problems(self, problems):
        page_width, page_height = self.parser.pagesize
        # Layout configuration
        left_margin = self.grid['lm']
        top_margin = self.grid['tm']
        bottom_margin = self.grid['bm']
        n = len(problems)
        cell_width = (page_width - 2 * left_margin)
        cell_height = (page_height - (bottom_margin + top_margin)) / n
        max_image_width = cell_width - 20
        max_image_height = cell_height - 20
        for i, item in enumerate(problems, start=1):
            if isinstance(item, Basic):
                buffer = self._render_expression(item)
            elif isinstance(item, str):
                buffer = self._read_image(item)
            else:
                raise ValueError('Item type not supported')
            buffer.seek(0)
            img = ImageReader(buffer)
            img_width, img_height = img.getSize()

            # Calculate scaling factor
            scale_cap = self.grid['scale_cap']
            scale = min(scale_cap, min(max_image_width / img_width, max_image_height / img_height))
            scaled_width = img_width * scale
            scaled_height = img_height * scale

            y = page_height - top_margin - i * cell_height + (cell_height - scaled_height) / 2

            self.c.drawImage(img, left_margin, y, width=scaled_width, height=scaled_height)
            self.c.drawString(left_margin - 20, y + scaled_height / 2, f"{i})")  # Numbering
        self.c.showPage()

    def _read_image(self, filename):
        with open(filename, 'rb') as f:
            return io.BytesIO(f.read())

    def _render_expression(self, expr):
        buffer = io.BytesIO()

        # Calculate complexity factor based on expression size
        complexity = len(str(expr))  # Simple complexity metric
        font_size = max(12, 16 - complexity // 4)  # Adjust font size based on complexity
        # Generate LaTeX and process in temporary directory
        try:
            preview(expr, output='png', viewer='BytesIO', outputbuffer=buffer,
                    dvioptions=['-D', '300', '-T', 'tight'], fontsize=font_size, euler=False)
        except Exception as e:
            raise RuntimeError(f"Failed to render equation: {str(e)}") from e
        return buffer

    def get_problem_pairs(self):
        if self.grid['grid_type'] == GridTypes.VOLUME:
            vol = Volumes('volumes')
            p, ans = vol.get_problem_pairs(generator.grid['n'], generator.grid['difficulty'], generator.grid['x_range'])
        elif self.grid['grid_type'] == GridTypes.DERIVATIVE:
            dv = Derivative()
            p, ans = dv.get_problem_pairs(generator.grid['n'], (4, 4), 4)
        else:
            print('Invalid problem type:', self.grid['grid_type'], file=stderr)
            exit(1)
        return p, ans

    def clean(self):
        subprocess.run('rm output/volumes_*.jpg 2>/dev/null', shell=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <problems-type>.xml")
        sys.exit(1)
    problem_template = sys.argv[1]
    if not problem_template.endswith('.xml'):
        print(f"Usage: {sys.argv[0]} <problems-type>.xml")
        sys.exit(1)
    generator = PDFGenerator(problem_template)
    p, ans = generator.get_problem_pairs()
    generator.generate_pdf(p, ans)
    generator.clean()