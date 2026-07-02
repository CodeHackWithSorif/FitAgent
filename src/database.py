"""
Database module for FitAgent - Handles all SQLite ORM operations.
Stores user profiles, meal logs, workout logs, and health metrics.
"""

import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any

# --- DATABASE SETUP ---
DB_PATH = "fitAgent_data.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- SQLALCHEMY ORM MODELS ---
class User(Base):
    """User profile model - stores personal health information."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)  # Male, Female, Other
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    goal = Column(String(100), nullable=False)  # weight_loss, muscle_gain, maintenance, endurance
    diet_preference = Column(String(50), nullable=False)  # vegetarian, non_veg, vegan
    daily_water_goal = Column(Float, default=2.5)  # in liters
    daily_steps_goal = Column(Integer, default=10000)
    dietary_restrictions = Column(Text)  # JSON string of restrictions
    health_conditions = Column(Text)  # JSON string of conditions (diabetes, hypertension, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MealLog(Base):
    """Meal logging model - tracks food intake."""
    __tablename__ = "meal_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    meal_name = Column(String(200), nullable=False)
    meal_type = Column(String(50), nullable=False)  # breakfast, lunch, dinner, snack
    quantity = Column(String(100), nullable=False)  # e.g., "1 bowl", "150g"
    calories = Column(Float, nullable=False)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    fiber_g = Column(Float)
    ingredients = Column(Text)  # Comma-separated ingredients
    logged_at = Column(DateTime, default=datetime.utcnow)


class WorkoutLog(Base):
    """Workout logging model - tracks exercise."""
    __tablename__ = "workout_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    exercise_name = Column(String(200), nullable=False)
    exercise_type = Column(String(50), nullable=False)  # cardio, strength, flexibility, sports
    duration_minutes = Column(Integer, nullable=False)
    intensity = Column(String(20))  # low, moderate, high
    calories_burned = Column(Float)
    distance_km = Column(Float)  # For cardio
    sets_reps = Column(String(100))  # For strength training
    notes = Column(Text)
    logged_at = Column(DateTime, default=datetime.utcnow)


class HealthMetrics(Base):
    """Daily health metrics model - tracks comprehensive health data."""
    __tablename__ = "health_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    weight_kg = Column(Float)
    bmi = Column(Float)
    water_intake_liters = Column(Float, default=0.0)
    steps = Column(Integer, default=0)
    sleep_hours = Column(Float)
    mood = Column(String(50))  # happy, neutral, stressed, tired
    energy_level = Column(String(50))  # low, medium, high
    notes = Column(Text)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class ReminderSettings(Base):
    """Reminder settings model."""
    __tablename__ = "reminder_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True)
    meal_reminders_enabled = Column(Boolean, default=True)
    meal_reminder_time_before_minutes = Column(Integer, default=30)
    water_reminders_enabled = Column(Boolean, default=True)
    water_reminder_interval_hours = Column(Integer, default=2)
    workout_reminders_enabled = Column(Boolean, default=True)
    workout_reminder_time_before_minutes = Column(Integer, default=15)
    sleep_reminder_enabled = Column(Boolean, default=True)
    sleep_reminder_time = Column(String(5), default="22:00")
    mood_check_enabled = Column(Boolean, default=True)
    mood_check_time = Column(String(5), default="20:00")
    notification_sound_enabled = Column(Boolean, default=True)
    vibration_enabled = Column(Boolean, default=True)
    quiet_hours_start = Column(String(5), default="22:00")
    quiet_hours_end = Column(String(5), default="07:00")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReminderModel(Base):
    """Reminder persistence model."""
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    reminder_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    data = Column(JSON, nullable=True)


# --- PYDANTIC MODELS (for validation & API) ---
class UserBase(BaseModel):
    name: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    goal: str
    diet_preference: str
    daily_water_goal: float = 2.5
    daily_steps_goal: int = 10000
    dietary_restrictions: Optional[str] = None
    health_conditions: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MealLogBase(BaseModel):
    meal_name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    quantity: str
    calories: float
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    ingredients: Optional[str] = None


class MealLogCreate(MealLogBase):
    user_id: int


class MealLogResponse(MealLogBase):
    id: int
    user_id: int
    logged_at: datetime
    
    class Config:
        from_attributes = True


class WorkoutLogBase(BaseModel):
    exercise_name: str
    exercise_type: str
    duration_minutes: int
    intensity: Optional[str] = None
    calories_burned: Optional[float] = None
    distance_km: Optional[float] = None
    sets_reps: Optional[str] = None
    notes: Optional[str] = None


class WorkoutLogCreate(WorkoutLogBase):
    user_id: int


class WorkoutLogResponse(WorkoutLogBase):
    id: int
    user_id: int
    logged_at: datetime
    
    class Config:
        from_attributes = True


class HealthMetricsBase(BaseModel):
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    water_intake_liters: float = 0.0
    steps: int = 0
    sleep_hours: Optional[float] = None
    mood: Optional[str] = None
    energy_level: Optional[str] = None
    notes: Optional[str] = None


class HealthMetricsCreate(HealthMetricsBase):
    user_id: int


class HealthMetricsResponse(HealthMetricsBase):
    id: int
    user_id: int
    date: datetime
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class ReminderSettingsBase(BaseModel):
    user_id: int
    meal_reminders_enabled: bool = True
    meal_reminder_time_before_minutes: int = 30
    water_reminders_enabled: bool = True
    water_reminder_interval_hours: int = 2
    workout_reminders_enabled: bool = True
    workout_reminder_time_before_minutes: int = 15
    sleep_reminder_enabled: bool = True
    sleep_reminder_time: str = "22:00"
    mood_check_enabled: bool = True
    mood_check_time: str = "20:00"
    notification_sound_enabled: bool = True
    vibration_enabled: bool = True
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"


class ReminderSettingsCreate(ReminderSettingsBase):
    pass


class ReminderSettingsResponse(ReminderSettingsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderBase(BaseModel):
    user_id: int
    reminder_type: str
    title: str
    description: str
    scheduled_time: datetime
    status: str = "pending"
    data: Optional[Dict[str, Any]] = None

    @field_validator("data", mode="before")
    @classmethod
    def parse_data(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("Reminder data must be a valid JSON object") from exc
            return parsed
        return value


class ReminderCreate(ReminderBase):
    pass


class ReminderResponse(ReminderBase):
    id: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
    }


# --- CRUD OPERATIONS ---
class DatabaseService:
    """Service class for all database operations."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def init_db(self):
        """Initialize database tables."""
        Base.metadata.create_all(bind=engine)
        print(f"[OK] Database initialized: {DB_PATH}")
    
    def close(self):
        """Close database session."""
        self.db.close()
    
    # --- USER OPERATIONS ---
    def create_user(self, user: UserCreate) -> UserResponse:
        """Create a new user profile."""
        db_user = User(**user.dict())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return UserResponse.from_orm(db_user)
    
    def get_user(self, user_id: int) -> Optional[UserResponse]:
        """Get user by ID."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        return UserResponse.from_orm(db_user) if db_user else None
    
    def get_all_users(self) -> List[UserResponse]:
        """Get all users."""
        users = self.db.query(User).all()
        return [UserResponse.from_orm(u) for u in users]
    
    def update_user(self, user_id: int, user: UserBase) -> Optional[UserResponse]:
        """Update user profile."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if db_user:
            for key, value in user.dict().items():
                setattr(db_user, key, value)
            db_user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_user)
            return UserResponse.from_orm(db_user)
        return None
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user and related data."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if db_user:
            self.db.delete(db_user)
            self.db.commit()
            return True
        return False
    
    # --- MEAL LOG OPERATIONS ---
    def log_meal(self, meal: MealLogCreate) -> MealLogResponse:
        """Log a meal."""
        db_meal = MealLog(**meal.dict())
        self.db.add(db_meal)
        self.db.commit()
        self.db.refresh(db_meal)
        return MealLogResponse.from_orm(db_meal)
    
    def get_user_meal_logs(self, user_id: int, days: int = 7) -> List[MealLogResponse]:
        """Get user's meal logs from last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        meals = self.db.query(MealLog).filter(
            MealLog.user_id == user_id,
            MealLog.logged_at >= start_date
        ).order_by(MealLog.logged_at.desc()).all()
        return [MealLogResponse.from_orm(m) for m in meals]
    
    def get_today_calories(self, user_id: int) -> float:
        """Get total calories consumed today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        meals = self.db.query(MealLog).filter(
            MealLog.user_id == user_id,
            MealLog.logged_at >= today_start
        ).all()
        return sum(meal.calories for meal in meals)
    
    def delete_meal_log(self, meal_id: int) -> bool:
        """Delete a meal log."""
        meal = self.db.query(MealLog).filter(MealLog.id == meal_id).first()
        if meal:
            self.db.delete(meal)
            self.db.commit()
            return True
        return False
    
    # --- WORKOUT LOG OPERATIONS ---
    def log_workout(self, workout: WorkoutLogCreate) -> WorkoutLogResponse:
        """Log a workout."""
        db_workout = WorkoutLog(**workout.dict())
        self.db.add(db_workout)
        self.db.commit()
        self.db.refresh(db_workout)
        return WorkoutLogResponse.from_orm(db_workout)
    
    def get_user_workout_logs(self, user_id: int, days: int = 7) -> List[WorkoutLogResponse]:
        """Get user's workout logs from last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        workouts = self.db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.logged_at >= start_date
        ).order_by(WorkoutLog.logged_at.desc()).all()
        return [WorkoutLogResponse.from_orm(w) for w in workouts]
    
    def get_today_calories_burned(self, user_id: int) -> float:
        """Get total calories burned today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        workouts = self.db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.logged_at >= today_start
        ).all()
        return sum(workout.calories_burned or 0 for workout in workouts)
    
    # --- HEALTH METRICS OPERATIONS ---
    def log_health_metrics(self, metrics: HealthMetricsCreate) -> HealthMetricsResponse:
        """Log health metrics."""
        db_metrics = HealthMetrics(**metrics.dict())
        self.db.add(db_metrics)
        self.db.commit()
        self.db.refresh(db_metrics)
        return HealthMetricsResponse.from_orm(db_metrics)
    
    def get_user_health_metrics(self, user_id: int, days: int = 30) -> List[HealthMetricsResponse]:
        """Get user's health metrics from last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        metrics = self.db.query(HealthMetrics).filter(
            HealthMetrics.user_id == user_id,
            HealthMetrics.recorded_at >= start_date
        ).order_by(HealthMetrics.recorded_at.desc()).all()
        return [HealthMetricsResponse.from_orm(m) for m in metrics]
    
    def get_latest_health_metrics(self, user_id: int) -> Optional[HealthMetricsResponse]:
        """Get latest health metrics for user."""
        metrics = self.db.query(HealthMetrics).filter(
            HealthMetrics.user_id == user_id
        ).order_by(HealthMetrics.recorded_at.desc()).first()
        return HealthMetricsResponse.from_orm(metrics) if metrics else None

    # --- REMINDER SETTINGS OPERATIONS ---
    def create_reminder_settings(self, settings: ReminderSettingsCreate) -> ReminderSettingsResponse:
        """Create reminder settings for a user."""
        db_settings = ReminderSettings(**settings.dict())
        self.db.add(db_settings)
        self.db.commit()
        self.db.refresh(db_settings)
        return ReminderSettingsResponse.from_orm(db_settings)

    def get_reminder_settings(self, user_id: int) -> Optional[ReminderSettingsResponse]:
        """Get reminder settings for a user."""
        settings = self.db.query(ReminderSettings).filter(ReminderSettings.user_id == user_id).first()
        return ReminderSettingsResponse.from_orm(settings) if settings else None

    def update_reminder_settings(self, user_id: int, settings: ReminderSettingsCreate) -> Optional[ReminderSettingsResponse]:
        """Update reminder settings for a user."""
        db_settings = self.db.query(ReminderSettings).filter(ReminderSettings.user_id == user_id).first()
        if db_settings:
            for key, value in settings.dict().items():
                setattr(db_settings, key, value)
            db_settings.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_settings)
            return ReminderSettingsResponse.from_orm(db_settings)
        return None

    # --- REMINDER OPERATIONS ---
    def create_reminder(self, reminder: ReminderCreate) -> ReminderResponse:
        """Create a reminder for a user."""
        reminder_data = reminder.dict()
        db_reminder = ReminderModel(**reminder_data)
        self.db.add(db_reminder)
        self.db.commit()
        self.db.refresh(db_reminder)
        return ReminderResponse.model_validate(db_reminder, from_attributes=True)

    def get_user_reminders(self, user_id: int, status: Optional[str] = None, days: int = 7) -> List[ReminderResponse]:
        """Get reminders for a user from the last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(ReminderModel).filter(
            ReminderModel.user_id == user_id,
            ReminderModel.scheduled_time >= start_date,
        )
        if status:
            query = query.filter(ReminderModel.status == status)
        reminders = query.order_by(ReminderModel.scheduled_time.asc()).all()
        return [ReminderResponse.model_validate(reminder, from_attributes=True) for reminder in reminders]

    def update_reminder_status(self, reminder_id: int, status: str) -> Optional[ReminderResponse]:
        """Update the status of a reminder."""
        reminder = self.db.query(ReminderModel).filter(ReminderModel.id == reminder_id).first()
        if reminder:
            reminder.status = status
            if status == "completed":
                reminder.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(reminder)
            return ReminderResponse.model_validate(reminder, from_attributes=True)
        return None

    def snooze_reminder(self, reminder_id: int, minutes: int = 10) -> Optional[ReminderResponse]:
        """Snooze a reminder by a given number of minutes."""
        reminder = self.db.query(ReminderModel).filter(ReminderModel.id == reminder_id).first()
        if reminder and reminder.status == "pending":
            reminder.scheduled_time = reminder.scheduled_time + timedelta(minutes=minutes)
            self.db.commit()
            self.db.refresh(reminder)
            return ReminderResponse.model_validate(reminder, from_attributes=True)
        return None

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder."""
        reminder = self.db.query(ReminderModel).filter(ReminderModel.id == reminder_id).first()
        if reminder:
            self.db.delete(reminder)
            self.db.commit()
            return True
        return False


# --- HELPER FUNCTIONS ---
def get_db_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService()


def init_database():
    """Initialize database on app startup."""
    service = DatabaseService()
    service.init_db()
    service.close()


if __name__ == "__main__":
    # Initialize database
    init_database()
