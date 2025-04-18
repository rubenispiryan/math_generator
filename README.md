# Math Worksheet PDF Generator

This project generates printable PDF worksheets for math problems such as derivatives and volume integration. The layout and content are customizable via XML templates.

---

## 🧩 Project Structure

- `generate_pdf.py`: Script to generate the worksheet PDF from XML templates
- `templates/`: Directory containing XML templates
- `assets/`: Folder for static resources (e.g., `logo.png`)
- `output/`: Folder where the generated PDFs are saved

---

### 1. Usage

Use the CLI to generate the PDF from the template:

```bash
python3 generate_pdf.py templates/derivatives.xml
python3 generate_pdf.py templates/volumes.xml
```

The argument should be a xml template with supported elements.

The generated PDFs will appear in the `output/` directory.

---

### 2. Structure

- The template file should contain a root element `document`.
- The `document` must contain 2 `page` and 1 `grid` elements.
- The `page` contains any number of static elements.
- The `grid` is a dynamic generator of math expressions.

**Note**: The first `page` is the page of problems,
the second `page` is the page of answers.


---

### 3. Static Elements
- `<document>`: Configure the resulting document.

  - Attributes:
    - `size` (optional): either `letter` or `a4`
    - `meta_title` (optional): the title embedded in the PDF metadata
    - `name` (optional): the output PDF filename (without `.pdf` extension)

- `<image>`: Places an image on the page.

  - Attributes:
    - `path`: Path to the image file.
    - `x`, `y`: Coordinates on the page.
    - `width`, `height`: Dimensions of the image.

- `<qr>`: Places a QR code on the page.

  - Attributes:
    - `content`: URL or text to encode in the QR code.
    - `x`, `y`: Coordinates on the page.
    - `size`: Size of the QR code.

- `<text>`: Renders a line of text.

  - Attributes:
    - `x`, `y`: Coordinates on the page.
    - `size`: Font size.
    - `font` (optional): Font name (e.g., `Helvetica-Bold`).
    - `link` (optional): Must be a URL, makes the text clickable.
  - Content: The text to render.
---

### 4. Dynamic Elements

- `<grid>`: Inserts a grid of problems.
  - Attributes:
    - `n`: Number of problems to generate.
    - `type`: Type of problem. Supported types: `derivatives`, `volumes`.
    - `difficulty` (optional): For volume problems **ONLY**, set difficulty level.
      - Options: simple, hard, extreme (simple is recommended to get nice graphs)
    - `x_left`, `x_right` (optional): For volume problems, define the region of the graph.
    - `lm`: Left margin in pixels.
    - `tm`: Top margin in pixels.
    - `bm`: Bottom margin in pixels.

---

