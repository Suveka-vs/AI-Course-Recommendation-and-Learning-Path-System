"""
LLM-based personalized recommendation explanations.

Takes the user's current skills, target role, skill gaps, and the
RAG-retrieved courses, and asks an LLM (Gemini) to generate a short,
personalized explanation of the gap and a suggested learning order.

If no API key is configured, or the API call fails for any reason
(network issue, quota, bad key), we fall back to a rule-based template
so the website keeps working end-to-end without the LLM.
"""
import json
from django.conf import settings

def _build_prompt(current_skills, target_role, matched, missing, retrieved_courses):
    course_lines = []
    for c in retrieved_courses[:6]:
        course_lines.append(
            f"- {c['course_name']} ({c['platform']}, {c['price_type']}, "
            f"{c['level']}, {c['duration']}, rating {c['rating']}) — skill: {c['skill']}"
        )
    courses_text = "\n".join(course_lines) if course_lines else "No specific courses retrieved."

    prompt = f"""You are a friendly career mentor helping a student plan their learning.

Student's current skills: {', '.join(current_skills) if current_skills else 'None yet'}
Target job role: {target_role}
Skills already matched for this role: {', '.join(matched) if matched else 'None'}
Missing skills for this role: {', '.join(missing) if missing else 'None'}

Relevant courses retrieved for the missing skills:
{courses_text}

Write a short, encouraging, personalized explanation (4-6 sentences) that:
1. Acknowledges the student's existing strengths.
2. Clearly names the main skill gaps for their target role.
3. Suggests a sensible order to learn the missing skills in (which one first and why).
4. Mentions that both free and paid course options are available.

Keep it concise, plain text, no markdown headers, no bullet lists — just a short paragraph."""
    return prompt


def _fallback_explanation(current_skills, target_role, matched, missing):
    """Rule-based explanation used when the LLM is unavailable."""
    if not missing:
        return (
            f"You already have all the key skills typically required for a {target_role} role. "
            f"Great foundation — consider deepening your expertise or exploring an advanced specialization next."
        )

    strengths = ', '.join(matched) if matched else 'the basics you already have'
    first_gap = missing[0]
    remaining = missing[1:]

    text = (
        f"You already have a solid foundation with {strengths}. "
        f"To move toward becoming a {target_role}, your main gaps are: {', '.join(missing)}. "
        f"We'd suggest starting with {first_gap}, since it tends to be a building block for the others. "
    )
    if remaining:
        text += f"After that, work through {', '.join(remaining)} in order of difficulty. "
    text += "Both free and paid course options are available below to help you close these gaps at your own pace."
    return text


