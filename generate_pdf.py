import io
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from enum import Enum

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from sys import stderr
import qrcode
from sympy import Basic, latex

from src.derivatives import Derivative
from src.game_theory import Game2x2
from src.taylor import TaylorSeries
from src.volumes import Volumes


class GridTypes(Enum):
    VOLUME = 'volumes'
    DERIVATIVE = 'derivatives'
    TAYLOR = 'taylor'
    NASH = 'nash'

class XMLTemplateParser:
    def __init__(self, xml_file):
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()

    def parse_document(self):
        document: dict = self._parse_document()
        document['pages'] = self._parse_pages()
        document['grid'] = self._parse_grid_element(self.root.find('grid'))
        return document

    def _parse_document(self):
        return {
            'size': self._get_pagesize(),
            'meta_title': self.root.get('meta_title', 'Untitled'),
            'name': self.root.get('name', None),
        }

    def _get_pagesize(self):
        size = self.root.get('size', 'letter').lower()
        return {
            'letter': letter,
            'a4': (595.27, 841.89)
        }.get(size, letter)

    def _parse_pages(self):
        pages = []
        for page_elem in self.root.findall('page'):
            elements = []
            for elem in page_elem:
                if elem.tag == 'text':
                    elements.append(self._parse_text_element(elem))
                elif elem.tag == 'image':
                    elements.append(self._parse_image_element(elem))
                elif elem.tag == 'qr':
                    elements.append(self._parse_qr_element(elem))
                elif elem.tag == 'answer':
                    elements.append(self._parse_answer_element(elem))
            pages.append(self._parse_page_element(page_elem))
            pages[-1]['elements'] = elements
        return pages

    def _parse_page_element(self, page_elem):
        return {}

    def _parse_text_element(self, elem):
        return {
            'type': 'text',
            'content': elem.text,
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'font': elem.get('font', 'Helvetica'),
            'size': int(elem.get('size', 12)),
            'color': elem.get('color', '#000000'),
            'link': elem.get('link', None),
        }

    def _parse_answer_element(self, elem):
        return {
            'type': 'answer',
            'content': elem.text,
            'position': (float(elem.get('x', 0)) * inch,
                         float(elem.get('y', 0)) * inch),
            'font': elem.get('font', 'Helvetica'),
            'size': int(elem.get('size', 12)),
            'color': elem.get('color', '#000000'),
            'link': elem.get('link', None),
            'answer_margin': elem.get('answer_margin', 0.5),
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
            'a': float(elem.get('a', 1)),
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
        self.document = self.parser.parse_document()
        self.pages: list | None = self.document.get('pages')
        self.grid: dict | None = self.document.get('grid')
        self.game_2x2 = None
        self.answer_places = self._get_answers(self.pages)

    def _get_answers(self, pages):
        answers = []
        for page in pages:
            for elem in page['elements']:
                if elem['type'] == 'answer':
                    answers.append(elem)
        return answers

    def generate_pdf(self, problems, answers):
        if self.document['name'] is None:
            self.document['name'] = 'output/' + self.base_name + '.pdf'
        else:
            self.document['name'] = 'output/' + self.document['name'] + '.pdf'
        self.c = canvas.Canvas(self.document['name'])
        self.c.setPageSize(self.document['size'])
        self.c.setTitle(self.document['meta_title'])
        self._process_problems_page(self.pages[0], problems)
        self._process_answers_page(self.pages[1], answers)
        self.c.save()

    def _process_problems_page(self, page, problems):
        self._add_static_elements(page)
        if self.grid is not None:
            self._process_grid_problems(problems)
        self.c.showPage()

    def _process_answers_page(self, page, answers):
        self._add_static_elements(page)
        if self.grid is not None:
            self._process_grid_answers(answers)
        self.c.showPage()

    def _process_grid_problems(self, problems):
        assert len(GridTypes) == 4
        if self.grid['grid_type'] == GridTypes.NASH:
            lm = self.grid['lm'] + 55
            tm = self.grid['tm']
            bm = self.grid['bm'] + 400
            p1 = 'Taxpayer'
            p2 = 'Auditor'
            self.game_2x2 = Game2x2(p1, p2)
            self._draw_grid(lm, tm, bm, f'{p1}/{p2}',
                            ['Audit', 'Neglect'], ['Declare', 'Cheat'], self.game_2x2.matrix)
            return
        if self.grid['grid_type'] == GridTypes.VOLUME:
            new_problems = []
            for i in range(len(problems)):
                new_problems.append(f'output/{self.base_name}_{i}.jpg')
            problems = new_problems
        self._add_math_problems(problems)

    def _process_grid_answers(self, answers):
        if self.grid['grid_type'] == GridTypes.NASH:
            pure = self.game_2x2.get_pure_nash_equilibria()
            mixed = self.game_2x2.get_mixed_strategy_nash()
            self._draw_nash_answers([pure, mixed])
            return
        self._add_math_problems(answers)

    def _add_static_elements(self, page):
        for element in page['elements']:
            if element['type'] == 'text':
                self._draw_text(element)
            elif element['type'] == 'image':
                self._draw_image(element)
            elif element['type'] == 'qr':
                self._draw_qr(element)

    def _draw_text(self, element):
        self.c.setFont(element['font'], element['size'])
        self.c.setFillColor(element['color'])
        x, y = element['position']
        text = element['content']
        self.c.drawString(x, y, str(text))
        self.c.setFont('Helvetica', 12)
        if element['link'] is not None:
            text_width = self.c.stringWidth(text, element['font'], element['size'])
            self.c.linkURL(
                element['link'],
                (x, y, x + text_width, y + element['size']),
                relative=0
            )

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


    def _draw_grid(self, left_margin, top_margin, bottom_margin, title,
                   col_labels, row_labels, data, n = 3):
        page_width, page_height = self.document['size']
        grid_width = page_width - 2 * left_margin
        grid_height = page_height - top_margin - bottom_margin
        cell_width = grid_width / n
        cell_height = grid_height / n
        x_start = left_margin
        y_start = bottom_margin

        # Draw horizontal lines
        for row in range(n + 1):
            y = y_start + row * cell_height
            self.c.line(x_start, y, x_start + grid_width, y)

        # Draw vertical lines
        for col in range(n + 1):
            x = x_start + col * cell_width
            self.c.line(x, y_start, x, y_start + grid_height)

        if title:
            x = x_start + 5
            y = y_start + (n - 0.5) * cell_height
            self.c.drawString(x, y, title)

        # Insert text into first row (columns 2..n)
        if col_labels:
            assert(len(col_labels) == n - 1)
            for j, label in enumerate(col_labels, start=1):
                x = x_start + j * cell_width + 5
                y = y_start + (n - 0.5) * cell_height
                self.c.drawString(x, y, str(label))

        # Insert text into first column (rows 2..n)
        if row_labels:
            assert (len(row_labels) == n - 1)
            for i, label in enumerate(row_labels, start=1):
                x = x_start + 5
                y = y_start + (n - i - 0.5) * cell_height
                self.c.drawString(x, y, str(label))

        # Insert data into the grid
        if data:
            for i in range(len(data)):
                for j in range(len(data[i])):
                    x = x_start + (j + 1) * cell_width + 5
                    y = y_start + (n - i - 1.5) * cell_height
                    self.c.drawString(x, y, str(data[i][j]))

    def _draw_nash_answers(self, answers):
        assert len(self.answer_places) >= 2, 'Two answer tags required for this problem'
        assert len(answers) == 2, 'Two answers required for nash problem'
        for i in range(len(answers)):
            answer = answers[i]
            answer_element = self.answer_places[i]
            self._draw_text(answer_element)
            answer_element['content'] = answer if answer is not None and len(answer) > 0 else 'Does not exist'
            x, y = answer_element['position']
            answer_element['position'] = (x + 20, y - answer_element['answer_margin'] * inch)
            self._draw_text(answer_element)

    def _add_math_problems(self, problems):
        page_width, page_height = self.document['size']
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

    def _read_image(self, filename):
        with open(filename, 'rb') as f:
            return io.BytesIO(f.read())

    def _render_expression(self, expr):
        latex_str = f"${latex(expr)}$"
        dpi = 200
        fontsize = 16

        # Step 1: Create initial figure to measure size
        fig = Figure(figsize=(4, 1), dpi=dpi)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.axis("off")
        text = ax.text(0, 0, latex_str, fontsize=fontsize)

        # Step 2: Draw and measure bounding box
        canvas.draw()
        renderer = canvas.get_renderer()
        bbox = text.get_window_extent(renderer=renderer)

        width_in = (bbox.width + 10) / dpi  # Add padding
        height_in = (bbox.height + 10) / dpi

        # Step 3: Create final figure with correct size
        fig = Figure(figsize=(width_in, height_in), dpi=dpi)
        canvas = FigureCanvas(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.text(0.5, 0.5, latex_str, fontsize=fontsize, ha="center", va="center")

        # Step 4: Render to PNG in memory
        buffer = io.BytesIO()
        canvas.print_png(buffer)
        buffer.seek(0)
        return buffer

    def get_problem_pairs(self):
        assert len(GridTypes) == 4
        if self.grid['grid_type'] == GridTypes.VOLUME:
            vol = Volumes('volumes')
            p, ans = vol.get_problem_pairs(generator.grid['n'], generator.grid['difficulty'], generator.grid['x_range'])
        elif self.grid['grid_type'] == GridTypes.DERIVATIVE:
            dv = Derivative()
            p, ans = dv.get_problem_pairs(generator.grid['n'], (4, 4), 4)
        elif self.grid['grid_type'] == GridTypes.TAYLOR:
            tay = TaylorSeries()
            p, ans = tay.get_problem_pairs(generator.grid['n'], (1, 2), generator.grid['a'])
        elif self.grid['grid_type'] == GridTypes.NASH:
            p, ans = 0, 0
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