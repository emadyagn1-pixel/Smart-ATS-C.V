# main.py (v12.0.1 - Fixed Skills Suggester to suggest only technical skills, no language proficiencies)

import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
import fitz  # PyMuPDF
import docx
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid

# --- Language Detection ---
from langdetect import detect, LangDetectException

# --- LangChain Core Components ---
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

# --- Import our data structures ---
from schemas import (
    ParsedCV, CVText, CompleteAnalysisResponse, QualityReport, 
    ATSComplianceReport, ATSCheckItem, RewrittenCV, RewrittenExperience,
    JobListing, CareerRecommendation, CareerRecommendationResponse
)

# --- Environment and API Key Setup ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please set it.")

# --- 1. Initialize the FastAPI App ---
app = FastAPI(
    title="Smart CV ATS Parser & Career Platform",
    description="An intelligent multilingual platform for CV analysis, ATS compliance checking, career optimization, and job matching.",
    version="12.0.1"
)
# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (or specify your domains)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Initialize AI Models ---
llm = ChatOpenAI(
    openai_api_key=api_key,
    model="gpt-4.1-mini",
    temperature=0.3
)

# --- 3. Language Configuration ---
SUPPORTED_LANGUAGES = {
    "en": "English",
    "de": "German (Deutsch)",
    "ar": "Arabic (العربية)"
}

def get_language_name(lang_code: str) -> str:
    """Get full language name from code"""
    return SUPPORTED_LANGUAGES.get(lang_code, "English")

# --- 4. Define Prompts and Chains (UPDATED with translation support) ---

# Chain 1: CV Parsing (UPDATED)
prompt_parser = ChatPromptTemplate.from_messages([
    ("system", """You are a world-class AI expert in parsing resumes (CVs) for Applicant Tracking Systems (ATS).
Your goal is to extract structured information from the provided CV text (English, German, or Arabic).

**EXTRACTION INSTRUCTIONS:**

1. **Personal Information:**
   - name, email, phone, address, summary

2. **Skills:**
   - Extract ALL skills (technical, soft, tools, languages, frameworks)
   - Return as a list of strings

3. **Experience:**
   - For each job: position, company, duration, description
   - Extract responsibilities and achievements

4. **Education:**
   - For each degree: degree, university/institution, year

5. **Projects:** (NEW!)
   - For each project: title, description, technologies, metrics
   - Extract quantifiable results (e.g., "90% accuracy", "1000+ users")

6. **Languages:** (NEW!)
   - For each language: language name, proficiency level
   - Levels: Native, Fluent, Advanced, Intermediate, Basic

7. **Hobbies:** (NEW!)
   - Extract hobbies/interests as a list of strings

**OUTPUT FORMAT:**
Return a valid JSON object matching this structure:
{{
  "name": "string",
  "email": "string",
  "phone": "string",
  "address": "string",
  "summary": "string",
  "skills": ["skill1", "skill2", ...],
  "experience": [
    {{
      "position": "string",
      "company": "string",
      "duration": "string",
      "description": "string"
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "institution": "string",
      "year": "string"
    }}
  ],
  "projects": [
    {{
      "title": "string",
      "description": "string",
      "technologies": "string",
      "metrics": "string"
    }}
  ],
  "languages": [
    {{
      "language": "string",
      "proficiency": "string"
    }}
  ],
  "hobbies": ["hobby1", "hobby2", ...]
}}

**IMPORTANT:**
- Extract information in the ORIGINAL language of the CV
- If a field is missing, use null or empty array
- Be precise and extract all available information
"""),
    ("human", "{cv_text}")
])

parser_chain = prompt_parser | llm | JsonOutputParser()