def generate_explanation(current_skills, target_role, matched, missing, retrieved_courses):
    """
    Returns a dict: {'explanation': str, 'source': 'llm' | 'fallback'}
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    if not api_key:
        return {
            'explanation': _fallback_explanation(current_skills, target_role, matched, missing),
            'source': 'fallback',
        }

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = _build_prompt(current_skills, target_role, matched, missing, retrieved_courses)
        response = model.generate_content(prompt)

        text = (response.text or '').strip()
        if not text:
            raise ValueError('Empty response from LLM')

        return {'explanation': text, 'source': 'llm'}

    except Exception as e:
        print(f"[llm] Gemini call failed, using fallback: {e}")
        return {
            'explanation': _fallback_explanation(current_skills, target_role, matched, missing),
            'source': 'fallback',
        }

FALLBACK_QUESTION_BANK = {
    'python': [
        {'question': 'Which keyword is used to define a function in Python?',
         'options': ['function', 'def', 'func', 'define'], 'correct_index': 1},
        {'question': 'Which data type is immutable in Python?',
         'options': ['list', 'dict', 'tuple', 'set'], 'correct_index': 2},
        {'question': 'What does len() do?',
         'options': ['Returns the type', 'Returns the length of an object', 'Deletes an object', 'Converts to string'], 'correct_index': 1},
        {'question': 'Which symbol is used for comments in Python?',
         'options': ['//', '#', '--', '/* */'], 'correct_index': 1},
        {'question': "What is the output of type(5.0)?",
         'options': ["<class 'int'>", "<class 'float'>", "<class 'str'>", "<class 'complex'>"], 'correct_index': 1},
    ],
    'django': [
        {'question': "Which file defines a Django app's database models?",
         'options': ['views.py', 'urls.py', 'models.py', 'settings.py'], 'correct_index': 2},
        {'question': 'What command applies migrations to the database?',
         'options': ['python manage.py migrate', 'python manage.py makemigrations', 'python manage.py runserver', 'python manage.py collectstatic'], 'correct_index': 0},
        {'question': 'Which Django component handles URL routing?',
         'options': ['models.py', 'urls.py', 'admin.py', 'forms.py'], 'correct_index': 1},
        {'question': "What is Django's built-in templating engine used for?",
         'options': ['Database queries', 'Rendering HTML with dynamic data', 'Handling HTTP requests', 'Managing migrations'], 'correct_index': 1},
        {'question': 'Which decorator restricts a view to logged-in users?',
         'options': ['@csrf_exempt', '@login_required', '@require_POST', '@staff_member_required'], 'correct_index': 1},
    ],
    'sql': [
        {'question': 'Which SQL keyword retrieves data from a table?',
         'options': ['GET', 'SELECT', 'FETCH', 'SHOW'], 'correct_index': 1},
        {'question': 'Which clause filters rows based on a condition?',
         'options': ['WHERE', 'ORDER BY', 'GROUP BY', 'HAVING'], 'correct_index': 0},
        {'question': 'Which SQL command adds a new row to a table?',
         'options': ['UPDATE', 'INSERT', 'ALTER', 'ADD'], 'correct_index': 1},
        {'question': 'Which JOIN returns only matching rows from both tables?',
         'options': ['LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'FULL JOIN'], 'correct_index': 2},
        {'question': 'Which keyword removes duplicate rows from a result set?',
         'options': ['UNIQUE', 'DISTINCT', 'FILTER', 'ONLY'], 'correct_index': 1},
    ],
    'html': [
        {'question': 'Which tag is used to create a hyperlink?',
         'options': ['<link>', '<a>', '<href>', '<url>'], 'correct_index': 1},
        {'question': 'Which tag defines the largest heading?',
         'options': ['<h6>', '<heading>', '<h1>', '<head>'], 'correct_index': 2},
        {'question': "Which attribute specifies an image's alternate text?",
         'options': ['alt', 'src', 'title', 'name'], 'correct_index': 0},
        {'question': 'Which tag is used to create an unordered list?',
         'options': ['<ol>', '<list>', '<ul>', '<li>'], 'correct_index': 2},
        {'question': 'Which HTML element typically contains page metadata?',
         'options': ['<body>', '<meta>', '<head>', '<title>'], 'correct_index': 2},
    ],
    'css': [
        {'question': 'Which property changes text color?',
         'options': ['font-color', 'text-color', 'color', 'background-color'], 'correct_index': 2},
        {'question': "Which CSS property controls spacing outside an element's border?",
         'options': ['padding', 'margin', 'spacing', 'border'], 'correct_index': 1},
        {'question': 'Which selector targets all elements with class "box"?',
         'options': ['#box', '.box', 'box', '*box'], 'correct_index': 1},
        {'question': 'Which display value hides an element completely?',
         'options': ['hidden', 'invisible', 'none', 'collapse'], 'correct_index': 2},
        {'question': 'What does "flex" as a display value enable?',
         'options': ['Grid layout', 'Flexible box layout', 'Table layout', 'Fixed layout'], 'correct_index': 1},
    ],
    'javascript': [
        {'question': 'Which keyword declares a block-scoped variable in JavaScript?',
         'options': ['var', 'let', 'global', 'static'], 'correct_index': 1},
        {'question': 'Which method converts a JSON string into a JavaScript object?',
         'options': ['JSON.stringify()', 'JSON.parse()', 'JSON.toObject()', 'Object.parse()'], 'correct_index': 1},
        {'question': 'Which operator checks both value and type equality?',
         'options': ['==', '=', '===', '!='], 'correct_index': 2},
        {'question': 'Which function selects an element by ID in the DOM?',
         'options': ['getElementById()', 'querySelectorClass()', 'getElement()', 'selectById()'], 'correct_index': 0},
        {'question': 'What does "===" do differently than "=="?',
         'options': ['Nothing different', 'Compares only type', 'Compares value and type strictly', 'Compares only value'], 'correct_index': 2},
    ],
    'machine learning': [
        {'question': 'Which type of learning uses labeled data?',
         'options': ['Unsupervised learning', 'Supervised learning', 'Reinforcement learning', 'Clustering'], 'correct_index': 1},
        {'question': 'Which algorithm is commonly used for classification problems?',
         'options': ['Linear Regression', 'K-Means', 'Logistic Regression', 'PCA'], 'correct_index': 2},
        {'question': 'What does "overfitting" mean?',
         'options': ['Model performs well on new data', 'Model performs poorly on training data', 'Model memorizes training data but fails on new data', 'Model has too few parameters'], 'correct_index': 2},
        {'question': 'Which metric is commonly used to evaluate classification models?',
         'options': ['RMSE', 'Accuracy', 'MAE', 'R-squared'], 'correct_index': 1},
        {'question': 'What is the purpose of splitting data into training and test sets?',
         'options': ['To reduce dataset size', 'To evaluate model performance on unseen data', 'To increase model complexity', 'To remove outliers'], 'correct_index': 1},
    ],
    'power bi': [
        {'question': 'What is Power BI primarily used for?',
         'options': ['Writing code', 'Data visualization and business intelligence', 'Video editing', 'Network security'], 'correct_index': 1},
        {'question': 'Which Power BI component is used to write custom calculations?',
         'options': ['Power Query', 'DAX', 'Power Pivot', 'Power View'], 'correct_index': 1},
        {'question': 'What is a "dashboard" in Power BI?',
         'options': ['A single visualization', 'A collection of visuals on one page for monitoring', 'A data source', 'A type of chart'], 'correct_index': 1},
        {'question': 'Which feature is used to import and transform data in Power BI?',
         'options': ['Power Query', 'DAX', 'Power BI Service', 'Power Map'], 'correct_index': 0},
        {'question': 'What file extension is used for a Power BI Desktop file?',
         'options': ['.pbix', '.pbid', '.pbi', '.pwbi'], 'correct_index': 0},
    ],
    'git': [
        {'question': 'Which command initializes a new Git repository?',
         'options': ['git start', 'git init', 'git create', 'git new'], 'correct_index': 1},
        {'question': 'Which command stages changes for commit?',
         'options': ['git commit', 'git add', 'git push', 'git stage'], 'correct_index': 1},
        {'question': 'Which command creates a new branch?',
         'options': ['git branch <name>', 'git new-branch <name>', 'git create <name>', 'git checkout-new <name>'], 'correct_index': 0},
        {'question': 'What does "git clone" do?',
         'options': ['Deletes a repository', 'Creates a copy of a remote repository', 'Merges two branches', 'Commits changes'], 'correct_index': 1},
        {'question': 'Which command uploads local commits to a remote repository?',
         'options': ['git pull', 'git fetch', 'git push', 'git merge'], 'correct_index': 2},
    ],
    'data analysis': [
        {'question': 'Which Python library is commonly used for data manipulation?',
         'options': ['Matplotlib', 'Pandas', 'Flask', 'Django'], 'correct_index': 1},
        {'question': 'What does "cleaning data" typically involve?',
         'options': ['Deleting the entire dataset', 'Handling missing values and correcting errors', 'Encrypting the data', 'Visualizing the data'], 'correct_index': 1},
        {'question': 'Which chart type is best for showing trends over time?',
         'options': ['Pie chart', 'Line chart', 'Scatter plot', 'Bar chart'], 'correct_index': 1},
        {'question': 'What is a "pivot table" used for?',
         'options': ['Sorting a dataset alphabetically', 'Summarizing and aggregating data', 'Encrypting sensitive data', 'Writing SQL queries'], 'correct_index': 1},
        {'question': 'Which measure represents the middle value of a sorted dataset?',
         'options': ['Mean', 'Mode', 'Median', 'Range'], 'correct_index': 2},
    ],
}

GENERIC_FALLBACK_QUESTIONS = [
    {'question': 'What is generally the best first step when learning a new technical skill?',
     'options': ['Memorize everything at once', 'Understand the fundamentals and practice', 'Skip the basics and go to advanced topics', 'Avoid hands-on practice'], 'correct_index': 1},
    {'question': 'Why is hands-on practice important when learning a new skill?',
     'options': ["It's not important", 'It reinforces theoretical understanding', 'It replaces the need to understand concepts', 'It has no impact on learning'], 'correct_index': 1},
    {'question': 'What does "documentation" refer to in a technical context?',
     'options': ['A type of programming language', 'Official reference material explaining how something works', 'A testing framework', 'A database system'], 'correct_index': 1},
    {'question': 'Why is it useful to break a large problem into smaller steps?',
     'options': ['It makes the problem harder', 'It makes the problem more manageable and easier to solve', 'It increases errors', 'It has no benefit'], 'correct_index': 1},
    {'question': 'What is a good habit when debugging code?',
     'options': ['Ignoring error messages', 'Reading error messages carefully and testing incrementally', 'Rewriting the entire program', 'Guessing randomly'], 'correct_index': 1},
]


def _fallback_questions(skill_name):
    questions = FALLBACK_QUESTION_BANK.get(skill_name.strip().lower(), GENERIC_FALLBACK_QUESTIONS)
    return {'questions': questions, 'source': 'fallback'}


def _build_question_prompt(skill_name, level, target_role):
    role_clause = f' for someone becoming a {target_role}' if target_role else ''
    return f"""Generate exactly 5 multiple choice questions to assess a learner's knowledge of "{skill_name}" at a {level} level{role_clause}.

