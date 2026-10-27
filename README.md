# AI Course Recommendation and Learning Path System

An AI-powered web application that helps users identify suitable career roles, discover relevant courses, analyze skill gaps, and generate personalized learning paths based on their skills and interests.

## Features

- **Resume Analysis:** Upload a resume in PDF format to extract skills and relevant information.
- **Career Role Prediction:** Predict suitable career roles using Machine Learning.
- **Course Recommendation:** Recommend relevant courses based on user skills and career goals.
- **Skill Gap Analysis:** Identify missing skills required for a target career role.
- **Personalized Learning Path:** Generate a structured learning path to improve skills.
- **AI-Powered Guidance:** Provide learning assistance using Gemini API and Retrieval-Augmented Generation (RAG).
- **Skill Assessment:** Evaluate knowledge through multiple-choice questions (MCQs).
- **Progress Tracking:** Monitor learning progress and assessment results.
- **User Authentication:** Support user registration and login.

## Technologies Used

- **Backend:** Python, Django
- **Frontend:** HTML, CSS, Bootstrap, JavaScript
- **Database:** SQLite
- **Machine Learning:** Scikit-learn, TF-IDF, Logistic Regression
- **Natural Language Processing:** Resume parsing and skill extraction
- **AI and RAG:** Sentence Transformers, FAISS, Gemini API
- **Data Processing:** Pandas

## Project Structure

```text
AI_Course_Recommendation/
├── course_recommender/
├── recommender/
│   ├── migrations/
│   ├── templates/
│   ├── static/
│   ├── models.py
│   ├── views.py
│   ├── resume_parser.py
│   ├── role_predictor.py
│   ├── course_recommender.py
│   ├── skill_extractor.py
│   └── learning_path.py
├── dataset/
├── ml_models/
├── rag_index/
├── media/
├── manage.py
├── .env.example
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Suveka-vs/AI-Course-Recommendation-and-Learning-Path-System.git
```

### 2. Navigate to the Project Folder

```bash
cd AI-Course-Recommendation-and-Learning-Path-System
```

### 3. Create a Virtual Environment

```bash
python -m venv env
```

Activate it on Windows:

```bash
env\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r course_recommender/requirements.txt
```

### 5. Configure Environment Variables

Configure the required environment variables using `.env.example` as a reference. Add your own Gemini API key if AI-powered guidance requires it. Never commit real API keys or passwords.

### 6. Apply Database Migrations

```bash
python manage.py migrate
```

### 7. Start the Development Server

```bash
python manage.py runserver
```

Open the following URL in your browser:

`http://127.0.0.1:8000/`

## How It Works

1. Register or log in to the application.
2. Upload a resume or enter skills manually.
3. Analyze skills and predict suitable career roles.
4. Explore recommended courses and identify skill gaps.
5. Follow the personalized learning path.
6. Complete MCQ assessments and track progress.
7. Use AI-powered guidance to support further learning.

## Future Enhancements

- Improve career prediction accuracy using larger datasets.
- Add more course providers and learning resources.
- Enhance personalized learning recommendations.
- Introduce additional assessments and progress analytics.
- Deploy the application to a cloud platform.

## Project Purpose

The goal of this project is to make career planning and skill development easier by combining Machine Learning, Natural Language Processing, and AI-powered learning assistance in a single web application.

*Developed as an AI-based web application for personalized career guidance and learning path generation.*