# Chain 2: Quality Analysis
prompt_quality = ChatPromptTemplate.from_messages([
    ("system", """You are an expert CV reviewer. Analyze the quality of this CV and provide a score (0-100) with feedback.

**EVALUATION CRITERIA:**
1. Completeness (all sections present?)
2. Clarity (easy to read and understand?)
3. Achievements (quantifiable results?)
4. Keywords (industry-relevant terms?)
5. Formatting (professional structure?)

**CRITICAL: OUTPUT MUST BE VALID JSON!**
- overall_score MUST be a NUMBER (e.g., 85, not "eighty-five" or "seventy")
- Use ONLY numeric digits for overall_score: 0, 10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100
- All values must be properly quoted strings or numbers
- No trailing commas
- No comments in JSON
- DO NOT write numbers as words (e.g., "seventy" is INVALID, use 70)

**OUTPUT FORMAT (EXACT):**
{{
  "overall_score": 85,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}

**EXAMPLE:**
{{
  "overall_score": 65,
  "strengths": ["Good experience", "Relevant education"],
  "weaknesses": ["Missing contact info", "No metrics"],
  "suggestions": ["Add phone number", "Include achievements"]
}}
"""),
    ("human", "{parsed_cv}")
])

quality_chain = prompt_quality | llm | JsonOutputParser()

# Chain 3: ATS Compliance Check
prompt_ats = ChatPromptTemplate.from_messages([
    ("system", """You are an ATS (Applicant Tracking System) compliance expert. Check if this CV meets ATS standards.

**ATS COMPLIANCE CHECKLIST (10 items):**
1. Contact information clearly visible
2. Standard section headings (Experience, Education, Skills)
3. No images, tables, or complex formatting
4. Keywords from job descriptions
5. Consistent date formats
6. Bullet points for achievements
7. Quantifiable results (numbers, percentages)
8. Professional summary present
9. Education details complete
10. Skills section well-organized

**CRITICAL: OUTPUT MUST BE VALID JSON!**
- overall_score MUST be a NUMBER (e.g., 80, not "eighty")
- All values must be properly quoted strings or numbers
- No trailing commas

**OUTPUT FORMAT:**
{{
  "overall_score": 80,
  "passed_checks": [
    {{"item": "Contact information", "status": "pass", "details": "Email and phone clearly visible"}}
  ],
  "failed_checks": [
    {{"item": "Quantifiable results", "status": "fail", "details": "Missing metrics in experience section"}}
  ],
  "critical_issues": ["issue1", "issue2"],
  "recommendations": ["recommendation1", "recommendation2"]
}}
"""),
    ("human", "{parsed_cv}")
])

ats_chain = prompt_ats | llm | JsonOutputParser()

# Chain 4: CV Rewriting (UPDATED with translation support)
def create_rewriter_prompt(output_language: str):
    """Create a rewriter prompt with specified output language"""
    lang_name = get_language_name(output_language)
    
    return ChatPromptTemplate.from_messages([
        ("system", f"""You are an expert CV writer and translator. Your task is to SIGNIFICANTLY IMPROVE and rewrite the CV sections in **{lang_name}** language.

**CRITICAL: THIS IS NOT JUST TRANSLATION! YOU MUST IMPROVE THE CONTENT!**

**IMPROVEMENT RULES (MANDATORY):**

1. **Strong Action Verbs (REQUIRED):**
   - Replace weak verbs with powerful ones:
     * "Assisted" → "Coordinated", "Facilitated", "Supported"
     * "Worked on" → "Led", "Developed", "Implemented", "Optimized"
     * "Helped" → "Enabled", "Drove", "Accelerated"
     * "Did" → "Executed", "Delivered", "Achieved"
   - Start EVERY bullet point with a strong action verb

2. **Add Context and Scope (REQUIRED):**
   - Add WHO: team size, stakeholders (e.g., "Led team of 5 engineers")
   - Add WHAT: specific technologies, tools, methods
   - Add WHERE: scale, platform, environment (e.g., "across 3 departments")
   - Add WHEN: timeframe, frequency (e.g., "daily", "quarterly")

3. **Emphasize Impact (REQUIRED):**
   - Add qualitative impact even without numbers:
     * "improving team productivity"
     * "enhancing user experience"
     * "reducing manual work"
     * "streamlining processes"
     * "increasing customer satisfaction"
   - If numbers exist in original, HIGHLIGHT them prominently
   - If no numbers exist, focus on qualitative improvements

4. **Industry Keywords (REQUIRED):**
   - Add relevant industry-specific terminology
   - Include technical skills and tools mentioned
   - Use standard job-related keywords for ATS

5. **Professional Structure (REQUIRED):**
   - Make descriptions clear, concise, and scannable
   - Use professional, formal language in {lang_name}
   - Avoid vague or generic statements

**TRANSLATION RULES:**
- If input is in different language, TRANSLATE to {lang_name}
- Use industry-standard terminology in {lang_name}
- Maintain original meaning and facts
- DO NOT invent numbers or metrics that don't exist

**EXAMPLE TRANSFORMATION:**

Before (weak):
"Assisted cooks in the preparation of salads."

After (strong):
"Koordinierte die Zubereitung verschiedener Salate (grüne Salate, Obstsalate, Nudelsalate) in einem schnelllebigen Küchenumfeld, wodurch die Effizienz der Lebensmittelzubereitung verbessert und die Wartezeiten für Gäste reduziert wurden."

Improvements:
- Strong verb: "Koordinierte" (Coordinated)
- Context: "verschiedener Salate", "schnelllebiges Küchenumfeld"
- Impact: "Effizienz verbessert", "Wartezeiten reduziert"
- Professional language in German

**OUTPUT FORMAT:**
{{{{
  "rewritten_summary": "string",
  "rewritten_experience": [
    {{{{
      "position": "string",
      "company": "string",
      "duration": "string",
      "original_description": "string",
      "rewritten_description": "string (SIGNIFICANTLY IMPROVED with context, impact, and strong verbs)",
      "improvements": ["List of specific improvements made"]
    }}}}
  ],
  "estimated_new_ats_score": 85
}}}}
"""),
        ("human", "{parsed_cv}")
    ])