Return ONLY valid JSON, no markdown, no code fences, no explanation — just a JSON array like this:

[
  {{"question": "...", "options": ["...", "...", "...", "..."], "correct_index": 0}}
]

Rules:
- Exactly 5 questions.
- Exactly 4 options per question.
- correct_index is the 0-based index (0-3) of the single correct option.
- Questions must be directly relevant to {skill_name}.
- Keep questions and options concise."""


def _parse_llm_questions(raw_text):
    """Parse and validate the LLM's JSON question output. Raises ValueError on any invalid structure."""
    cleaned = raw_text.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.strip('`')
        if cleaned.lower().startswith('json'):
            cleaned = cleaned[4:]

    questions = json.loads(cleaned)

    if not isinstance(questions, list) or len(questions) != 5:
        raise ValueError('Expected a list of exactly 5 questions')

    for q in questions:
        if not isinstance(q, dict) or 'question' not in q or 'options' not in q or 'correct_index' not in q:
            raise ValueError('Question missing required fields')
        if not isinstance(q['options'], list) or len(q['options']) != 4:
            raise ValueError('Each question must have exactly 4 options')
        if not isinstance(q['correct_index'], int) or not (0 <= q['correct_index'] <= 3):
            raise ValueError('correct_index must be an integer 0-3')

    return questions


def generate_questions(skill_name, level, target_role=''):
    """
    Returns {'questions': [...5 dicts...], 'source': 'llm' | 'fallback'}.
    Reuses the same GEMINI_API_KEY configuration as generate_explanation().
    Falls back to a curated question bank if the key is missing, the call
    fails, or the response can't be parsed into valid MCQs.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    if not api_key:
        return _fallback_questions(skill_name)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = _build_question_prompt(skill_name, level, target_role)
        response = model.generate_content(prompt)

        questions = _parse_llm_questions(response.text or '')
        return {'questions': questions, 'source': 'llm'}

    except Exception as e:
        print(f"[llm] Gemini question generation failed, using fallback: {e}")
        return _fallback_questions(skill_name)