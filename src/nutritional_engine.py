"""
Nutritional Analysis Engine for FitAgent.
Provides food analysis, macro tracking, and "Food as Medicine" insights.
Specialized for Indian foods and Ayurvedic principles.
"""

import os
import json
import re
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict

# --- PYDANTIC MODELS FOR NUTRITIONAL DATA ---
class NutritionalProfile(BaseModel):
    """Detailed nutritional information for a food item."""
    calories: float = Field(description="Calories per serving")
    protein_g: float = Field(description="Protein in grams")
    carbs_g: float = Field(description="Carbohydrates in grams")
    fat_g: float = Field(description="Fat in grams")
    fiber_g: Optional[float] = Field(default=None, description="Dietary fiber in grams")
    sugar_g: Optional[float] = Field(default=None, description="Sugar in grams")
    sodium_mg: Optional[float] = Field(default=None, description="Sodium in mg")

class AyurvedicBenefit(BaseModel):
    """Ayurvedic health benefits of a food."""
    benefit: str = Field(description="The health benefit")
    dosha_impact: str = Field(description="Impact on doshas (Vata, Pitta, Kapha)")
    supporting_principle: str = Field(description="Ayurvedic principle behind this benefit")

class FoodAnalysis(BaseModel):
    """Comprehensive food analysis output."""
    food_name: str = Field(description="Name of the food item")
    serving_size: str = Field(description="Standard serving size, e.g., 1 bowl, 100g")
    nutrition: NutritionalProfile = Field(description="Nutritional information")
    macronutrient_ratio: str = Field(description="Ratio like '25% protein, 50% carbs, 25% fat'")
    
    ayurvedic_benefits: List[AyurvedicBenefit] = Field(
        description="List of Ayurvedic health benefits"
    )
    
    best_time_to_eat: str = Field(description="Recommended time of day")
    pairs_well_with: List[str] = Field(description="Complementary foods")
    avoid_with: List[str] = Field(description="Foods to avoid combining with")
    
    digestibility: str = Field(description="How easy/difficult to digest")
    ideal_for_goal: List[str] = Field(
        description="Health goals this food is good for: weight_loss, muscle_gain, energy, etc."
    )
    
    precautions: Optional[str] = Field(default=None, description="Any health precautions")
    interesting_fact: str = Field(description="A cultural or nutritional fact about this food")

class DailyNutritionSummary(BaseModel):
    """Summary of daily nutritional intake."""
    date: str
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    
    protein_ratio: float = Field(description="Percentage of calories from protein")
    carbs_ratio: float = Field(description="Percentage of calories from carbs")
    fat_ratio: float = Field(description="Percentage of calories from fat")
    
    meal_breakdown: Dict[str, float] = Field(description="Calories by meal type")
    goals_met: List[str] = Field(description="Which nutritional goals were met")
    recommendations: List[str] = Field(description="Recommendations for next day")

logger = logging.getLogger(__name__)