# Chain 5: Skills Suggestion (UPDATED with translation support)
def create_skills_suggester_prompt(output_language: str):
    """Create a skills suggester prompt with specified output language"""
    lang_name = get_language_name(output_language)
    
    return ChatPromptTemplate.from_messages([
        ("system", f"""You are a career advisor. Based on the CV, suggest additional TECHNICAL skills that would be valuable.

**OUTPUT LANGUAGE:** {lang_name}

**IMPORTANT RULES:**
1. ✅ **ONLY suggest TECHNICAL skills** (programming languages, frameworks, tools, technologies, methodologies)
2. ❌ **DO NOT suggest language skills** (English, German, French, etc.) - languages are personal information
3. ❌ **DO NOT suggest soft skills** (communication, leadership, etc.) - focus on technical skills only

**Suggest 5-10 TECHNICAL skills that:**
1. Are relevant to the person's technical field
2. Are in high demand in the industry
3. Would complement existing technical skills
4. Are realistic to learn
5. Are specific technologies, tools, or frameworks

**EXAMPLES of GOOD suggestions:**
- Programming: Python, Java, C++, JavaScript
- Frameworks: TensorFlow, PyTorch, React, Django
- Tools: Docker, Kubernetes, Git, Jenkins
- Cloud: AWS, Azure, Google Cloud
- Databases: PostgreSQL, MongoDB, Redis
- Methodologies: MLOps, DevOps, Agile, CI/CD

**EXAMPLES of BAD suggestions (DO NOT include):**
- ❌ "German Language Proficiency"
- ❌ "English (C1 level)"
- ❌ "Communication Skills"
- ❌ "Leadership"

Return a JSON array of TECHNICAL skill names ONLY:
["skill1", "skill2", ...]
"""),
        ("human", "{parsed_cv}")
    ])

# Chain 6: Career Identifier (NEW - identifies most suitable career)
def create_career_identifier_prompt(output_language: str):
    """Create a career identifier prompt with specified output language"""
    lang_name = get_language_name(output_language)
    
    return ChatPromptTemplate.from_messages([
        ("system", f"""You are an expert career advisor and job market analyst. Your task is to identify the most suitable career/profession for the person based on their CV.

**OUTPUT LANGUAGE:** {lang_name}

**ANALYSIS CRITERIA:**
1. **Education Background:** What did they study? What degrees/certifications?
2. **Work Experience:** What roles have they held? What industries?
3. **Skills & Expertise:** What technical and soft skills do they have?
4. **Projects & Achievements:** What have they built or accomplished?
5. **Career Trajectory:** What is their career progression pattern?

**YOUR TASK:**
- Analyze the CV comprehensively
- Identify the MOST suitable career/profession title
- Provide confidence score (0-100)
- Explain WHY this career fits (based on education, experience, skills)
- Suggest 2-3 alternative career options

**IMPORTANT:**
- Be specific: "Data Scientist" not just "IT Professional"
- Consider current market demand
- Match skills to real job titles
- Output MUST be in {lang_name}

**OUTPUT FORMAT:**
{{{{
  "recommended_career": "Specific career title in {lang_name}",
  "confidence": 85,
  "reasoning": "Detailed explanation why this career fits, mentioning specific education, experience, and skills",
  "alternative_careers": ["Alternative 1", "Alternative 2", "Alternative 3"]
}}}}
"""),
        ("human", "{parsed_cv}")
    ])

