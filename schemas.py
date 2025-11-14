# schemas.py (v11.0 - Added Career Recommendation Models + Multi-Language Support)

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Core Data Structures ---

class Experience(BaseModel):
    position: Optional[str] = Field(description="The job title or position.")
    company: Optional[str] = Field(description="The name of the company.")
    duration: Optional[str] = Field(description="The duration of the employment, e.g., '2018 - 2022'")
    description: Optional[str] = Field(description="A brief description of responsibilities and achievements.")

class Education(BaseModel):
    degree: Optional[str] = Field(description="The degree or certification obtained.")
    institution: Optional[str] = Field(description="The name of the institution.")
    year: Optional[str] = Field(description="The year of graduation or completion.")

# --- NEW: Project, Language, Hobby Structures ---
class Project(BaseModel):
    title: Optional[str] = Field(description="The title or name of the project.")
    description: Optional[str] = Field(description="A brief description of the project.")
    technologies: Optional[str] = Field(description="Technologies or tools used in the project.")
    metrics: Optional[str] = Field(description="Quantifiable results or metrics (e.g., '90% accuracy', '1000+ users').")

class Language(BaseModel):
    language: Optional[str] = Field(description="The name of the language (e.g., 'English', 'German', 'Arabic').")
    proficiency: Optional[str] = Field(description="Proficiency level (e.g., 'Native', 'Fluent', 'Intermediate').")

# --- Parsed CV Structure (UPDATED) ---
class ParsedCV(BaseModel):
    name: Optional[str] = Field(description="Full name of the candidate.")
    email: Optional[str] = Field(description="Email address.")
    phone: Optional[str] = Field(description="Phone number.")
    address: Optional[str] = Field(description="Physical address or location.")
    summary: Optional[str] = Field(description="Professional summary or objective statement.")
    skills: Optional[List[str]] = Field(default=[], description="List of skills.")
    experience: Optional[List[Dict[str, Any]]] = Field(default=[], description="List of work experience entries.")
    education: Optional[List[Dict[str, Any]]] = Field(default=[], description="List of education entries.")
    projects: Optional[List[Dict[str, Any]]] = Field(default=[], description="List of projects.")
    languages: Optional[List[Dict[str, Any]]] = Field(default=[], description="List of languages with proficiency.")
    hobbies: Optional[List[str]] = Field(default=[], description="List of hobbies or interests.")
    social_links: Optional[Dict[str, str]] = Field(default=None, description="Social and professional links.")

# --- CV Text (for simple parsing) ---
class CVText(BaseModel):
    text: str = Field(description="The raw text content of the CV.")

# --- Quality Report ---
class QualityReport(BaseModel):
    overall_score: int = Field(description="Overall quality score (0-100).")
    strengths: List[str] = Field(description="List of strengths identified in the CV.")
    weaknesses: List[str] = Field(description="List of weaknesses or areas for improvement.")
    suggestions: List[str] = Field(description="Actionable suggestions to improve the CV.")

# --- ATS Compliance Report ---
class ATSCheckItem(BaseModel):
    item: str = Field(description="The name of the ATS check item.")
    status: str = Field(description="Status: 'pass' or 'fail'.")
    details: str = Field(description="Additional details about the check.")

class ATSComplianceReport(BaseModel):
    overall_score: int = Field(description="Overall ATS compliance score (0-100).")
    passed_checks: List[ATSCheckItem] = Field(description="List of passed ATS checks.")
    failed_checks: List[ATSCheckItem] = Field(description="List of failed ATS checks.")
    critical_issues: List[str] = Field(description="List of critical issues that must be fixed.")
    recommendations: List[str] = Field(description="List of actionable recommendations.")

# --- Rewritten CV Structures ---
class RewrittenExperience(BaseModel):
    position: str
    company: str
    duration: Optional[str] = Field(default="Not Specified", description="Duration of employment")
    original_description: str
    rewritten_description: str
    improvements: List[str] = Field(description="List of improvements made to this experience entry.")

class RewrittenCV(BaseModel):
    name: str
    email: str
    phone: str
    original_summary: str
    rewritten_summary: str
    original_skills: List[str]
    suggested_skills: List[str]
    combined_skills: List[str]
    rewritten_experience: List[RewrittenExperience]
    estimated_new_ats_score: int = Field(description="Estimated ATS score after applying improvements.")

