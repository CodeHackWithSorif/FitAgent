"""
Dashboard Engine for FitAgent - Provides health metrics calculations and insights.
Generates visualizations for weight trends, calorie tracking, macro analysis, and goal progress.
"""

from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
import statistics


# --- DASHBOARD DATA MODELS ---

class DailyMetricsSummary(BaseModel):
    """Summary of daily health metrics."""
    date: str
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    water_liters: float = 0.0
    steps: int = 0
    sleep_hours: Optional[float] = None
    mood: Optional[str] = None
    energy_level: Optional[str] = None
    calories: float = 0.0


class ProgressMetrics(BaseModel):
    """Overall progress tracking metrics."""
    days_tracked: int
    weight_change_kg: Optional[float] = None
    bmi_change: Optional[float] = None
    average_calories: float = 0.0
    average_water: float = 0.0
    average_steps: int = 0
    average_sleep_hours: Optional[float] = None
    mood_distribution: Dict[str, int] = {}
    goal_progress_percent: float = 0.0
    streak_days: int = 0


class GoalProgress(BaseModel):
    """Individual goal progress tracking."""
    goal_name: str
    current_value: float
    target_value: float
    unit: str
    progress_percent: float
    days_remaining: int = 0
    recommendation: str = ""


# --- CALCULATION FUNCTIONS ---

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI from weight and height."""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def calculate_bmi_category(bmi: float) -> str:
    """Get BMI category."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"


def calculate_caloric_burn_from_steps(steps: int, weight_kg: float) -> float:
    """Estimate calories burned from steps (average 0.04 cal per step for 70kg person)."""
    return round(steps * 0.04 * (weight_kg / 70), 1)


def calculate_daily_goal_progress(
    current_value: float,
    target_value: float,
) -> float:
    """Calculate percentage progress toward a goal."""
    if target_value == 0:
        return 0.0
    progress = (current_value / target_value) * 100
    return min(round(progress, 1), 100.0)  # Cap at 100%


def build_weight_trend_data(
    health_metrics: List[Dict],
    user_goal: Optional[str] = None,
) -> Dict:
    """Build weight trend data for visualization."""
    if not health_metrics:
        return {"dates": [], "weights": [], "bmi": [], "trend": "N/A"}
    
    # Sort by date ascending
    sorted_metrics = sorted(health_metrics, key=lambda x: x.get("date", datetime.utcnow()))
    
    dates = []
    weights = []
    bmi_values = []
    
    for metric in sorted_metrics:
        if metric.get("weight_kg"):
            date_str = metric["date"].strftime("%m-%d") if isinstance(metric["date"], datetime) else str(metric["date"])
            dates.append(date_str)
            weights.append(metric["weight_kg"])
            if metric.get("bmi"):
                bmi_values.append(metric["bmi"])
    
    # Calculate trend
    if len(weights) >= 2:
        weight_change = weights[-1] - weights[0]
        if user_goal == "weight_loss":
            trend = "On Track" if weight_change <= 0 else "Needs Attention"
        elif user_goal == "muscle_gain":
            trend = "On Track" if weight_change >= 0 else "Needs Attention"
        else:  # maintenance
            trend = "Stable" if abs(weight_change) < 2 else "Fluctuating"
    else:
        trend = "Insufficient Data"
    
    return {
        "dates": dates,
        "weights": weights,
        "bmi": bmi_values,
        "trend": trend,
        "total_change_kg": round(weights[-1] - weights[0], 1) if weights else 0,
    }


def build_calories_trend_data(
    daily_calories: List[Dict],
    target_calories: int = 2000,
) -> Dict:
    """Build calorie trend data for visualization."""
    if not daily_calories:
        return {"dates": [], "calories": [], "target": [], "status": "N/A"}
    
    # Sort by date ascending
    sorted_data = sorted(daily_calories, key=lambda x: x.get("date", datetime.utcnow()))
    
    dates = []
    calories = []
    
    for item in sorted_data:
        if item.get("calories") is not None:
            date_str = item["date"].strftime("%m-%d") if isinstance(item["date"], datetime) else str(item["date"])
            dates.append(date_str)
            calories.append(item["calories"])
    
    # Calculate average
    avg_calories = round(statistics.mean(calories)) if calories else 0
    
    # Determine status
    if avg_calories < target_calories * 0.9:
        status = "Below Target"
    elif avg_calories > target_calories * 1.1:
        status = "Above Target"
    else:
        status = "On Target"
    
    return {
        "dates": dates,
        "calories": calories,
        "target": [target_calories] * len(dates),
        "average": avg_calories,
        "status": status,
        "target_value": target_calories,
    }


