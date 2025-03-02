import pytest
from io import BytesIO
import re
import os
from fpdf import FPDF

# markdown to pdf function
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Add a Unicode-compatible font (check if fonts exist before loading)
        regular_font_path = "Arial-Unicode-Regular.ttf"  # Change to your path
        bold_font_path = "Arial-Unicode-Bold.ttf"  # Change to your path

        if os.path.exists(regular_font_path) and os.path.exists(bold_font_path):
            self.add_font("ArialUnicode", "", regular_font_path, uni=True)
            self.add_font("ArialUnicodeBold", "", bold_font_path, uni=True)  # Bold version
            print("Fonts loaded successfully.")
        else:
            print(f"Font files not found! Ensure '{regular_font_path}' and '{bold_font_path}' are in the correct directory.")

    def header(self):
        self.set_font("ArialUnicodeBold", "", 14)
        self.cell(0, 10, "Markdown to PDF", ln=True, align="C")

    def write_markdown(self, text):
        lines = text.split("\n")
        for line in lines:
            if line.startswith("# "):  # H1
                self.set_font("ArialUnicodeBold", "", 16)
                self.cell(0, 10, line[2:], ln=True)
            elif line.startswith("## "):  # H2
                self.set_font("ArialUnicodeBold", "", 14)
                self.cell(0, 8, line[3:], ln=True)
            elif re.match(r"^[-*] ", line):  # Bullet points
                self.set_font("ArialUnicode", "", 12)
                self.cell(10)  # Indent
                self.cell(0, 6, "  " + line[2:], ln=True)  # Added extra space for bullet
            else:  # Regular text with bold/italic
                parts = re.split(r"(\*\*|\*)", line)  # Split by bold, italic
                self.set_font("ArialUnicode", "", 12)  # Reset to regular font
                for part in parts:
                    if part == "**":  # Bold
                        self.set_font("ArialUnicodeBold", "", 12)
                    elif part == "*":  # Italic
                        self.set_font("ArialUnicode", "I", 12)
                    elif part not in ("**", "*"):  # Regular text
                        self.cell(0, 6, part)
                self.ln(6)  # Move to the next line

def test_pdf_generation():
    md_text = """
# Heading 1
This is regular text.
**This is bold text.**
*This is italic text.*
- Bullet point 1
- Bullet point 2
"""

    pdf = PDF()
    pdf.add_page()
    pdf.write_markdown(md_text)

    pdf_output = BytesIO()
    pdf.output(pdf_output, dest="F")
    pdf_output.seek(0)

    # Output PDF to a file for manual inspection
    with open("test_output.pdf", "wb") as f:
        f.write(pdf_output.getvalue())

    # Provide a message to view the PDF
    print("PDF saved as 'test_output.pdf'. Please open it to verify formatting.")

    # Basic assertion: Check if the PDF file was created
    assert os.path.exists("test_output.pdf")