# --- NEW: Improved CV Structure (Final Output) ---
class NewCV(BaseModel):
    name: str
    email: str
    phone: str
    address: Optional[str] = Field(default="", description="Physical address or location.")
    summary: str = Field(description="Improved professional summary.")
    skills: List[str] = Field(description="Combined original + suggested skills.")
    experience: List[RewrittenExperience] = Field(description="Improved experience entries.")
    education: Optional[List[Dict[str, Any]]] = Field(default=[], description="Education entries.")
    projects: Optional[List[Dict[str, Any]]] = Field(default=[], description="Projects.")
    languages: Optional[List[Dict[str, Any]]] = Field(default=[], description="Languages with proficiency.")
    hobbies: Optional[List[str]] = Field(default=[], description="Hobbies or interests.")
    social_links: Optional[Dict[str, str]] = Field(default=None, description="Social and professional links.")

# --- Improvements Summary ---
class ImprovementsSummary(BaseModel):
    ats_score_before: int = Field(description="Original ATS score (0-100).")
    ats_score_after: int = Field(description="Improved ATS score (0-100).")
    improvements_made: List[str] = Field(description="List of improvements applied to the CV.")
    translation_applied: bool = Field(description="Whether translation was applied.")
    input_language: str = Field(description="Detected language of the input CV.")
    output_language: str = Field(description="Language of the final CV.")

# --- Complete Analysis Response (UPDATED - Clean Output) ---
class CompleteAnalysisResponse(BaseModel):
    final_cv: NewCV = Field(description="The final improved CV (ready to use).")
    career_recommendation: Dict[str, Any] = Field(description="Career identification and recommendations.")
    improvements_summary: ImprovementsSummary = Field(description="Summary of improvements made.")
    improvement_notes: Dict[str, Any] = Field(description="Notes about what's needed to reach 90% ATS score.")
    quality_report: QualityReport = Field(description="Quality assessment of the original CV.")
    ats_compliance: ATSComplianceReport = Field(description="ATS compliance report of the original CV.")

# --- NEW: Career Recommendation System Models ---

class JobListing(BaseModel):
    id: str = Field(description="Unique job ID.")
    title: str = Field(description="Job title.")
    company: str = Field(description="Company name.")
    location: str = Field(description="Job location.")
    job_type: Optional[str] = Field(description="Job type (Full-time, Part-time, Contract, Remote).")
    experience_level: Optional[str] = Field(description="Experience level (Entry, Mid, Senior, Lead).")
    description: Optional[str] = Field(description="Job description.")
    required_skills: List[str] = Field(description="Required skills for the job.")
    salary_min: Optional[float] = Field(description="Minimum salary.")
    salary_max: Optional[float] = Field(description="Maximum salary.")
    salary_currency: Optional[str] = Field(default="EUR", description="Salary currency.")
    source: str = Field(description="Job source (BA-API, LinkedIn, Indeed).")
    posted_at: Optional[str] = Field(description="Job posting date (ISO format).")
    url: Optional[str] = Field(description="Job application URL.")

class ImprovementSuggestion(BaseModel):
    category: str = Field(description="Category of improvement (skills, experience, education, etc.).")
    suggestion: str = Field(description="Specific improvement suggestion.")

class CareerRecommendation(BaseModel):
    job: JobListing = Field(description="The recommended job listing.")
    overall_match_score: int = Field(description="Overall match score (0-100).")
    skills_match_score: Optional[int] = Field(description="Skills match score (0-100).")
    experience_match_score: Optional[int] = Field(description="Experience match score (0-100).")
    education_match_score: Optional[int] = Field(description="Education match score (0-100).")
    language_match_score: Optional[int] = Field(description="Language match score (0-100).")
    matched_skills: List[str] = Field(description="Skills that match the job requirements.")
    missing_skills: List[str] = Field(description="Skills that are required but missing.")
    improvement_suggestions: List[ImprovementSuggestion] = Field(description="Suggestions to improve match score.")
    estimated_preparation_time: Optional[str] = Field(description="Estimated time to prepare for this job (e.g., '2-3 months').")

class CareerRecommendationResponse(BaseModel):
    tier: str = Field(description="Subscription tier (free or premium).")
    location: str = Field(description="Job search location.")
    total_jobs_searched: int = Field(description="Total number of jobs searched.")
    recommendations: List[CareerRecommendation] = Field(description="List of career recommendations.")
    message: str = Field(description="Response message.")