def build_macro_trend_data(
    daily_macros: List[Dict],
) -> Dict:
    """Build macro trend data for visualization."""
    if not daily_macros:
        return {"dates": [], "protein": [], "carbs": [], "fat": []}
    
    # Sort by date ascending
    sorted_data = sorted(daily_macros, key=lambda x: x.get("date", datetime.utcnow()))
    
    dates = []
    protein_values = []
    carbs_values = []
    fat_values = []
    
    for item in sorted_data:
        date_str = item["date"].strftime("%m-%d") if isinstance(item["date"], datetime) else str(item["date"])
        dates.append(date_str)
        protein_values.append(item.get("protein_g", 0))
        carbs_values.append(item.get("carbs_g", 0))
        fat_values.append(item.get("fat_g", 0))
    
    return {
        "dates": dates,
        "protein": protein_values,
        "carbs": carbs_values,
        "fat": fat_values,
        "avg_protein": round(statistics.mean(protein_values)) if protein_values else 0,
        "avg_carbs": round(statistics.mean(carbs_values)) if carbs_values else 0,
        "avg_fat": round(statistics.mean(fat_values)) if fat_values else 0,
    }


def calculate_progress_metrics(
    health_metrics: List[Dict],
    user_goal: str,
    target_weight: Optional[float] = None,
    target_calories: int = 2000,
    target_steps: int = 10000,
    target_water: float = 2.5,
) -> ProgressMetrics:
    """Calculate overall progress metrics for user."""
    if not health_metrics:
        return ProgressMetrics(days_tracked=0)
    
    # Sort by date descending
    sorted_metrics = sorted(health_metrics, key=lambda x: x.get("date", datetime.utcnow()), reverse=True)
    
    days_tracked = len(sorted_metrics)
    
    # Weight change
    first_weight = sorted_metrics[-1].get("weight_kg") if sorted_metrics else None
    last_weight = sorted_metrics[0].get("weight_kg") if sorted_metrics else None
    weight_change_kg = None
    bmi_change = None
    
    if first_weight and last_weight:
        weight_change_kg = round(last_weight - first_weight, 1)
        first_bmi = sorted_metrics[-1].get("bmi")
        last_bmi = sorted_metrics[0].get("bmi")
        if first_bmi and last_bmi:
            bmi_change = round(last_bmi - first_bmi, 1)
    
    # Averages
    weights_with_data = [m.get("weight_kg") for m in sorted_metrics if m.get("weight_kg")]
    water_values = [m.get("water_liters", 0) for m in sorted_metrics]
    steps_values = [m.get("steps", 0) for m in sorted_metrics]
    sleep_values = [m.get("sleep_hours") for m in sorted_metrics if m.get("sleep_hours")]
    
    average_water = round(statistics.mean(water_values), 2) if water_values else 0.0
    average_steps = round(statistics.mean(steps_values)) if steps_values else 0
    average_sleep = round(statistics.mean(sleep_values), 1) if sleep_values else None
    
    # Mood distribution
    mood_dist = {}
    for metric in sorted_metrics:
        mood = metric.get("mood")
        if mood:
            mood_dist[mood] = mood_dist.get(mood, 0) + 1
    
    # Goal progress
    goal_progress = 0.0
    if target_weight and last_weight:
        if user_goal == "weight_loss":
            goal_progress = calculate_daily_goal_progress(
                first_weight - last_weight if first_weight else 0,
                first_weight - target_weight if first_weight else 1
            )
        elif user_goal == "muscle_gain":
            goal_progress = calculate_daily_goal_progress(
                last_weight - first_weight if first_weight else 0,
                target_weight - first_weight if first_weight else 1
            )
    
    return ProgressMetrics(
        days_tracked=days_tracked,
        weight_change_kg=weight_change_kg,
        bmi_change=bmi_change,
        average_calories=0.0,  # Calculated from meal logs separately
        average_water=average_water,
        average_steps=average_steps,
        average_sleep_hours=average_sleep,
        mood_distribution=mood_dist,
        goal_progress_percent=goal_progress,
    )


