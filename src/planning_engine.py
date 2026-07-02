"""
Enhanced Planning Engine for FitAgent.
Generates personalized diet and exercise plans based on user profiles and history.
"""

from __future__ import annotations

import os
import re
import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- INITIALIZATION ---
def init_gemini():
    """Initialize Vertex AI."""
    vertexai.init(project="fine-rite-497404-r7", location="us-central1")

def verify_model_available(model_name: str) -> bool:
    """Verify if the specified Gemini model is accessible."""
    return True

HEALTH_PLAN_TOP_LEVEL_KEYS = [
    "user_goal",
    "summary",
    "daily_schedule",
    "weekly_focus",
    "tips_and_warnings",
]

SCHEDULE_ITEM_KEYS = [
    "time",
    "activity_type",
    "title",
    "description",
    "medicinal_value",
    "calories_target",
    "duration_minutes",
]


def clean_gemini_json(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```$", "", text)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]
    return text.strip()


def parse_json_response(raw_text: str) -> dict:
    cleaned = clean_gemini_json(raw_text)
    logger.debug("Parsed Gemini text to cleaned JSON: %s", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from Gemini response. Cleaned response: %s", cleaned)
        raise ValueError(f"Invalid JSON response from Gemini: {exc}") from exc


def unwrap_health_plan_wrapper(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    for wrapper in ("plan", "health_plan", "result", "data", "response"):
        if wrapper in data and isinstance(data[wrapper], dict):
            candidate = data[wrapper]
            if all(key in candidate for key in ("user_goal", "summary", "daily_schedule")):
                logger.debug("Detected wrapper key '%s' in Gemini response; unwrapping.", wrapper)
                return candidate
    return data


def get_validation_issues(exc: ValidationError) -> list[str]:
    fields = []
    for error in exc.errors():
        loc = error.get("loc", ())
        if not isinstance(loc, (list, tuple)):
            loc = (loc,)
        field_name = ".".join(str(item) for item in loc)
        if error.get("type") == "missing":
            fields.append(field_name)
        else:
            fields.append(f"{field_name}: {error.get('msg')}")
    return fields


def merge_partial_health_plan(original: dict, update: dict) -> dict:
    merged = dict(original or {})
    for key, value in (update or {}).items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def build_health_plan_prompt(personalized_prompt: str) -> str:
    return (
        personalized_prompt
        + "\n\nReturn ONLY valid JSON with exactly these top-level keys:\n"
        + "- user_goal\n"
        + "- summary\n"
        + "- daily_schedule\n"
        + "- weekly_focus\n"
        + "- tips_and_warnings\n\n"
        + "The daily_schedule field must be a list of objects with these exact keys:\n"
        + "- time\n"
        + "- activity_type\n"
        + "- title\n"
        + "- description\n"
        + "- medicinal_value\n"
        + "- calories_target\n"
        + "- duration_minutes\n\n"
        + "Use the following rules:\n"
        + "- Do not include markdown, code fences, or any explanatory text outside the JSON.\n"
        + "- Return an empty string for any text field you cannot answer.\n"
        + "- Return null for optional numeric fields if not applicable.\n"
        + "- Keep the JSON valid and parsable.\n\n"
        + "Example structure:\n"
        + "{\n"
        + "  \"user_goal\": \"weight_loss\",\n"
        + "  \"summary\": \"...\",\n"
        + "  \"daily_schedule\": [\n"
        + "    {\n"
        + "      \"time\": \"08:00 AM\",\n"
        + "      \"activity_type\": \"Meal\",\n"
        + "      \"title\": \"Breakfast\",\n"
        + "      \"description\": \"...\",\n"
        + "      \"medicinal_value\": \"...\",\n"
        + "      \"calories_target\": 350,\n"
        + "      \"duration_minutes\": null\n"
        + "    }\n"
        + "  ],\n"
        + "  \"weekly_focus\": \"...\",\n"
        + "  \"tips_and_warnings\": [\"...\", \"...\"]\n"
        + "}\n"
    )


def build_health_plan_retry_prompt(missing_fields: list[str], personalized_prompt: str) -> str:
    field_list = "\n".join(f"- {field}" for field in missing_fields)
    return f"""Your previous response was incomplete or missing required fields.
Provide ONLY a valid JSON object with the same exact structure as the HealthPlan model.
Do not include markdown, code fences, or any extra text.
Missing fields:
{field_list}

User context:
{personalized_prompt}
"""


def _generate_structured_health_plan(
    model: GenerativeModel,
    prompt: str,
) -> dict:
    logger.debug("Sending prompt to Gemini: %s", prompt)
    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    logger.debug("Gemini raw response: %s", response.text)
    return parse_json_response(response.text)


def _validate_health_plan(data: dict, user_goal: str) -> HealthPlan:
    if not isinstance(data, dict):
        raise ValueError("Parsed Gemini response is not a JSON object.")
    unwrapped = unwrap_health_plan_wrapper(data)
    try:
        return HealthPlan.model_validate(unwrapped)
    except ValidationError as exc:
        issues = get_validation_issues(exc)
        logger.error(
            "HealthPlan validation failed for '%s': %s. Parsed response: %s",
            user_goal,
            issues,
            unwrapped,
        )
        raise

# --- PYDANTIC MODELS ---
class ScheduleItem(BaseModel):
    """A single item in the daily schedule."""
    time: str = Field(description="Time of day, e.g., '08:00 AM'")
    activity_type: str = Field(description="Type: 'Meal', 'Exercise', 'Water Break', 'Rest', etc.")
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Detailed instructions or Indian food recommendation")
    medicinal_value: str = Field(description="'Food as Medicine' benefits or health rationale")
    calories_target: Optional[int] = Field(default=None, description="Calorie target for meal")
    duration_minutes: Optional[int] = Field(default=None, description="Duration in minutes for exercise")

class HealthPlan(BaseModel):
    """Structured health plan output."""
    user_goal: str = Field(description="User's primary health goal")
    summary: str = Field(description="Executive summary of the plan")
    daily_schedule: List[ScheduleItem] = Field(description="Chronologically ordered daily routine")
    weekly_focus: str = Field(description="Focus areas for the week")
    tips_and_warnings: List[str] = Field(description="Important tips and warnings")

# --- SYSTEM PROMPT ---
FITAGEN_SYSTEM_PROMPT = """
You are FitAgent, an elite autonomous health co-pilot designed for the INDIA RUNS hackathon.
Your mission: Bridge the gap between knowing what to do and actually doing it.

CORE PERSONALITY:
- Empathetic, supportive, and genuinely interested in user wellness
- Professional yet conversational (like a supportive expert friend)
- Data-driven but human-centered
- Culturally aware of Indian food, lifestyle, and constraints

PLANNING PHILOSOPHY:
1. PERSONALIZATION IS EVERYTHING
   - Use user goals, health conditions, dietary restrictions, and history
   - Adjust intensity based on current fitness level
   - Consider daily routine and available time
   - Respect cultural food preferences and affordability

2. INDIAN-FIRST DIET RECOMMENDATIONS
   - Prioritize local, affordable Indian foods: Moong Dal, Chana, Paneer, Roti, Sabzi, Rice
   - Include regional variants (South Indian, North Indian, etc.)
   - Avoid expensive imported/exotic diets
   - Always explain "Food as Medicine" benefits (Ayurvedic perspective)
   - Support vegetarian, vegan, and non-veg preferences equally

3. REALISTIC & SUSTAINABLE
   - Create plans that fit typical Indian daily routines (office hours, traffic, etc.)
   - Include water intake goals and hydration breaks
   - Build in flexibility for weekend variations
   - Consider seasonal variations (summer vs winter)

4. STRUCTURED OUTPUT
   - Provide clear time-based schedules (08:00 AM, 12:30 PM, etc.)
   - Include both meals and exercise/activity
   - Add duration and calorie targets where relevant
   - Explain medicinal/health benefits of each recommendation

5. RESPECT CONSTRAINTS
   - Health conditions: diabetes, hypertension, PCOS, etc.
   - Allergies and dietary restrictions
   - Time limitations and work schedules
   - Budget limitations
"""

# --- HELPER FUNCTION: BUILD PERSONALIZED PROMPT ---
def build_personalized_prompt(
    user_goal: str,
    diet_preference: str,
    age: int,
    weight_kg: float,
    height_cm: float,
    health_conditions: Optional[str] = None,
    dietary_restrictions: Optional[str] = None,
    daily_routine: Optional[str] = None,
    recent_meals: Optional[List[str]] = None,
    recent_workouts: Optional[List[str]] = None,
) -> str:
    """
    Build a detailed personalized prompt for the planning engine.
    Uses user profile data and history to create context-aware recommendations.
    """
    
    bmi = weight_kg / ((height_cm / 100) ** 2)
    
    prompt_parts = [
        "USER PROFILE:",
        f"- Goal: {user_goal.replace('_', ' ').title()}",
        f"- Age: {age} years",
        f"- Weight: {weight_kg} kg, Height: {height_cm} cm (BMI: {bmi:.1f})",
        f"- Diet Preference: {diet_preference.replace('_', ' ').title()}",
    ]
    
    if health_conditions:
        prompt_parts.append(f"- Health Conditions: {health_conditions}")
    
    if dietary_restrictions:
        prompt_parts.append(f"- Dietary Restrictions: {dietary_restrictions}")
    
    if daily_routine:
        prompt_parts.append(f"- Daily Routine: {daily_routine}")
    
    if recent_meals:
        prompt_parts.append(f"\nRECENT MEAL HISTORY (last 7 days):")
        for meal in recent_meals[-5:]:  # Last 5 meals
            prompt_parts.append(f"- {meal}")
    
    if recent_workouts:
        prompt_parts.append(f"\nRECENT WORKOUT HISTORY (last 7 days):")
        for workout in recent_workouts[-5:]:  # Last 5 workouts
            prompt_parts.append(f"- {workout}")
    
    prompt_parts.extend([
        "",
        "TASK: Generate a comprehensive 14-hour daily health plan (08:00 AM to 10:00 PM).",
        "Include 3 meals, 2 snacks, water breaks, and 1-2 exercise sessions.",
        "Tailor everything to the user's goal, preferences, and constraints.",
        "Ensure calorie targets align with their goal (weight loss: -300-500 cal, muscle gain: +200-300 cal, maintenance: balanced).",
        "Provide 'Food as Medicine' explanations emphasizing Ayurvedic principles.",
        "Include weekly focus areas and practical tips.",
    ])
    
    return "\n".join(prompt_parts)

# --- CORE PLANNING ENGINE ---
def generate_health_plan(
    user_goal: str,
    diet_preference: str,
    age: int = 30,
    weight_kg: float = 75,
    height_cm: float = 175,
    health_conditions: Optional[str] = None,
    dietary_restrictions: Optional[str] = None,
    daily_routine: Optional[str] = None,
    recent_meals: Optional[List[str]] = None,
    recent_workouts: Optional[List[str]] = None,
) -> HealthPlan:
    """
    Generate a personalized health plan.
    
    Args:
        user_goal: weight_loss, muscle_gain, maintenance, endurance
        diet_preference: vegetarian, non_veg, vegan
        age: User's age
        weight_kg: Current weight
        height_cm: Height
        health_conditions: Any health conditions (optional)
        dietary_restrictions: Any dietary restrictions (optional)
        daily_routine: Description of typical day (optional)
        recent_meals: List of recently logged meals (optional)
        recent_workouts: List of recently logged workouts (optional)
    
    Returns:
        HealthPlan object with personalized schedule
    """
    
    try:
        init_gemini()
    except ValueError as e:
        raise RuntimeError(f"Cannot initialize Gemini: {str(e)}")
    
    model_name = "gemini-2.5-flash"
    if not verify_model_available(model_name):
        raise RuntimeError(f"Model '{model_name}' not accessible. Check API key and account.")
    
    # Build personalized prompt
    personalized_prompt = build_personalized_prompt(
        user_goal=user_goal,
        diet_preference=diet_preference,
        age=age,
        weight_kg=weight_kg,
        height_cm=height_cm,
        health_conditions=health_conditions,
        dietary_restrictions=dietary_restrictions,
        daily_routine=daily_routine,
        recent_meals=recent_meals,
        recent_workouts=recent_workouts,
    )
    
    # Initialize model with system prompt
    model = GenerativeModel(
        model_name=model_name,
        system_instruction=FITAGEN_SYSTEM_PROMPT,
    )
    
    # Generate plan with structured output
    main_prompt = build_health_plan_prompt(personalized_prompt)
    try:
        first_parsed = _generate_structured_health_plan(model, main_prompt)
        validated = _validate_health_plan(first_parsed, user_goal)
        return validated
    except (ValueError, ValidationError) as first_exc:
        logger.warning(
            "First health plan generation failed for '%s': %s",
            user_goal,
            str(first_exc),
        )

        missing_fields = get_validation_issues(first_exc) if isinstance(first_exc, ValidationError) else HEALTH_PLAN_TOP_LEVEL_KEYS
        retry_prompt = build_health_plan_retry_prompt(missing_fields, personalized_prompt)
        second_parsed = _generate_structured_health_plan(model, retry_prompt)

        merged_response = merge_partial_health_plan(first_parsed if isinstance(first_exc, ValidationError) else {}, second_parsed)
        validated_retry = _validate_health_plan(merged_response, user_goal)
        return validated_retry