# --- 5. Helper Functions ---

def extract_text_from_file(uploaded_file: UploadFile) -> str:
    """Extract text from PDF or DOCX file"""
    file_bytes = uploaded_file.file.read()
    file_extension = uploaded_file.filename.split('.')[-1].lower()
    
    if file_extension == 'pdf':
        # Extract from PDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    
    elif file_extension in ['docx', 'doc']:
        # Extract from DOCX
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_extension}")

def detect_language(text: str) -> str:
    """Detect the language of the text"""
    try:
        lang = detect(text)
        if lang in ['en', 'de', 'ar']:
            return lang
        return 'en'  # Default to English
    except LangDetectException:
        return 'en'

def filter_null_values(data: Dict) -> Dict:
    """Remove null values from dictionaries recursively"""
    if isinstance(data, dict):
        return {k: filter_null_values(v) for k, v in data.items() if v is not None and v != "" and v != []}
    elif isinstance(data, list):
        return [filter_null_values(item) for item in data if item is not None and item != "" and item != {}]
    else:
        return data

# --- 6. API Endpoints ---

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Smart CV ATS Parser & Career Platform API",
        "version": "12.0.1",
        "features": [
            "✅ Multi-language CV parsing (English, German, Arabic)",
            "✅ Multi-language output (translate CV to any supported language)",
            "✅ **NEW v12** Clean output: Final improved CV only (no original CV clutter)",
            "✅ **NEW v12** Improvements summary: See exactly what was improved",
            "✅ ATS compliance checking (10 criteria)",
            "✅ Quality assessment (0-100 score)",
            "✅ Improved CV rewriting with strong action verbs and context",
            "✅ ATS improvement tracking (shows gap to 90% target)",
            "✅ Personalized recommendations for reaching 90% ATS score",
            "✅ Career identification (identifies most suitable profession)",
            "✅ Skills suggestion",
            "✅ Projects, Languages, and Hobbies extraction",
            "✅ Manual social/professional links input",
            "✅ Career recommendation system",
            "✅ Job matching (Free: BA-API, Premium: LinkedIn + Indeed)"
        ],
        "supported_languages": SUPPORTED_LANGUAGES,
        "endpoints": {
            "/analyze-and-rewrite/": "Complete CV analysis and rewriting",
            "/recommend-careers/": "Get career recommendations based on CV",
            "/docs": "Interactive API documentation"
        }
    }

