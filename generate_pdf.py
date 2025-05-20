import io
import logging
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from enum import Enum
import random
import numpy as np
from typing import Dict, List, Optional, Tuple, Union

import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import qrcode
from sympy import Basic, latex
import matplotlib.pyplot as plt

from src.derivatives import Derivative
from src.game_theory import Game2x2
from src.taylor import TaylorSeries
from src.volumes import Volumes
from src.config import PDFConfig, setup_logging, LogConfig, log_exceptions
from src.horizontal_tangent import HorizontalTangent

logger = logging.getLogger(__name__)

class GridTypes(Enum):
    VOLUME = 'volumes'
    DERIVATIVE = 'derivatives'
    TAYLOR = 'taylor'
    NASH = 'nash'
    HORIZONTAL_TANGENT = 'horizontal_tangent'

class XMLTemplateParser:
    def __init__(self, xml_file: str):
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        self.config = PDFConfig()

    def parse_document(self) -> Dict:
        """Parse the XML document and return a structured dictionary."""
        document: Dict = self._parse_document()
        document['pages'] = self._parse_pages()
        document['grid'] = self._parse_grid_element(self.root.find('grid'))
        return document

    def _parse_document(self) -> Dict:
        """Parse the root document element."""
        seed = self.root.get('seed')
        if seed is not None:
            seed = int(seed)
            random.seed(seed)
            np.random.seed(seed)
            
        return {
            'size': self._get_pagesize(),
            'meta_title': self.root.get('meta_title', 'Untitled'),
            'name': self.root.get('name', None),
            'seed': seed
        }

    def _get_pagesize(self) -> Tuple[float, float]:
        """Get the page size from the document configuration."""
        size = self.root.get('size', 'letter').lower()
        return {
            'letter': letter,
            'a4': (595.27, 841.89)
        }.get(size, letter)

    def _parse_pages(self) -> List[Dict]:
        """Parse all pages in the document."""
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

    def _parse_page_element(self, page_elem: ET.Element) -> Dict:
        """Parse a single page element."""
        return {}

    def _parse_text_element(self, elem: ET.Element) -> Dict:
        """Parse a text element."""
        return {
            'type': 'text',
            'content': elem.text,
            'position': (float(elem.get('x', 0)) * inch,
                        float(elem.get('y', 0)) * inch),
            'font': elem.get('font', 'Helvetica'),
            'size': int(elem.get('size', self.config.fontsize)),
            'color': elem.get('color', '#000000'),
            'link': elem.get('link', None),
        }

    def _parse_answer_element(self, elem: ET.Element) -> Dict:
        """Parse an answer element."""
        return {
            'type': 'answer',
            'content': elem.text,
            'position': (float(elem.get('x', 0)) * inch,
                        float(elem.get('y', 0)) * inch),
            'font': elem.get('font', 'Helvetica'),
            'size': int(elem.get('size', self.config.fontsize)),
            'color': elem.get('color', '#000000'),
            'link': elem.get('link', None),
            'answer_margin': float(elem.get('answer_margin', 0.5)),
        }

    def _parse_image_element(self, elem: ET.Element) -> Dict:
        """Parse an image element."""
        return {
            'type': 'image',
            'path': elem.get('path'),
            'position': (float(elem.get('x', 0)) * inch,
                        float(elem.get('y', 0)) * inch),
            'width': float(elem.get('width', 1)) * inch,
            'height': float(elem.get('height', 1)) * inch
        }

    def _parse_qr_element(self, elem: ET.Element) -> Dict:
        """Parse a QR code element."""
        return {
            'type': 'qr',
            'content': elem.get('content'),
            'position': (float(elem.get('x', 0)) * inch,
                        float(elem.get('y', 0)) * inch),
            'size': float(elem.get('size', 1)) * inch
        }

    def _parse_grid_element(self, elem: Optional[ET.Element]) -> Optional[Dict]:
        """Parse the grid element."""
        if elem is None:
            return None
            
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
    @log_exceptions(logger)
    def __init__(self, template_file: str):
        self.c: Optional[canvas.Canvas] = None
        self.base_name = os.path.splitext(os.path.basename(template_file))[0]
        logger.debug(f"Initializing PDFGenerator with template: {template_file}")
        self.parser = XMLTemplateParser(template_file)
        self.document = self.parser.parse_document()
        self.pages: Optional[List[Dict]] = self.document.get('pages')
        self.grid: Optional[Dict] = self.document.get('grid')
        self.game_2x2: Optional[Game2x2] = None
        self.answer_places = self._get_answers(self.pages) if self.pages else []

    def _get_answers(self, pages: List[Dict]) -> List[Dict]:
        """Extract answer elements from all pages."""
        answers = []
        for page in pages:
            for elem in page['elements']:
                if elem['type'] == 'answer':
                    answers.append(elem)
        return answers

    @log_exceptions(logger)
    def generate_pdf(self, problems: List[Union[Basic, str]], answers: List[Union[Basic, str]]) -> None:
        """Generate the PDF with problems and answers."""
        output_path = self._get_output_path()
        logger.info(f"Generating PDF at: {output_path}")
        self.c = canvas.Canvas(output_path)
        self.c.setPageSize(self.document['size'])
        self.c.setTitle(self.document['meta_title'])
        
        if self.pages:
            self._process_problems_page(self.pages[0], problems)
            if len(self.pages) > 1:
                self._process_answers_page(self.pages[1], answers)
        
        self.c.save()
        logger.info("PDF generation completed successfully")

    def _get_output_path(self) -> str:
        """Get the output path for the PDF file."""
        if self.document['name'] is None:
            return os.path.join(self.parser.config.output_dir, f"{self.base_name}.pdf")
        return os.path.join(self.parser.config.output_dir, f"{self.document['name']}.pdf")

    def _process_problems_page(self, page: Dict, problems: List[Union[Basic, str]]) -> None:
        """Process the problems page."""
        self._add_static_elements(page)
        if self.grid is not None:
            self._process_grid_problems(problems)
        self.c.showPage()

    def _process_answers_page(self, page: Dict, answers: List[Union[Basic, str]]) -> None:
        """Process the answers page."""
        self._add_static_elements(page)
        if self.grid is not None:
            self._process_grid_answers(answers)
        self.c.showPage()

    def _process_grid_problems(self, problems: List[Union[Basic, str]]) -> None:
        """Process grid problems based on type."""
        if self.grid['grid_type'] == GridTypes.NASH:
            self._process_nash_problems()
        elif self.grid['grid_type'] == GridTypes.VOLUME:
            problems = [f'output/{self.base_name}_{i}.jpg' for i in range(len(problems))]
        self._add_math_problems(problems)

    def _process_nash_problems(self) -> None:
        """Process Nash equilibrium problems."""
        lm = self.grid['lm'] + 55
        tm = self.grid['tm']
        bm = self.grid['bm'] + 400
        p1 = 'Taxpayer'
        p2 = 'Auditor'
        self.game_2x2 = Game2x2(p1, p2)
        self._draw_grid(lm, tm, bm, f'{p1}/{p2}',
                       ['Audit', 'Neglect'], ['Declare', 'Cheat'], self.game_2x2.matrix)

    def _process_grid_answers(self, answers: List[Union[Basic, str]]) -> None:
        """Process grid answers based on type."""
        if self.grid['grid_type'] == GridTypes.NASH:
            pure = self.game_2x2.get_pure_nash_equilibria()
            mixed = self.game_2x2.get_mixed_strategy_nash()
            self._draw_nash_answers([pure, mixed])
        else:
            self._add_math_problems(answers)

    def _add_static_elements(self, page: Dict) -> None:
        """Add static elements to the page."""
        for element in page['elements']:
            if element['type'] == 'text':
                self._draw_text(element)
            elif element['type'] == 'image':
                self._draw_image(element)
            elif element['type'] == 'qr':
                self._draw_qr(element)

    def _draw_text(self, element: Dict) -> None:
        """Draw text on the canvas."""
        self.c.setFont(element['font'], element['size'])
        self.c.setFillColor(element['color'])
        x, y = element['position']
        text = element['content']
        self.c.drawString(x, y, str(text))
        self.c.setFont('Helvetica', self.parser.config.fontsize)
        
        if element['link'] is not None:
            text_width = self.c.stringWidth(text, element['font'], element['size'])
            self.c.linkURL(
                element['link'],
                (x, y, x + text_width, y + element['size']),
                relative=0
            )

    def _draw_image(self, element: Dict) -> None:
        """Draw an image on the canvas."""
        img = ImageReader(element['path'])
        self.c.drawImage(img, *element['position'],
                        width=element['width'],
                        height=element['height'])

    def _draw_qr(self, element: Dict) -> None:
        """Draw a QR code on the canvas."""
        qr = qrcode.make(element['content'])
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        buffer.seek(0)
        img = ImageReader(buffer)
        self.c.drawImage(img, *element['position'],
                        width=element['size'],
                        height=element['size'])

    def _draw_grid(self, left_margin: float, top_margin: float, bottom_margin: float,
                  title: str, col_labels: List[str], row_labels: List[str],
                  data: List[List], n: int = 3) -> None:
        """Draw a grid on the canvas."""
        page_width, page_height = self.document['size']
        grid_width = page_width - 2 * left_margin
        grid_height = page_height - top_margin - bottom_margin
        cell_width = grid_width / n
        cell_height = grid_height / n
        x_start = left_margin
        y_start = bottom_margin

        # Draw grid lines
        self._draw_grid_lines(x_start, y_start, grid_width, grid_height, n, cell_width, cell_height)

        # Add labels and data
        self._add_grid_labels(x_start, y_start, cell_width, cell_height, n,
                            title, col_labels, row_labels, data)

    def _draw_grid_lines(self, x_start: float, y_start: float, grid_width: float,
                        grid_height: float, n: int, cell_width: float, cell_height: float) -> None:
        """Draw the grid lines."""
        # Horizontal lines
        for row in range(n + 1):
            y = y_start + row * cell_height
            self.c.line(x_start, y, x_start + grid_width, y)

        # Vertical lines
        for col in range(n + 1):
            x = x_start + col * cell_width
            self.c.line(x, y_start, x, y_start + grid_height)

    def _add_grid_labels(self, x_start: float, y_start: float, cell_width: float,
                        cell_height: float, n: int, title: str,
                        col_labels: List[str], row_labels: List[str],
                        data: List[List]) -> None:
        """Add labels and data to the grid."""
        if title:
            x = x_start + 5
            y = y_start + (n - 0.5) * cell_height
            self.c.drawString(x, y, title)

        # Column labels
        if col_labels:
            assert len(col_labels) == n - 1
            for j, label in enumerate(col_labels, start=1):
                x = x_start + j * cell_width + 5
                y = y_start + (n - 0.5) * cell_height
                self.c.drawString(x, y, str(label))

        # Row labels
        if row_labels:
            assert len(row_labels) == n - 1
            for i, label in enumerate(row_labels, start=1):
                x = x_start + 5
                y = y_start + (n - i - 0.5) * cell_height
                self.c.drawString(x, y, str(label))

        # Data
        if data:
            for i in range(len(data)):
                for j in range(len(data[i])):
                    x = x_start + (j + 1) * cell_width + 5
                    y = y_start + (n - i - 1.5) * cell_height
                    self.c.drawString(x, y, str(data[i][j]))

    def _draw_nash_answers(self, answers: List) -> None:
        """Draw Nash equilibrium answers."""
        assert len(self.answer_places) >= 2, 'Two answer tags required for this problem'
        assert len(answers) == 2, 'Two answers required for nash problem'
        
        for i, answer in enumerate(answers):
            answer_element = self.answer_places[i]
            self._draw_text(answer_element)
            answer_element['content'] = answer if answer is not None and len(answer) > 0 else 'Does not exist'
            x, y = answer_element['position']
            answer_element['position'] = (x + 20, y - answer_element['answer_margin'] * inch)
            self._draw_text(answer_element)

    def _add_math_problems(self, problems: List[Union[Basic, str]]) -> None:
        """Add mathematical problems to the page."""
        page_width, page_height = self.document['size']
        left_margin = self.grid['lm']
        top_margin = self.grid['tm']
        bottom_margin = self.grid['bm']
        n = len(problems)
        cell_width = (page_width - 2 * left_margin)
        cell_height = (page_height - (bottom_margin + top_margin)) / n
        max_image_width = cell_width - 20
        max_image_height = cell_height - 20

        for i, item in enumerate(problems, start=1):
            if isinstance(item, str) and (item.endswith('.jpg') or item.endswith('.png')):
                buffer = self._read_image(item)
            elif isinstance(item, Basic) or isinstance(item, str):
                buffer = self._render_expression(item)
            else:
                raise ValueError('Item type not supported')

            buffer.seek(0)
            img = ImageReader(buffer)
            img_width, img_height = img.getSize()

            scale = min(self.grid['scale_cap'],
                       min(max_image_width / img_width, max_image_height / img_height))
            scaled_width = img_width * scale
            scaled_height = img_height * scale

            y = page_height - top_margin - i * cell_height + (cell_height - scaled_height) / 2

            self.c.drawImage(img, left_margin, y, width=scaled_width, height=scaled_height)
            self.c.drawString(left_margin - 20, y + scaled_height / 2, f"{i})")

    def _read_image(self, filename: str) -> io.BytesIO:
        """Read an image file into a buffer."""
        with open(filename, 'rb') as f:
            return io.BytesIO(f.read())

    def _render_expression(self, expr: Basic) -> io.BytesIO:
        """Render a mathematical expression as an image."""
        latex_str = f"${latex(expr)}$"
        dpi = self.parser.config.dpi
        fontsize = self.parser.config.fontsize

        # Create figure with initial size
        fig = Figure(figsize=(4, 1), dpi=dpi)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.axis("off")
        text = ax.text(0.5, 0.5, latex_str, fontsize=fontsize, ha="center", va="center")

        # Draw and measure bounding box
        canvas.draw()
        renderer = canvas.get_renderer()
        bbox = text.get_window_extent(renderer=renderer)

        # Adjust figure size to fit content
        width_in = (bbox.width + 10) / dpi
        height_in = (bbox.height + 10) / dpi
        fig.set_size_inches(width_in, height_in)

        # Render to PNG in memory
        buffer = io.BytesIO()
        canvas.print_png(buffer)
        buffer.seek(0)
        
        # Clean up
        plt.close(fig)
        return buffer

    @log_exceptions(logger)
    def get_problem_pairs(self) -> Tuple[List, List]:
        """Get problem pairs based on grid type."""
        logger.debug(f"Generating problems for grid type: {self.grid['grid_type']}")
        if self.grid['grid_type'] == GridTypes.VOLUME:
            vol = Volumes('volumes')
            return vol.get_problem_pairs(self.grid['n'], self.grid['difficulty'], self.grid['x_range'])
        elif self.grid['grid_type'] == GridTypes.DERIVATIVE:
            dv = Derivative()
            return dv.get_problem_pairs(self.grid['n'], (4, 4), 4)
        elif self.grid['grid_type'] == GridTypes.TAYLOR:
            tay = TaylorSeries()
            return tay.get_problem_pairs(self.grid['n'], (1, 2), self.grid['a'])
        elif self.grid['grid_type'] == GridTypes.NASH:
            return [], []
        elif self.grid['grid_type'] == GridTypes.HORIZONTAL_TANGENT:
            ht = HorizontalTangent()
            return ht.get_problem_pairs(self.grid['n'])
        else:
            logger.error(f'Invalid problem type: {self.grid["grid_type"]}')
            sys.exit(1)

    def clean(self) -> None:
        """Clean up temporary files."""
        subprocess.run('rm output/volumes_*.jpg 2>/dev/null', shell=True)

@log_exceptions(logger)
def main():
    """Main entry point for the PDF generator."""
    # Setup logging
    setup_logging(LogConfig(
        console_level=logging.INFO,  # Show INFO and above in console
        file_level=logging.DEBUG     # Log everything to file
    ))
    
    if len(sys.argv) != 2:
        logger.error(f"Usage: {sys.argv[0]} <problems-type>.xml")
        sys.exit(1)
        
    problem_template = sys.argv[1]
    if not problem_template.endswith('.xml'):
        logger.error(f"Usage: {sys.argv[0]} <problems-type>.xml")
        sys.exit(1)
        
    try:
        generator = PDFGenerator(problem_template)
        p, ans = generator.get_problem_pairs()
        generator.generate_pdf(p, ans)
        generator.clean()
        logger.info(f"Successfully generated PDF from template: {problem_template}")
    except Exception as e:
        logger.error(f"Failed to generate PDF: {str(e)}")
        raise

if __name__ == "__main__":
    main()