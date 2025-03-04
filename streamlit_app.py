import os
import json
import base64
import openai
import fitz  # PyMuPDF
import streamlit as st

# Ensure dependencies are installed
def check_dependencies():
    try:
        import streamlit
    except ModuleNotFoundError:
        os.system("pip install streamlit")
    try:
        import openai
    except ModuleNotFoundError:
        os.system("pip install openai")
    try:
        import fitz
    except ModuleNotFoundError:
        os.system("pip install pymupdf")

check_dependencies()

# Configure page layout
st.set_page_config(layout="wide")

def main():
    st.title("Resume Customization for ML Roles")

    # --- Input fields ---
    openai_api_key = st.text_input("Enter your OpenAI API Key", type="password")
    job_title = st.text_input("Enter the Job Title")
    company_name = st.text_input("Enter the Company Name")
    job_description = st.text_area("Paste the Job Description")
    user_resume = st.file_uploader("Upload Your Resume (PDF/TXT)", type=["pdf", "txt"])
    additional_prompt = st.text_area("Add Additional Instructions (Optional)")

    resume_text = ""

    # --- Process resume using Fitz if uploaded ---
    if user_resume:
        st.write("Processing Resume using Fitz (PyMuPDF)...")
        try:
            if user_resume.type == "text/plain":
                resume_text = user_resume.read().decode("utf-8")
            elif user_resume.type == "application/pdf":
                doc = fitz.open(stream=user_resume.read(), filetype="pdf")
                resume_text = "\n".join(
                    page.get_text("text") for page in doc
                )
            st.write("Resume processed successfully. Ready to customize!")
        except Exception as e:
            st.error(f"Error processing resume with Fitz: {str(e)}")

    # --- Default Base Prompt ---
    if "default_base_prompt" not in st.session_state:
        st.session_state["default_base_prompt"] = (
            """
Act as a resume strategist specializing in machine learning roles. 
Customize my resume for the {job_title} role at {company_name}. 
Please ensure the final resume fully integrates the main responsibilities and 
qualifications from the job description. Follow these steps:

Step 1: Job Description Analysis
- Identify the top 5 technical requirements (e.g., NLP, AWS, PyTorch, MLOps, RAG).
- Extract 2-3 hidden priorities (e.g., “collaborate with cross-functional teams” = highlight Institute for Experiential AI leadership).
- List 8-10 exact terms from the JD (e.g., “real-time analytics,” “multi-modal AI,” “model optimization”).

Step 2: Resume Customization Rules

A. Summary:
- Start with “Machine Learning Professional with 4+ years in [JD-relevant field: NLP/Healthcare AI/MLOps]” and include at least 3 keywords from the JD (e.g., “LLM optimization,” “scalable RAG,” “applied research”).

B. Experience Section:
- Use precise wording from the JD. 
- Prioritize responsibilities and achievements that align with the JD’s main requirements.
- Include metrics (80% of bullets): e.g., “Improved document relevance +30%.”
- If the JD emphasizes certain tasks or outcomes (e.g., real-time analytics, resource optimization), integrate these details into the bullet points.

C. Publications & Skills:
- Retain or emphasize relevant publications, especially if they align with the JD’s focus areas.
- Reorder technical skills based on the JD (most critical first).
- Check for missing skills or tools mentioned in the JD and add them where appropriate.

D. ATS Fixes:
- Ensure proper formatting for LinkedIn/GitHub links (e.g., “LinkedIn: [link], GitHub: [link]”) 
- Use standard headings (e.g., “Work Experience,” “Skills”).

Step 3: Unique Value Proposition (UVP):
- Highlight a key accomplishment that integrates both research and industry impact.

Input Data:
- My Resume: {resume_text}
- Job Description: {job_description}

Output Format:
- Revised Resume in plain text format.
- Remove all bolding and generic/cliché filler words (e.g., “detail-oriented,” “passionate,” etc.).
- Incorporate the most relevant skills, responsibilities, and keywords from the JD throughout the resume.
"""
        )

    if "final_base_prompt" not in st.session_state:
        st.session_state["final_base_prompt"] = ""

    required_inputs_filled = bool(
        job_title and company_name and job_description and resume_text
    )

    # The effective base_prompt we use for generation
    base_prompt = st.session_state["default_base_prompt"]

    # --- Once all required inputs are provided, allow viewing/editing ---
    if required_inputs_filled:
        if st.button("View Base Prompt"):
            st.session_state["view_prompt"] = True

        if st.session_state.get("view_prompt", False):
            # Show default prompt (read-only)
            st.subheader("Base Prompt")
            st.text_area(
                "This is the base prompt being used:",
                value=st.session_state["default_base_prompt"],
                height=400,
                disabled=True,
            )

            # Button to allow editing
            if st.button("Edit Base Prompt"):
                st.session_state["edit_prompt"] = True

        if st.session_state.get("edit_prompt", False):
            user_custom_prompt = st.text_area(
                "Modify the base prompt as needed (use placeholders {job_title}, {company_name}, {job_description}, {resume_text}):",
                value=st.session_state["default_base_prompt"],
                height=400,
            )
            if st.button("Process It"):
                # Check placeholders
                placeholders = ["{job_title}", "{company_name}", "{job_description}", "{resume_text}"]
                missing = [ph for ph in placeholders if ph not in user_custom_prompt]
                if missing:
                    st.error(
                        f"Please ensure you're using the correct placeholders: {', '.join(missing)}"
                    )
                else:
                    # Format the prompt with user data
                    populated_prompt = user_custom_prompt.format(
                        job_title=job_title,
                        company_name=company_name,
                        job_description=job_description,
                        resume_text=resume_text,
                    )
                    st.session_state["final_base_prompt"] = populated_prompt
                    st.success("Your prompt has been updated! Below is the updated prompt:")
                    st.text_area("Updated Base Prompt:", value=populated_prompt, height=400, disabled=True)

    # If user has updated the base prompt, use it; otherwise use default
    if st.session_state.get("final_base_prompt"):
        base_prompt = st.session_state["final_base_prompt"]
    else:
        base_prompt = st.session_state["default_base_prompt"]

    # Append additional instructions
    if additional_prompt:
        base_prompt += f"\nAdditional Instructions: {additional_prompt}\n"

    # --- 'Still not satisfied?' copy button ---
    if st.button("Still not satisfied? Copy the JD and your resume to be pasted in another LLM service"):
        copy_prompt = f"""
Job Title: {job_title}
Company: {company_name}

Job Description:
{job_description}

Resume:
{resume_text if resume_text.strip() else '[Resume content missing]'}

Additional Instructions:
[Add any specific request here]
"""
        st.text_area(
            "Copy and paste this into another LLM service:",
            copy_prompt,
            height=300,
        )

    # --- Show a small map of placeholders for better understanding ---
    st.sidebar.subheader("Prompt Variables Map")
    st.sidebar.write(
        """
**Available placeholders:**
- `{job_title}` → Job Title
- `{company_name}` → Company Name
- `{job_description}` → Job Description
- `{resume_text}` → Extracted Resume Content

**Sample usage in your prompt**:
"Hello, I'm applying for the `{job_title}` role at `{company_name}`..."
"""
    )

    # --- Generate Customized Resume ---
    if st.button("Generate Customized Resume"):
        if not openai_api_key:
            st.error("Please enter your OpenAI API Key.")
            return
        if not resume_text:
            st.error("Please upload your resume before generating the customized version.")
            return
        
        # Final check: if the user never edited or processed the base prompt, we still auto-format placeholders
        if st.session_state.get("final_base_prompt"):
            final_prompt = st.session_state["final_base_prompt"]
        else:
            # Attempt to auto-populate placeholders in the default prompt
            try:
                final_prompt = st.session_state["default_base_prompt"].format(
                    job_title=job_title,
                    company_name=company_name,
                    job_description=job_description,
                    resume_text=resume_text
                )
            except KeyError:
                # if placeholders missing from the string, fallback
                final_prompt = st.session_state["default_base_prompt"]

        openai_client = openai.OpenAI(api_key=openai_api_key)
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": final_prompt}],
            )
            st.subheader("Customized Resume:")
            st.text_area("Generated Content:", response.choices[0].message.content, height=500)
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")

if __name__ == "__main__":
    main()