def calculate_goal_progress_items(
    user_goal: str,
    current_weight: Optional[float],
    target_weight: Optional[float],
    height_cm: Optional[float],
    days_active: int = 0,
) -> List[GoalProgress]:
    """Calculate progress for individual goals."""
    goals = []
    
    if user_goal == "weight_loss" and current_weight and target_weight and height_cm:
        weight_to_lose = current_weight - target_weight
        progress = calculate_daily_goal_progress(
            max(0, weight_to_lose - (current_weight - target_weight)),
            weight_to_lose
        ) if weight_to_lose > 0 else 0
        
        goals.append(GoalProgress(
            goal_name="Weight Loss",
            current_value=current_weight,
            target_value=target_weight,
            unit="kg",
            progress_percent=progress,
            recommendation=f"Continue tracking diet and exercise. {weight_to_lose:.1f}kg to target."
        ))
        
        # BMI goal
        current_bmi = calculate_bmi(current_weight, height_cm)
        target_bmi = 22  # Normal BMI
        goals.append(GoalProgress(
            goal_name="BMI",
            current_value=current_bmi,
            target_value=target_bmi,
            unit="BMI",
            progress_percent=100 - ((current_bmi - target_bmi) / current_bmi * 100),
            recommendation=f"Current BMI: {current_bmi} ({calculate_bmi_category(current_bmi)})"
        ))
    
    elif user_goal == "muscle_gain" and current_weight and target_weight:
        weight_to_gain = target_weight - current_weight
        progress = calculate_daily_goal_progress(
            current_weight - (target_weight - weight_to_gain) if target_weight else 0,
            weight_to_gain
        ) if weight_to_gain > 0 else 100
        
        goals.append(GoalProgress(
            goal_name="Muscle Gain",
            current_value=current_weight,
            target_value=target_weight,
            unit="kg",
            progress_percent=progress,
            recommendation=f"Focus on strength training. {weight_to_gain:.1f}kg to target."
        ))
    
    else:  # maintenance
        if current_weight and target_weight:
            weight_variance = abs(current_weight - target_weight)
            progress = 100 if weight_variance < 2 else max(0, 100 - weight_variance * 10)
            goals.append(GoalProgress(
                goal_name="Weight Maintenance",
                current_value=current_weight,
                target_value=target_weight,
                unit="kg",
                progress_percent=progress,
                recommendation=f"Maintain consistent weight. Variance: {weight_variance:.1f}kg"
            ))
    
    return goals


def get_health_insights(progress: ProgressMetrics, user_goal: str) -> List[str]:
    """Generate health insights based on progress metrics."""
    insights = []
    
    if progress.weight_change_kg is not None:
        if user_goal == "weight_loss":
            if progress.weight_change_kg < 0:
                insights.append(f"✅ Great progress! You've lost {abs(progress.weight_change_kg)}kg.")
            elif progress.weight_change_kg > 1:
                insights.append(f"⚠️ Weight increased by {progress.weight_change_kg}kg. Check your diet.")
        elif user_goal == "muscle_gain":
            if progress.weight_change_kg > 0:
                insights.append(f"✅ Gaining weight steadily. +{progress.weight_change_kg}kg progress.")
            else:
                insights.append("⚠️ Weight unchanged. Increase calorie intake for muscle gain.")
    
    if progress.average_water > 0:
        if progress.average_water >= 2.5:
            insights.append(f"✅ Great hydration! Average {progress.average_water}L per day.")
        else:
            insights.append(f"💧 Low water intake. Average {progress.average_water}L. Target 2.5L.")
    
    if progress.average_steps > 0:
        if progress.average_steps >= 10000:
            insights.append(f"🚶 Excellent activity! Average {progress.average_steps} steps/day.")
        else:
            insights.append(f"🚶 Activity low. Average {progress.average_steps} steps. Target 10,000.")
    
    if progress.average_sleep_hours:
        if 7 <= progress.average_sleep_hours <= 9:
            insights.append(f"😴 Good sleep! Average {progress.average_sleep_hours}h per night.")
        else:
            insights.append(f"😴 Sleep irregular. Average {progress.average_sleep_hours}h. Target 7-9h.")
    
    if not insights:
        insights.append("📊 Keep tracking your metrics for personalized insights!")
    
    return insights
