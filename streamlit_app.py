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
                parts = re.split(r"(\*\*|__|\*)", line)  # Split by bold, italic, underline
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
                
# OpenAI client
client = OpenAI(api_key=st.secrets["general"]["project_oai_key"])

# Initialize session state for response & download button
if "gpt_response" not in st.session_state:
    st.session_state.gpt_response = ""  # Stores GPT output
if "download_ready" not in st.session_state:
    st.session_state.download_ready = False
export_as_pdf = ""

def encode_image(uploaded_file):
    """Convert uploaded image file to Base64."""
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

# Initialize `uploaded_file` before the conditional check
uploaded_file = None
goal = 'Select an option'

# Show title and description.
st.title("Welcome to Rightsize AI")

# Dropdown menu for goal
room = st.selectbox(
    "What type of room are you looking for advice on?", 
    ["Select an option", "Living Space", "Bedroom", "Kitchen", "Garage", "Attic"],
    index=0 # This ensures "Select an option" is the default
)


# Ensure the user picks a valid option before proceeding
if room == "Select an option":
    st.write("Please select a room before proceeding.")
else:
    # Lowercase version only in this line
    st.write(
        f"Select the goal you have for your {room.lower()}:"
    )


# Dropdown menu for goal
    goal = st.selectbox(
    "What is the goal of your project?", 
    ["Select an option", "Downsize", "Organize", "Liquidate", "Clearout"],
    index=0 # This ensures "Select an option" is the default
)


# Ensure the user picks a valid option before proceeding
if goal != "Select an option":
     # Lowercase version only in this line
    st.write(
        f"Upload an image of the {room.lower()} you would like to {goal.lower()}:"
    )


# File uploader (accepts images only)
    uploaded_file = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

    # Display streamed response
    if not st.session_state.gpt_response:    
        response_container = st.empty()  # Creates a placeholder for the response
        full_response = ""  # Store the full response

        # stage prompts from selection
        base_prompt = st.secrets["prompts"][f"{goal.lower()}_prompt"]
        prompt_w_room = base_prompt.format(room=room)

        # Convert image to Base64
        base64_image = encode_image(uploaded_file)

        # Prepare OpenAI API request
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt_w_room},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]

        # Send request to OpenAI
        with st.spinner("Analyzing image..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True
            )

        for chunk in response:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content  # Append new words
                response_container.markdown(full_response)  # Update output dynamically
                st.session_state.gpt_response = full_response
                st.session_state.download_ready = True  # Mark as ready

# Ensure the session state variable exists
if "download_ready" not in st.session_state:
    st.session_state.download_ready = False

if st.session_state.download_ready:
    # Initialize the PDF object
    pdf = PDF()
    pdf.add_page()

    # Set the header font with exact match (remove "B" if not defined in the add_font)
    pdf.set_font("ArialUnicodeBold", "", 14)  # Use the bold variant
    pdf.cell(0, 10, "Markdown to PDF", ln=True, align="C")

    text_content = st.session_state.gpt_response
    pdf.write_markdown(text_content)

    # Generate the PDF output as bytes
    pdf_output = BytesIO()
    pdf.output(pdf_output, dest="F")
    pdf_output.seek(0)  # Reset pointer to start

    # Single-click download button
    st.download_button(
        label="Download Report as PDF",
        data=pdf_output,
        file_name="gpt_response_report.pdf",
        mime="application/pdf"
    )