@app.post("/analyze-and-rewrite/", response_model=CompleteAnalysisResponse, tags=["Complete Analysis & Rewriting"])
async def analyze_and_rewrite_cv(
    cv_file: UploadFile = File(...),
    output_language: str = Form("de", description="Output language for rewritten CV: 'en', 'de', or 'ar'"),
    # Optional social/professional links (manual input)
    github: str = Form("", description="GitHub profile URL (e.g., https://github.com/username)"),
    linkedin: str = Form("", description="LinkedIn profile URL (e.g., https://linkedin.com/in/username)"),
    kaggle: str = Form("", description="Kaggle profile URL (e.g., https://kaggle.com/username)"),
    portfolio: str = Form("", description="Personal portfolio or website URL"),
    stackoverflow: str = Form("", description="Stack Overflow profile URL"),
    medium: str = Form("", description="Medium or blog URL"),
    twitter: str = Form("", description="Twitter/X profile URL")
):
    """
    **(RECOMMENDED)** Upload a CV file to get:
    - Parsed data (including NEW fields: projects, languages, hobbies)
    - Quality report
    - ATS compliance report
    - Rewritten CV with improvements (in specified language)
    
    **NEW FEATURES:**
    - **Multi-language output:** Choose output language (en, de, ar)
    - **Translation:** CV will be translated to the chosen language
    - **Social links:** Add your professional links manually
    """
    
    # Validate output language
    if output_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid output_language. Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    
    # Validate social links
    social_links_data = {}
    
    if github and github.strip():
        if "github.com" not in github.lower():
            raise HTTPException(status_code=400, detail="Invalid GitHub URL. Must contain 'github.com'")
        social_links_data["github"] = github.strip()
    
    if linkedin and linkedin.strip():
        if "linkedin.com" not in linkedin.lower():
            raise HTTPException(status_code=400, detail="Invalid LinkedIn URL. Must contain 'linkedin.com'")
        social_links_data["linkedin"] = linkedin.strip()
    
    if kaggle and kaggle.strip():
        if "kaggle.com" not in kaggle.lower():
            raise HTTPException(status_code=400, detail="Invalid Kaggle URL. Must contain 'kaggle.com'")
        social_links_data["kaggle"] = kaggle.strip()
    
    if portfolio and portfolio.strip():
        if not any(x in portfolio.lower() for x in ["http", ".com", ".io", ".dev", ".net", ".org"]):
            raise HTTPException(status_code=400, detail="Invalid Portfolio URL. Must be a valid URL")
        social_links_data["portfolio"] = portfolio.strip()
    
    if stackoverflow and stackoverflow.strip():
        if "stackoverflow.com" not in stackoverflow.lower():
            raise HTTPException(status_code=400, detail="Invalid Stack Overflow URL. Must contain 'stackoverflow.com'")
        social_links_data["stackoverflow"] = stackoverflow.strip()
    
    if medium and medium.strip():
        if "medium.com" not in medium.lower():
            raise HTTPException(status_code=400, detail="Invalid Medium URL. Must contain 'medium.com'")
        social_links_data["medium"] = medium.strip()
    
    if twitter and twitter.strip():
        if not any(x in twitter.lower() for x in ["twitter.com", "x.com"]):
            raise HTTPException(status_code=400, detail="Invalid Twitter URL. Must contain 'twitter.com' or 'x.com'")
        social_links_data["twitter"] = twitter.strip()
    
    # Extract text from file
    extracted_text = extract_text_from_file(cv_file)
    
    if not extracted_text or len(extracted_text) < 50:
        raise HTTPException(status_code=400, detail="Could not extract sufficient text from the file. Please check the file format.")
    
    # Detect input language
    input_language = detect_language(extracted_text)
    
    # Step 1: Parse CV
    parsed_data_dict = await parser_chain.ainvoke({"cv_text": extracted_text})
    
    # Add manually provided social links if any
    if social_links_data:
        parsed_data_dict["social_links"] = social_links_data
    
    # Filter null values from parsed data
    if "projects" in parsed_data_dict and parsed_data_dict["projects"]:
        parsed_data_dict["projects"] = [filter_null_values(p) for p in parsed_data_dict["projects"]]
    
    if "languages" in parsed_data_dict and parsed_data_dict["languages"]:
        parsed_data_dict["languages"] = [filter_null_values(l) for l in parsed_data_dict["languages"]]
    
    if "education" in parsed_data_dict and parsed_data_dict["education"]:
        parsed_data_dict["education"] = [filter_null_values(e) for e in parsed_data_dict["education"]]
    
    # Step 2: Quality Analysis
    quality_data = await quality_chain.ainvoke({"parsed_cv": json.dumps(parsed_data_dict, ensure_ascii=False)})
    
    # Step 3: ATS Compliance Check
    ats_data = await ats_chain.ainvoke({"parsed_cv": json.dumps(parsed_data_dict, ensure_ascii=False)})
    
    # Step 4: Suggest Skills (in output language)
    skills_prompt = create_skills_suggester_prompt(output_language)
    skills_chain = skills_prompt | llm | JsonOutputParser()
    suggested_skills = await skills_chain.ainvoke({"parsed_cv": json.dumps(parsed_data_dict, ensure_ascii=False)})
    
    # Step 5: Identify Career (in output language)
    career_prompt = create_career_identifier_prompt(output_language)
    career_chain = career_prompt | llm | JsonOutputParser()
    career_data = await career_chain.ainvoke({"parsed_cv": json.dumps(parsed_data_dict, ensure_ascii=False)})
    
    # Step 6: Rewrite CV (in output language)
    rewriter_prompt = create_rewriter_prompt(output_language)
    rewriter_chain = rewriter_prompt | llm | JsonOutputParser()
    rewritten_data = await rewriter_chain.ainvoke({"parsed_cv": json.dumps(parsed_data_dict, ensure_ascii=False)})
    
    # Calculate improvements
    original_ats = ats_data.get("overall_score", 0)
    improved_ats = rewritten_data.get("estimated_new_ats_score", original_ats + 10)
    combined_skills = list(set(parsed_data_dict.get("skills", []) + (suggested_skills if isinstance(suggested_skills, list) else [])))
    
    # Build improvements_made list
    improvements_made = []
    if input_language != output_language:
        lang_names = {"en": "English", "de": "German", "ar": "Arabic"}
        improvements_made.append(f"Translated CV from {lang_names.get(input_language, input_language)} to {lang_names.get(output_language, output_language)}")
    
    improvements_made.append(f"Improved professional summary with strong action verbs and context")
    improvements_made.append(f"Enhanced {len(rewritten_data.get('rewritten_experience', []))} experience descriptions with impact and scope")
    
    if isinstance(suggested_skills, list) and len(suggested_skills) > 0:
        improvements_made.append(f"Added {len(suggested_skills)} suggested skills based on experience")
    
    improvements_made.append(f"Improved ATS compliance from {original_ats}% to {improved_ats}% (+{improved_ats - original_ats}%)")
    improvements_made.append(f"Applied industry-specific keywords and professional terminology")
    
    # Prepare response
    response = {
        "final_cv": {
            "name": parsed_data_dict.get("name") or "",
            "email": parsed_data_dict.get("email") or "",
            "phone": parsed_data_dict.get("phone") or "",
            "address": parsed_data_dict.get("address") or "",
            "summary": rewritten_data.get("rewritten_summary", ""),
            "skills": combined_skills,
            "experience": rewritten_data.get("rewritten_experience", []),
            "education": parsed_data_dict.get("education", []),
            "projects": parsed_data_dict.get("projects", []),
            "languages": parsed_data_dict.get("languages", []),
            "hobbies": parsed_data_dict.get("hobbies", []),
            "social_links": social_links_data
        },
        "career_recommendation": {
            "recommended_career": career_data.get("recommended_career", "Unknown"),
            "confidence": career_data.get("confidence", 0),
            "reasoning": career_data.get("reasoning", ""),
            "alternative_careers": career_data.get("alternative_careers", [])
        },
        "improvements_summary": {
            "ats_score_before": original_ats,
            "ats_score_after": improved_ats,
            "improvements_made": improvements_made,
            "translation_applied": input_language != output_language,
            "input_language": input_language,
            "output_language": output_language
        },
        "improvement_notes": {
            "original_ats_score": ats_data.get("overall_score", 0),
            "improved_ats_score": rewritten_data.get("estimated_new_ats_score", ats_data.get("overall_score", 0) + 10),
            "target_ats_score": 90,
            "gap_to_target": max(0, 90 - rewritten_data.get("estimated_new_ats_score", ats_data.get("overall_score", 0) + 10)),
            "missing_for_90_percent": [
                "Quantifiable metrics (e.g., 'Improved efficiency by 30%', 'Managed team of 5 engineers')",
                "Specific numbers (e.g., 'Served 10,000+ users daily', 'Generated $2M in revenue')",
                "Measurable achievements (e.g., 'Reduced costs by 25%', 'Increased customer satisfaction by 40%')",
                "Project scope details (e.g., 'Led 3 major projects over 6 months', 'Delivered to 50+ clients')"
            ] if rewritten_data.get("estimated_new_ats_score", ats_data.get("overall_score", 0) + 10) < 90 else [],
            "recommendation": "To reach 90% ATS score, please add specific quantifiable metrics to your achievements. Without concrete numbers, we can improve your CV to ~75-80% ATS compliance through better language, structure, and keywords. For 85-90%, you'll need to provide measurable results from your work experience." if rewritten_data.get("estimated_new_ats_score", ats_data.get("overall_score", 0) + 10) < 90 else "Excellent! Your CV meets high ATS standards.",
            "examples": [
                "Instead of: 'Worked on projects' → Use: 'Led 5 cross-functional projects serving 50,000+ users'",
                "Instead of: 'Improved processes' → Use: 'Optimized workflow processes, reducing processing time by 35%'",
                "Instead of: 'Managed team' → Use: 'Managed team of 8 engineers, delivering 12 features in 6 months'"
            ] if rewritten_data.get("estimated_new_ats_score", ats_data.get("overall_score", 0) + 10) < 90 else []
        },
        "quality_report": {
            "overall_score": quality_data.get("overall_score", 0),
            "strengths": quality_data.get("strengths", []),
            "weaknesses": quality_data.get("weaknesses", []),
            "suggestions": quality_data.get("suggestions", [])
        },
        "ats_compliance": {
            "overall_score": ats_data.get("overall_score", 0),
            "passed_checks": [
                {
                    "item": check.get("item", ""),
                    "status": check.get("status", ""),
                    "details": check.get("details", "")
                }
                for check in ats_data.get("passed_checks", [])
            ],
            "failed_checks": [
                {
                    "item": check.get("item", ""),
                    "status": check.get("status", ""),
                    "details": check.get("details", "")
                }
                for check in ats_data.get("failed_checks", [])
            ],
            "critical_issues": ats_data.get("critical_issues", []),
            "recommendations": ats_data.get("recommendations", [])
        }
    }
    
    return response


