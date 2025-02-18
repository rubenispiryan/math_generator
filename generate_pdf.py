import io
import os
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
from sympy.printing.preview import preview

from derivatives import get_problem_pairs


def generate_pdf(problems, answers, filename='math_worksheets.pdf'):
    """
    Generate a PDF with math problems and answers in a 3x3 grid layout.
    """
    if len(problems) != 9 or len(answers) != 9:
        raise ValueError("Both problems and answers must contain exactly 9 expressions")

    c = canvas.Canvas(filename, pagesize=letter)
    page_width, page_height = letter

    # Layout configuration
    left_margin = 50
    top_margin = 50
    cell_width = (page_width - 2 * left_margin) / 3
    cell_height = (page_height - 2 * top_margin) / 3
    max_image_width = cell_width - 20
    max_image_height = cell_height - 20

    def render_expressions(expressions):
        """Render SymPy expressions to image buffers with proper LaTeX handling"""
        buffers = []
        preamble = r'\documentclass[20pt]{article}' + \
                   r'\usepackage{amsmath, amssymb, amsthm}' + \
                   r'\begin{document}'
                   # r'\usepackage[active]{preview}' + \

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
                        # preamble=preamble,
                        dvioptions=['-D', '300', '-T', 'tight'],
                        fontsize=font_size,
                        euler=False
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to render equation {i + 1}: {str(e)}") from e

                with open(temp_png, 'rb') as f:
                    buffers.append(io.BytesIO(f.read()))
        return buffers

    def draw_grid(canvas, buffers, title):
        """Draw a 3x3 grid of equations on a canvas page"""
        # Add title
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(left_margin, page_height - top_margin + 10, title)

        # Draw equations in grid
        for i in range(9):
            row = i // 3
            col = i % 3

            buffer = buffers[i]
            buffer.seek(0)
            img = ImageReader(buffer)
            img_width, img_height = img.getSize()

            # Calculate scaling factor
            scale_cap = 1.2
            scale = min(scale_cap, min(max_image_width / img_width, max_image_height / img_height))
            print(f"Current problem: {i}, Current scaling: {scale}")
            scaled_width = img_width * scale
            scaled_height = img_height * scale

            # Calculate position
            x = left_margin + col * cell_width + (cell_width - scaled_width) / 2
            y = page_height - top_margin - (row + 1) * cell_height + (cell_height - scaled_height) / 2

            canvas.drawImage(img, x, y, scaled_width, scaled_height)

    # Render problems and answers to image buffers
    problem_buffers = render_expressions(problems)
    answer_buffers = render_expressions(answers)

    # Create problems page
    draw_grid(c, problem_buffers, "Math Problems - Worksheet")
    c.showPage()

    # Create answers page
    draw_grid(c, answer_buffers, "Answer Key")
    c.showPage()

    # Save PDF
    c.save()


if __name__ == "__main__":
    p, ans = get_problem_pairs(9, (4, 4), 2)
    print('Got problems')
    generate_pdf(p, ans, 'math_worksheet.pdf')