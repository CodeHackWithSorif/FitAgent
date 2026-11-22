# FitAgent - Autonomous AI Health Co-Pilot
*Bridging the gap between health knowledge and actionable habits.*
<img width="128" height="128" alt="image" src="https://github.com/user-attachments/assets/ca5adfce-3af0-474d-8ef7-339483647e0e" />
[Live App](https://whatsapp.com/channel/0029VbBJa7iIt5rtVuNzfP2g)

## 🏆 Hackathon Context
This project was built for the **INDIA RUNS Hackathon (Track 3: Everyday AI)** and **Gen AI Academy Cohort 2**.

## 🚀 Overview & Mission
FitAgent is an autonomous AI health co-pilot designed to transform health knowledge into actionable, daily routines. Recognizing the unique nuances of Indian dietary habits and Ayurvedic principles, FitAgent acts as your personal nutritionist, fitness coach, and daily scheduler all in one. Our mission is to bridge the gap between knowing what's healthy and actually doing it, making well-being a seamless part of your lifestyle.

## ✨ Key Features
- **Personalized Health Planning**: Generates detailed, hour-by-hour 14-hour diet and workout schedules tailored to your profile.
- **AI-Powered Nutritional Analysis**: Dive deep into the foods you eat with insights blending modern nutritional science and ancient Ayurvedic wisdom.
- **Actionable Reminders**: Export your routines and sync them natively with your mobile and desktop calendars for timely alerts.
- **Autonomous Workflow**: Enjoy intelligent decision-making support that adapts to your health goals, dietary preferences, and restrictions.

## 🛠 Technology Stack
- **Google Cloud Vertex AI**
- **Gemini 1.5 Flash**
- **Streamlit**
- **Python**
- **Google Cloud Platform (GCP)**

## ⚙️ Installation Guide

### 1. Clone the Repository
```bash
git clone https://github.com/CodeHackWithSorif/FitAgent.git
cd FitAgent
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Authenticate with Google Cloud
FitAgent strictly utilizes Google Cloud Vertex AI via Application Default Credentials (ADC).
```bash
gcloud auth application-default login
```

### 5. Run the Application
```bash
streamlit run app.py
```

## 📱 Usage Guide (Mobile & Laptop)
FitAgent allows you to integrate your health plan directly into your daily routine using the **Export Reminders** page.

- **Mobile Users**: Download the generated `.ics` file from the app. Open it on your phone to import all your scheduled meals, workouts, and habits directly into Google Calendar or Apple Calendar. Ensure notifications are enabled for your calendar app.
- **Laptop/Desktop Users**: Download the native scheduler script provided on the page. 
  - **Windows**: Run the downloaded script to register tasks in the Windows Task Scheduler.
  - **macOS/Linux**: Follow the instructions provided to install the shell script as a `cron` job.

## 🧪 Demo Checklist
To fully experience FitAgent, follow this 10-step sequence:
1. **Activate Environment**: Ensure your virtual environment is active.
2. **Authenticate**: Run `gcloud auth application-default login`.
3. **Launch**: Start the app via `streamlit run app.py`.
4. **Create Profile**: Navigate to the "Create Profile" page and input your health goals, diet, and details.
5. **Generate Plan**: Go to "Health Plan" and let Vertex AI generate your personalized 14-hour routine.
6. **Review Insights**: Navigate to the "Food Nutritional Analysis" page and analyze an Indian dish (e.g., Paneer Butter Masala).
7. **Create Reminders**: On the Health Plan page, click "Create Reminders from Plan".
8. **Export Schedule**: Head to the "Export Reminders" page and download the `.ics` file or Windows/Linux scheduler script.
9. **Test Reminders**: Import the `.ics` into your mobile calendar or run the scheduler script on your laptop.
10. **Verify Notifications**: Wait for the scheduled time to confirm native OS or mobile alerts are working properly!

## 🤝 Credits & Socials
FitAgent was built by **Team Logic Loopers**.

**Creator**: Code Hack with Sorif

Connect with us and follow our journey:
- 💼 [LinkedIn](https://www.linkedin.com/in/sorif-hossain-code-hack/)
- 📺 [YouTube Channel](https://www.youtube.com/@CodeHackWithSorif)
- 💻 [GitHub](https://github.com/CodeHackWithSorif)
- 💬 [WhatsApp Channel](https://whatsapp.com/channel/0029VbBJa7iIt5rtVuNzfP2g)
