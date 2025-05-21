import streamlit as st
import base64
from openai import OpenAI
import io

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
        docs_service = build("docs", "v1", credentials=creds)
        drive_service = build("drive", "v3", credentials=creds)

        # 1. Create a new Google Doc
        title = "Rightsize AI Output"
        new_doc = docs_service.documents().create(body={"title": title}).execute()
        document_id = new_doc.get("documentId")
        st.success(f"Created Google Doc: https://docs.google.com/document/d/{document_id}/edit")

        # 2. Insert the GPT Output Text
        requests = [
            {
                "insertText": {
                    "location": {
                        "index": 1, # Insert at the beginning of the document body
                    },
                    "text": gpt_output_text + "\n\n" # Add some space after the text
                }
            },
            {
                 "insertText": {
                    "location": {
                        "index": 1, # Insert title before the text
                    },
                    "text": f"Rightsize AI Analysis for {st.session_state.room} ({st.session_state.goal})\n\n"
                 }
            }
        ]

        docs_service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()


        # 3. Upload the Image to Google Drive and Insert into Doc
        # Reset the file pointer before reading for upload
        image_file.seek(0)
        file_metadata = {"name": "uploaded_room_image", "mimeType": "image/jpeg"} # Adjust mimeType if needed
        media = MediaIoBaseUpload(image_file, mimetype=file_metadata["mimeType"], resumable=True)
        uploaded_file_in_drive = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        file_id = uploaded_file_in_drive.get("id")
        st.info(f"Uploaded image to Google Drive with ID: {file_id}")

        # Insert the image from Drive into the document
        image_request = [
    {
        "insertInlineImage": {
            "location": {
                "index": 1 + len(f"Rightsize AI Analysis for {st.session_state.room} ({st.session_state.goal})\n\n") + len(gpt_output_text) + 2
            },
            "uri": f"https://drive.google.com/uc?export=view&id={file_id}",
            "objectSize": {
                "height": {"magnitude": 300, "unit": "PT"},
                "width": {"magnitude": 400, "unit": "PT"}
            }
        }
    }
]

        docs_service.documents().batchUpdate(
             documentId=document_id, body={"requests": image_request}
        ).execute()
        st.success("Inserted image into the document.")


        # 4. Share the Document with the User's Email
        share_permission = {
            "type": "user",
            "role": "reader", # Or 'writer' if you want them to be able to edit
            "emailAddress": user_email
        }
        drive_service.permissions().create(
            fileId=document_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
            sendNotificationEmail=True
        ).execute()
        st.success(f"Shared document with {user_email}.")

        # 5. Also share with master Google account (no notification)
        master_permission = {
            "type": "user",
            "role": "writer",  # or "reader" if you want view-only
            "emailAddress": "chris@croppedframe.xyz"
        }
        drive_service.permissions().create(
            fileId=document_id,
            body=master_permission,
            fields="id",
            sendNotificationEmail=False  # Don't send email notification to master
        ).execute()
        st.info("Also shared with master account.")

        return f"Successfully created and shared Google Doc: https://docs.google.com/document/d/{document_id}/edit"

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