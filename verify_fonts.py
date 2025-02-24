import os

# Define the font paths
regular_font_path = "Arial-Unicode-Regular.ttf"
bold_font_path = "Arial-Unicode-Bold.ttf"

# Function to check if font files exist
def check_fonts():
    if os.path.exists(regular_font_path) and os.path.exists(bold_font_path):
        print("Fonts loaded successfully.")
        print(f"Regular font found at: {os.path.abspath(regular_font_path)}")
        print(f"Bold font found at: {os.path.abspath(bold_font_path)}")
    else:
        print("Font files not found! Ensure the following fonts are in the correct directory:")
        if not os.path.exists(regular_font_path):
            print(f"- Regular font: {regular_font_path} is missing.")
        if not os.path.exists(bold_font_path):
            print(f"- Bold font: {bold_font_path} is missing.")

# Call the function to verify fonts
check_fonts()