@app.post("/recommend-careers/", response_model=CareerRecommendationResponse, tags=["Career Recommendations"])
async def recommend_careers(
    cv_data: Dict[str, Any],
    tier: str = "free",
    location: str = "Germany",
    limit: int = 10
):
    """
    Get career recommendations based on parsed CV data.
    
    **Tiers:**
    - **free**: BA-API (German Federal Employment Agency) - ~50,000 jobs in Germany
    - **premium**: BA-API + LinkedIn + Indeed - ~500,000 jobs worldwide
    
    **Parameters:**
    - cv_data: Parsed CV data (from /analyze-and-rewrite/ endpoint)
    - tier: "free" or "premium"
    - location: Location for job search (default: "Germany")
    - limit: Number of recommendations to return (default: 10)
    """
    
    if tier not in ["free", "premium"]:
        raise HTTPException(status_code=400, detail="Invalid tier. Must be 'free' or 'premium'")
    
    # For now, return mock data (will be implemented in next phases)
    # TODO: Implement actual job fetching and matching logic
    
    mock_jobs = [
        {
            "id": str(uuid.uuid4()),
            "title": "Data Scientist",
            "company": "Tech Company GmbH",
            "location": "Berlin, Germany",
            "job_type": "Full-time",
            "experience_level": "Mid-level",
            "description": "We are looking for a Data Scientist...",
            "required_skills": ["Python", "Machine Learning", "SQL"],
            "salary_min": 60000,
            "salary_max": 80000,
            "salary_currency": "EUR",
            "source": "BA-API" if tier == "free" else "LinkedIn",
            "posted_at": datetime.now().isoformat(),
            "url": "https://example.com/job/123"
        }
    ]
    
    mock_recommendations = [
        {
            "job": mock_jobs[0],
            "overall_match_score": 85,
            "skills_match_score": 90,
            "experience_match_score": 80,
            "education_match_score": 85,
            "language_match_score": 95,
            "matched_skills": ["Python", "Machine Learning"],
            "missing_skills": ["Deep Learning", "TensorFlow"],
            "improvement_suggestions": [
                {
                    "category": "skills",
                    "suggestion": "Learn Deep Learning frameworks like TensorFlow or PyTorch"
                },
                {
                    "category": "experience",
                    "suggestion": "Work on more ML projects to gain hands-on experience"
                }
            ],
            "estimated_preparation_time": "2-3 months"
        }
    ]
    
    return {
        "tier": tier,
        "location": location,
        "total_jobs_searched": len(mock_jobs),
        "recommendations": mock_recommendations[:limit],
        "message": f"Showing top {len(mock_recommendations[:limit])} recommendations from {tier} tier"
    }


# --- 7. Run the App ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)
