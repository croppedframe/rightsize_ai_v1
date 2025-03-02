import streamlit as st
import base64
from openai import OpenAI
from fpdf import FPDF
from io import BytesIO
import re
import os

# markdown to pdf function
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Add a Unicode-compatible font (check if fonts exist before loading)
        regular_font_path = "/workspaces/rightsize_ai_v1/Arial-Unicode-Regular.ttf"
        bold_font_path = "/workspaces/rightsize_ai_v1/Arial-Unicode-Bold.ttf"

        if os.path.exists(regular_font_path) and os.path.exists(bold_font_path):
            self.add_font("ArialUnicode", "", regular_font_path, uni=True)
            self.add_font("ArialUnicodeBold", "", bold_font_path, uni=True)  # Bold version
            print("Fonts loaded successfully.")
        else:
            print(f"Font files not found! Ensure '{regular_font_path}' and '{bold_font_path}' are in the correct directory.")
        
    def header(self):
        self.set_font("ArialUnicodeBold", "", 14)

    def write_markdown(self, text): # more changes to this are in gemini, also i need to unit test this rather than run the whole app
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
                parts = re.split(r"(\*\*|\*)", line)  # Split by bold, italic, underline
                self.set_font("ArialUnicode", "", 12)  # Reset to regular font
                for part in parts:
                    if part in ("**", "__"):  # Bold
                        self.set_font("ArialUnicodeBold", "", 12)
                    elif part == "*":  # Italic ( FPDF doesn't have native underline)
                        self.set_font("ArialUnicode", "I", 12)
                    elif part not in ("**", "__", "*"):  # Regular text
                        self.set_font("ArialUnicode", "", 12)
                        self.cell(0, 6, part)
                self.ln(6)  # Move to the next line

md_text = """
Absolutely! Let's transform your bedroom into a serene and organized haven. Here’s a step-by-step guide t
### Step 1: Declutter
**Clothes and Shoes**: Gather the clothes and shoes from the bed and floor. Decide which items yo **Desk Items**: Remove items from the desk that you don’t use daily. Dispose of unnecessary paper **Books and Magazines**: Sort through the magazines on the rug. Keep only the ones you will read
### Step 2: Organize
**Shelving Unit**: Use boxes or baskets on the shelving unit to store smaller items. Label them for ea **Desk**: Use drawer organizers to keep office supplies tidy. Consider a desktop organizer for freque
### Step 3: Enhance Storage
**Under Bed Storage**: Utilize storage boxes under the bed for seasonal clothes and extra blankets. **Floating Shelves**: Install floating shelves above the desk for additional storage and display of dec
### Step 4: Decorate
**Bedding**: Choose a bedding set that complements the room’s color scheme for a cohesive look. **Wall Decor**: Rearrange or replace wall art for a fresh, balanced appearance. Hang artwork symm **Lighting**: Consider adding a cozy bedside lamp for ambiance and functionality.
### Step 5: Maintain
**Daily Tidying**: Spend 5-10 minutes each day putting items back in their place to prevent clutter bu **Weekly Declutter**: Set aside time weekly to reassess and tidy up your space.
### Products to Consider
**Storage Baskets**: For organizing shelves and under-bed items. **File Holders**: To keep the desk neat and organized.
**Floating Shelves**: Add decor space without sacrificing floor space.
### Donation and Consignment Benefits
Giving away items you don’t need not only helps clear your space but also supports those in need and can
---
“A place for everything, and everything in its place.” When your bedroom is organized, you’ll feel more at pe
"""

pdf = PDF()
pdf.add_page()

# Set the header font with exact match (remove "B" if not defined in the add_font)
pdf.set_font("ArialUnicodeBold", "", 14)  # Use the bold variant
pdf.cell(0, 10, "Markdown to PDF", ln=True, align="C")

pdf.write_markdown(md_text)

# Generate the PDF output as bytes
pdf_output = BytesIO()
pdf.output(pdf_output, dest="F")
pdf_output.seek(0)  # Reset pointer to start

# Save the PDF to a file
with open("test_output.pdf", "wb") as f:
    f.write(pdf_output.getvalue())

# Provide a message to view the PDF
print("PDF saved as 'test_output.pdf'. Please open it to verify formatting.")

# Basic assertion: Check if the PDF file was created
assert os.path.exists("test_output.pdf")