FOOD_ANALYSIS_TOP_LEVEL_KEYS = [
    "food_name",
    "serving_size",
    "nutrition",
    "macronutrient_ratio",
    "ayurvedic_benefits",
    "best_time_to_eat",
    "pairs_well_with",
    "avoid_with",
    "digestibility",
    "ideal_for_goal",
    "precautions",
    "interesting_fact",
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
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from Gemini response. Cleaned response: %s", cleaned)
        raise ValueError(f"Invalid JSON response from Gemini: {exc}") from exc


def unwrap_analysis_wrapper(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    for wrapper in ("analysis", "data", "result", "response"):
        if wrapper in data and isinstance(data[wrapper], dict):
            candidate = data[wrapper]
            if all(key in candidate for key in ("food_name", "serving_size", "nutrition")):
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


def build_structured_food_analysis_prompt(food_description: str) -> str:
    return f"""You are FitAgent's expert Nutritionist and Ayurvedic practitioner.
Return ONLY valid JSON. Do not include markdown, code fences, explanations, or any text outside the JSON.
The JSON object must have exactly these top-level keys:
- food_name
- serving_size
- nutrition
- macronutrient_ratio
- ayurvedic_benefits
- best_time_to_eat
- pairs_well_with
- avoid_with
- digestibility
- ideal_for_goal
- precautions
- interesting_fact

The nutrition object must contain:
- calories
- protein_g
- carbs_g
- fat_g
- fiber_g
- sodium_mg

The ayurvedic_benefits list must contain objects with:
- benefit
- dosha_impact
- supporting_principle

If a field is not applicable, return an empty string, empty list, or null for precautions.
Food: {food_description}
"""


def build_retry_prompt(missing_fields: list[str], food_description: str) -> str:
    field_list = "\n".join(f"- {field}" for field in missing_fields)
    return f"""Your previous response was incomplete.
Provide only a valid JSON object containing the missing fields below, using the same structure as the FoodAnalysis model.
Do not include markdown, code fences, or any extra text.
Missing fields:
{field_list}
Food: {food_description}
"""


def merge_partial_food_analysis(original: dict, update: dict) -> dict:
    merged = dict(original or {})
    for key, value in (update or {}).items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _validate_food_analysis(data: dict, food_description: str) -> FoodAnalysis:
    if not isinstance(data, dict):
        raise ValueError("Parsed Gemini response is not a JSON object.")

    unwrapped = unwrap_analysis_wrapper(data)
    try:
        return FoodAnalysis.model_validate(unwrapped)
    except ValidationError as exc:
        issues = get_validation_issues(exc)
        logger.error(
            "FoodAnalysis validation failed for '%s': %s. Parsed response: %s",
            food_description,
            issues,
            unwrapped,
        )
        raise


def _generate_structured_food_analysis(
    model: GenerativeModel,
    prompt: str,
) -> dict:
    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    return parse_json_response(response.text)


def analyze_food_item_structured(food_description: str) -> FoodAnalysis:
    """
    Detailed structured analysis of a food item.
    Returns comprehensive FoodAnalysis object with macros, Ayurvedic benefits, etc.
    """
    try:
        init_gemini()
    except ValueError as e:
        raise RuntimeError(f"Cannot initialize Gemini: {str(e)}")

    model = GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=(
            "You are FitAgent's expert Nutritionist and Ayurvedic practitioner. "
            "Provide detailed, structured analysis of foods with emphasis on: "
            "1. Accurate nutritional information (approximate if not exact) "
            "2. Ayurvedic principles and benefits (dosha balance, digestibility) "
            "3. 'Food as Medicine' perspective "
            "4. Practical food pairing recommendations "
            "5. Best suited for which health goals "
            "\n"
            "For Indian foods specifically, emphasize cultural context and Ayurvedic wisdom."
        )
    )

    prompt = build_structured_food_analysis_prompt(food_description)

    first_parsed = {}
    first_exc_captured = None
    try:
        first_parsed = _generate_structured_food_analysis(model, prompt)
        validated = _validate_food_analysis(first_parsed, food_description)
        return validated
    except (ValueError, ValidationError) as e:
        first_exc_captured = e
        logger.warning(
            "First structured food analysis attempt failed for '%s': %s",
            food_description,
            str(e),
        )

    try:
        if isinstance(first_exc_captured, ValidationError):
            missing_fields = get_validation_issues(first_exc_captured)
        else:
            missing_fields = [
                "food_name",
                "serving_size",
                "nutrition",
                "macronutrient_ratio",
                "ayurvedic_benefits",
                "best_time_to_eat",
                "pairs_well_with",
                "avoid_with",
                "digestibility",
                "ideal_for_goal",
                "precautions",
                "interesting_fact",
            ]

        retry_prompt = build_retry_prompt(missing_fields, food_description)
        second_parsed = _generate_structured_food_analysis(model, retry_prompt)
        merged_response = merge_partial_food_analysis(first_parsed if isinstance(first_exc_captured, ValidationError) else {}, second_parsed)
        validated = _validate_food_analysis(merged_response, food_description)
        return validated
    except (ValueError, ValidationError) as second_exc:
        logger.error(
            "Second structured food analysis attempt failed for '%s': %s",
            food_description,
            str(second_exc),
        )
        raise RuntimeError(
            "Unable to generate a valid structured food analysis. "
            "Please try again with a simpler food description."
        ) from second_exc

# --- INDIAN FOOD DATABASE ---
INDIAN_FOOD_DATABASE = {
    "moong_dal": {
        "name": "Moong Dal (cooked)",
        "calories": 105,
        "protein_g": 3.1,
        "carbs_g": 19.3,
        "fat_g": 0.4,
        "fiber_g": 2.0,
        "serving_size": "100g cooked",
    },
    "paneer": {
        "name": "Paneer (fresh)",
        "calories": 265,
        "protein_g": 25.2,
        "carbs_g": 3.6,
        "fat_g": 17.3,
        "fiber_g": 0,
        "serving_size": "100g",
    },
    "chana_dal": {
        "name": "Chana Dal (cooked)",
        "calories": 120,
        "protein_g": 8.5,
        "carbs_g": 20.8,
        "fat_g": 0.5,
        "fiber_g": 2.1,
        "serving_size": "100g cooked",
    },
    "roti": {
        "name": "Roti (wheat)",
        "calories": 150,
        "protein_g": 4.0,
        "carbs_g": 29.4,
        "fat_g": 0.9,
        "fiber_g": 1.7,
        "serving_size": "1 medium roti (50g)",
    },
    "basmati_rice": {
        "name": "Basmati Rice (cooked)",
        "calories": 130,
        "protein_g": 2.7,
        "carbs_g": 28.0,
        "fat_g": 0.3,
        "fiber_g": 0.4,
        "serving_size": "100g cooked",
    },
    "ghee": {
        "name": "Ghee (clarified butter)",
        "calories": 900,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 99.5,
        "fiber_g": 0,
        "serving_size": "1 tbsp (15g)",
    },
    "coconut_oil": {
        "name": "Coconut Oil",
        "calories": 892,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 99.1,
        "fiber_g": 0,
        "serving_size": "1 tbsp (15g)",
    },
    "turmeric": {
        "name": "Turmeric powder",
        "calories": 312,
        "protein_g": 9.7,
        "carbs_g": 67.1,
        "fat_g": 3.1,
        "fiber_g": 21.1,
        "serving_size": "1 tsp (3g)",
    },
    "curd": {
        "name": "Yogurt (plain, full fat)",
        "calories": 61,
        "protein_g": 3.5,
        "carbs_g": 4.7,
        "fat_g": 3.3,
        "fiber_g": 0,
        "serving_size": "100g",
    },
    "spinach": {
        "name": "Palak (Spinach) raw",
        "calories": 23,
        "protein_g": 2.7,
        "carbs_g": 3.6,
        "fat_g": 0.4,
        "fiber_g": 2.2,
        "serving_size": "100g",
    },
    "cauliflower": {
        "name": "Cauliflower raw",
        "calories": 25,
        "protein_g": 1.9,
        "carbs_g": 4.9,
        "fat_g": 0.3,
        "fiber_g": 2.4,
        "serving_size": "100g",
    },
    "tomato": {
        "name": "Tomato raw",
        "calories": 18,
        "protein_g": 0.9,
        "carbs_g": 3.9,
        "fat_g": 0.2,
        "fiber_g": 1.2,
        "serving_size": "100g",
    },
    "onion": {
        "name": "Onion raw",
        "calories": 40,
        "protein_g": 1.1,
        "carbs_g": 9.3,
        "fat_g": 0.1,
        "fiber_g": 1.7,
        "serving_size": "100g",
    },
    "egg": {
        "name": "Egg (full)",
        "calories": 155,
        "protein_g": 13.0,
        "carbs_g": 1.1,
        "fat_g": 11.0,
        "fiber_g": 0,
        "serving_size": "1 large egg (50g)",
    },
    "chicken_breast": {
        "name": "Chicken breast (cooked, skinless)",
        "calories": 165,
        "protein_g": 31.0,
        "carbs_g": 0,
        "fat_g": 3.6,
        "fiber_g": 0,
        "serving_size": "100g",
    },
}

# --- HELPER FUNCTIONS ---
def init_gemini():
    """Initialize Vertex AI."""
    vertexai.init(project="fine-rite-497404-r7", location="us-central1")

def get_food_from_database(food_key: str) -> Optional[Dict]:
    """Get food information from the database."""
    return INDIAN_FOOD_DATABASE.get(food_key.lower())

def calculate_macro_ratios(protein_g: float, carbs_g: float, fat_g: float) -> Dict[str, float]:
    """Calculate macronutrient ratios."""
    total_cals = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
    
    if total_cals == 0:
        return {"protein": 0, "carbs": 0, "fat": 0}
    
    return {
        "protein": round((protein_g * 4) / total_cals * 100, 1),
        "carbs": round((carbs_g * 4) / total_cals * 100, 1),
        "fat": round((fat_g * 9) / total_cals * 100, 1),
    }

def analyze_food_item(food_description: str) -> str:
    """
    Simple analysis of a food item - returns formatted text.
    Uses AI for foods not in database.
    """
    try:
        init_gemini()
    except ValueError as e:
        raise RuntimeError(f"Cannot initialize Gemini: {str(e)}")
    
    model = GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=(
            "You are FitAgent's Nutritional Expert specializing in Indian foods. "
            "When asked about a food or meal, provide: "
            "1. Approximate macros (protein, carbs, fat, calories) "
            "2. Ayurvedic benefits and 'Food as Medicine' perspective "
            "3. Best time to eat and food combinations "
            "4. Who should/shouldn't eat it "
            "Keep responses concise (2-3 paragraphs) and practical."
        )
    )
    
    prompt = f"Analyze this Indian food or meal: {food_description}"
    
    response = model.generate_content(
        prompt,
        generation_config=GenerationConfig(temperature=0.5),
    )
    
    return response.text

