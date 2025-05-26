import streamlit as st
import base64
from openai import OpenAI
import io
import markdown
import time

# Import Google API libraries
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload # For uploading to Drive

# OpenAI client
client = OpenAI(api_key=st.secrets["general"]["project_oai_key"])

def encode_image(uploaded_file):
    """Convert uploaded image file to Base64."""
    # Reset file pointer to the beginning before reading
    uploaded_file.seek(0)
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

# Initialize session state variables if they don't exist
if 'gpt_output_text' not in st.session_state:
    st.session_state.gpt_output_text = "" # To store the complete GPT response
if 'show_email_input' not in st.session_state:
    st.session_state.show_email_input = False # Control visibility of email input section


# Function to get Google Service Account credentials
@st.cache_resource # Cache the credential object
def get_google_credentials():
    # Assuming you stored the secrets as individual fields
    try:
        creds_info = {
            "type": st.secrets["google_service_account"]["type"],
            "project_id": st.secrets["google_service_account"]["project_id"],
            "private_key_id": st.secrets["google_service_account"]["private_key_id"],
            "private_key": st.secrets["google_service_account"]["private_key"],
            "client_email": st.secrets["google_service_account"]["client_email"],
            "client_id": st.secrets["google_service_account"]["client_id"],
            "auth_uri": st.secrets["google_service_account"]["auth_uri"],
            "token_uri": st.secrets["google_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["google_service_account"]["client_x509_cert_url"],
        }
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return creds
    except KeyError as e:
        st.error(f"Missing Google Service Account secret: {e}. Please check your secrets.toml file.")
        return None
    except Exception as e:
        st.error(f"Error loading Google credentials: {e}")
        return None

# Function to create and populate Google Doc
def create_and_populate_google_doc(image_file, gpt_output_text, user_email):
    creds = get_google_credentials()
    if not creds:
        return "Error: Could not load Google credentials."

    try:
        # Build the Google Docs and Drive services
        docs_service = build("docs", "v1", credentials=creds, static_discovery=False)
        drive_service = build("drive", "v3", credentials=creds, static_discovery=False)

        # 1. Upload the Image to Google Drive and Make it Publicly Accessible
        image_file.seek(0)
        image_file_metadata = {"name": image_file.name, "mimeType": image_file.type}
        image_media_body = MediaIoBaseUpload(image_file, mimetype=image_file_metadata["mimeType"], resumable=True)
        uploaded_image_in_drive = drive_service.files().create(
            body=image_file_metadata, media_body=image_media_body, fields="id"
        ).execute()
        image_file_id = uploaded_image_in_drive.get("id")
        st.info(f"Uploaded image to Google Drive with ID: {image_file_id}")

        public_permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        drive_service.permissions().create(
            fileId=image_file_id,
            body=public_permission,
            fields='id'
        ).execute()
        st.success("Image made publicly accessible for embedding.")

        # 2. Convert GPT's Markdown output to HTML
        # Remove the title/prefix from the HTML content.
        # The HTML content will *only* be the GPT output, Markdown-converted
        gpt_output_html = markdown.markdown(gpt_output_text, extensions=['fenced_code', 'tables', 'nl2br'])
        full_html_content = gpt_output_html

        # Create an in-memory HTML file from the combined HTML
        html_content_bytes = full_html_content.encode('utf-8')
        html_file_obj = io.BytesIO(html_content_bytes)

        # Upload this HTML content to Google Drive as a temporary HTML file
        html_file_metadata = {
            "name": "temp_gpt_output.html",
            "mimeType": "text/html"
        }
        html_media_body = MediaIoBaseUpload(html_file_obj, mimetype="text/html", resumable=True)

        uploaded_html_file_in_drive = drive_service.files().create(
            body=html_file_metadata, media_body=html_media_body, fields="id"
        ).execute()
        temp_html_file_id = uploaded_html_file_in_drive.get("id")
        st.info(f"Uploaded temporary HTML to Drive with ID: {temp_html_file_id}")
        time.sleep(1)

        # Convert the uploaded HTML file to a new Google Doc
        # This is your *main* document now, with GPT's formatted output
        converted_doc_metadata = {
            "name": "Rightsize AI Output",
            "mimeType": "application/vnd.google-apps.document",
            "parents": []
        }
        time.sleep(1)
        main_doc_from_html = drive_service.files().copy(
            fileId=temp_html_file_id,
            body=converted_doc_metadata,
            fields="id"
        ).execute()
        document_id = main_doc_from_html.get("id")
        st.success(f"Converted HTML to Google Doc: https://docs.google.com/document/d/{document_id}/edit")

        # 3. Prepare requests for the document (Image, then Title, then "Generated by", then content)
        requests = []
        current_index = 1

        # Insert the image at the beginning (index 1)
        requests.append(
            {
                "insertInlineImage": {
                    "location": {
                        "index": current_index
                    },
                    "uri": f"https://drive.google.com/uc?export=view&id={image_file_id}",
                    "objectSize": {
                        "height": {"magnitude": 300, "unit": "PT"},
                        "width": {"magnitude": 400, "unit": "PT"}
                    }
                }
            }
        )
        current_index += 1

        # Add a newline after the image for spacing
        requests.append(
            {
                "insertText": {
                    "location": {
                        "index": current_index
                    },
                    "text": "\n"
                }
            }
        )
        current_index += 1

        # Insert the main title and apply HEADING_1 style
        title_text = f"Rightsize AI Analysis for {st.session_state.room} ({st.session_state.goal})"
        requests.append(
            {
                "insertText": {
                    "location": {
                        "index": current_index
                    },
                    "text": title_text + "\n"
                }
            }
        )
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": current_index,
                        "endIndex": current_index + len(title_text) + 1
                    },
                    "paragraphStyle": {
                        "namedStyleType": "HEADING_1"
                    },
                    "fields": "namedStyleType"
                }
            }
        )
        current_index += len(title_text) + 1

        # Insert the "Generated by AI" text and apply NORMAL_TEXT style
        generated_by_text = "Generated by Rightsize AI."
        requests.append(
            {
                "insertText": {
                    "location": {
                        "index": current_index
                    },
                    "text": generated_by_text + "\n\n"
                }
            }
        )
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": current_index,
                        "endIndex": current_index + len(generated_by_text) + 2
                    },
                    "paragraphStyle": {
                        "namedStyleType": "NORMAL_TEXT"
                    },
                    "fields": "namedStyleType"
                }
            }
        )
        current_index += len(generated_by_text) + 2

        # The rest of the content (from GPT's HTML conversion) is already present in the document
        # from the index 'current_index' onwards. We do NOT need to insert it again.

        # Execute all document update requests in one batch
        docs_service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()
        st.success("Inserted image and custom-formatted title into the document.")

        # 4. Share the Document with the User's Email
        share_permission = {
            "type": "user",
            "role": "reader",
            "emailAddress": user_email
        }
        drive_service.permissions().create(
            fileId=document_id,
            body=share_permission,
            fields="id",
            sendNotificationEmail=True
        ).execute()
        st.success(f"Shared document with {user_email}.")

        # 5. Also share with master Google account (no notification)
        master_permission = {
            "type": "user",
            "role": "writer",
            "emailAddress": "chris@croppedframe.xyz"
        }
        drive_service.permissions().create(
            fileId=document_id,
            body=master_permission,
            fields="id",
            sendNotificationEmail=False
        ).execute()
        st.info("Also shared with master account.")

        return f"Successfully created and shared Google Doc: https://docs.google.com/document/d/{document_id}/edit"

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return f"Error creating Google Doc: {e}"

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

st.session_state.room = room 

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

st.session_state.goal = goal 

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

    # stage prompts from selection
    base_prompt = st.secrets["prompts"][f"{goal.lower()}_prompt"]
    prompt_w_room = base_prompt.format(room=room)

    # Convert image to Base64
    base64_image = encode_image(uploaded_file)
    # Only call OpenAI if we don't already have a response for this image
    if not st.session_state.gpt_output_text:
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

        # Display streamed response
        response_container = st.empty()  # Creates a placeholder for the response
        full_response = ""  # Store the full response

        for chunk in response:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content  # Append new words
                response_container.markdown(full_response)  # Update output dynamically

        # Store the full response in session state
        st.session_state.gpt_output_text = full_response
    else:
        # Display the stored response
        st.markdown(st.session_state.gpt_output_text)

    user_email = st.text_input("Enter your email to receive the Google Doc:")

    if st.button("Create and Share Google Doc"):
        if user_email:
            result = create_and_populate_google_doc(uploaded_file, st.session_state.gpt_output_text, user_email)
            st.info(result)
        else:
            st.warning("Please enter your email address.")