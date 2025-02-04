import streamlit as st
import base64
from openai import OpenAI

# OpenAI client
client = OpenAI(api_key=st.secrets["general"]["project_oai_key"])

def encode_image(uploaded_file):
    """Convert uploaded image file to Base64."""
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

# Show title and description.
st.title("Rightsize AI v1")
st.write(
    "Upload an image of a room you would like suggestions to help liquidate the items inside:"
)

# File uploader (accepts images only)
uploaded_file = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

    # Convert image to Base64
    base64_image = encode_image(uploaded_file)

    # Prepare OpenAI API request
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": [
            {"type": "text", "text": "Pretend you are a move manager and are dealing with a client who has a goal to liquidate the items in their space. The customer has provided the following image of their [insert space here] please provide step by step instructions based on the particular items that are in the image on how the customer can acccomplish their goal. Provide resources for the customer to read related to their goal. Please make mention of partciular items in the room which may have value on the secondary market. Look at the image as if you were a move manager seeing the space for the first time. Please use an upbeat tone, and end the response with an inspirational quote that will get the customer excited to start their project, and relate it to how they will feel when the project is complete. "},
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

    # Display streamed response
    response_container = st.empty()  # Creates a placeholder for the response
    full_response = ""  # Store the full response

    for chunk in response:
        if chunk.choices[0].delta.content:
            full_response += chunk.choices[0].delta.content  # Append new words
            response_container.markdown(full_response)  # Update output dynamically