def calculate_daily_nutrition_summary(
    meals: List[Dict],  # List of {name, calories, protein_g, carbs_g, fat_g, fiber_g}
    date: str,
    target_calories: Optional[float] = None,
    target_protein_g: Optional[float] = None,
) -> DailyNutritionSummary:
    """
    Calculate daily nutrition summary from meal list.
    Optionally compares against targets.
    """
    total_calories = sum(m.get("calories", 0) for m in meals)
    total_protein_g = sum(m.get("protein_g", 0) for m in meals)
    total_carbs_g = sum(m.get("carbs_g", 0) for m in meals)
    total_fat_g = sum(m.get("fat_g", 0) for m in meals)
    total_fiber_g = sum(m.get("fiber_g", 0) for m in meals)
    
    macros = calculate_macro_ratios(total_protein_g, total_carbs_g, total_fat_g)
    
    # Determine goals met
    goals_met = []
    recommendations = []
    
    if target_calories:
        if total_calories >= target_calories * 0.95:
            goals_met.append("Calorie target met")
        else:
            recommendations.append(f"Add {target_calories - total_calories:.0f} more calories")
    
    if target_protein_g:
        if total_protein_g >= target_protein_g:
            goals_met.append("Protein target met")
        else:
            recommendations.append(f"Add {target_protein_g - total_protein_g:.0f}g more protein")
    
    if total_fiber_g < 25:
        recommendations.append(f"Increase fiber intake (current: {total_fiber_g:.1f}g)")
    
    return DailyNutritionSummary(
        date=date,
        total_calories=total_calories,
        total_protein_g=total_protein_g,
        total_carbs_g=total_carbs_g,
        total_fat_g=total_fat_g,
        total_fiber_g=total_fiber_g,
        protein_ratio=macros["protein"],
        carbs_ratio=macros["carbs"],
        fat_ratio=macros["fat"],
        meal_breakdown={},  # Can be populated with meal-type breakdown
        goals_met=goals_met if goals_met else ["Keep monitoring nutrition"],
        recommendations=recommendations if recommendations else ["Well-balanced diet! Keep it up!"],
    )
