import argparse
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Render synthetic UI previews without using the working database.')
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
from django.conf import settings
settings.DATABASES['default']['NAME'] = ':memory:'
settings.ALLOWED_HOSTS = ['testserver']
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.MEDIA_ROOT = args.output_dir / 'media'
django.setup()
from django.core.management import call_command
from django.test import Client
from django.contrib.auth.models import User
from subjects.models import Subject
from notes.models import Note
from documents.models import Document, DocumentChunk
from quizzes.models import QuizAttempt
from quizzes.services.quiz_persister import QuizPersister
from ai_assistant.models import ChatMessage

call_command('migrate', verbosity=0)
preview = args.output_dir.resolve()
preview.mkdir(parents=True, exist_ok=True)
user = User.objects.create_user('Alex', email='alex@example.test')
subject_names = ['Computer Science', 'Biology', 'Mathematics', 'Design & Technology']
subjects = [Subject.objects.create(user=user, name=name, description=description) for name, description in zip(subject_names, [
    'From algorithms to applications. Understanding how the digital world works.',
    'Exploring cells, ecosystems, and the remarkable science of living things.',
    'Finding patterns, solving problems, and seeing the world a little differently.',
    'Where useful ideas meet thoughtful experiences. Learning to build with intention.',
])]
text = ('Photosynthesis is the process by which plants convert light energy into chemical energy. '
        'Chlorophyll in the chloroplasts absorbs light. Water and carbon dioxide are used to produce glucose and oxygen.\n\n'
        'The light-dependent reactions occur in the thylakoid membranes. They produce ATP and NADPH. '
        'The Calvin cycle uses this energy to fix carbon dioxide into sugars in the stroma.\n\n'
        'Light intensity, carbon dioxide availability, and temperature can affect the rate of photosynthesis.')
doc_specs = [('Photosynthesis & cellular energy', subjects[1], text),
             ('A practical guide to algorithms', subjects[0], 'An algorithm is a sequence of clear steps for solving a problem. Binary search repeatedly halves a sorted search interval.'),
             ('Thinking in design systems', subjects[3], 'A design system connects reusable components, patterns, and guidelines. Consistency helps people build familiarity.'),
             ('An introduction to linear algebra', subjects[2], 'Vectors represent quantities with direction and magnitude. Matrices describe transformations between vector spaces.')]
documents = []
for title, subject, content in doc_specs:
    doc = Document.objects.create(user=user, subject=subject, title=title, extracted_text=content, file='demo.pdf')
    documents.append(doc)
notes = [
    ('The two stages of photosynthesis', subjects[1], 'Light-dependent reactions capture solar energy and store it in ATP and NADPH. The Calvin cycle uses that energy to build sugars.\n\nA way to remember it: capture first, build second.\n\nQuestion to explore: how does light intensity change the rate?'),
    ('Why binary search feels like magic', subjects[0], 'Each step halves the search space. Start with a sorted list, compare the middle element, and keep the half that could contain your target.'),
    ('Good design starts with a question', subjects[3], 'Before drawing a screen, understand what someone is trying to do. A clear question can save a lot of unnecessary complexity.'),
    ('Vectors: a quick mental model', subjects[2], 'Think of a vector as an arrow. Its length is the magnitude, and its orientation is the direction.'),
]
for title, subject, content in notes:
    Note.objects.create(user=user, subject=subject, title=title, content=content)
summary = ('### The big idea\nPlants transform **light** into chemical energy through photosynthesis.&#x20;\n\n'
           '### Two stages, working together\n1. **Light-dependent reactions** capture energy in ATP and NADPH.\n2. **The Calvin cycle** uses that energy to turn carbon dioxide into sugars.\n\n'
           '### What to remember\n* Chlorophyll absorbs the light.\n* Water and carbon dioxide go in; glucose and oxygen come out.\n'
           '* Light, temperature, and carbon dioxide availability can influence the rate.')
documents[0].ai_summary = summary
documents[0].save()
quiz = None
for index, doc in enumerate(documents[:3]):
    chunk = DocumentChunk.objects.create(document=doc, chunk_index=0, content=doc.extracted_text)
    payload = {'title': ['Photosynthesis: connect the dots', 'Algorithms: think it through', 'Design systems: the essentials'][index],
               'description': 'A little practice to connect the key ideas in your study material.', 'questions': [
                   {'text': 'What is the primary role of chlorophyll in photosynthesis?', 'choices': ['To absorb light energy', 'To break down glucose', 'To transport water', 'To release carbon dioxide'], 'correct_choice_index': 0, 'explanation': 'Chlorophyll absorbs light energy, which powers the light-dependent reactions.', 'difficulty': 'easy', 'source_chunk_ids': [chunk.pk]},
                   {'text': 'Where do the light-dependent reactions take place?', 'choices': ['In the nucleus', 'In the thylakoid membranes', 'In the cytoplasm', 'In the cell wall'], 'correct_choice_index': 1, 'explanation': 'The light-dependent reactions occur in the thylakoid membranes of chloroplasts.', 'difficulty': 'medium', 'source_chunk_ids': [chunk.pk]},
                   {'text': 'What does the Calvin cycle use to build sugars?', 'choices': ['Oxygen and water', 'Chlorophyll alone', 'ATP, NADPH, and carbon dioxide', 'Glucose and oxygen'], 'correct_choice_index': 2, 'explanation': 'The Calvin cycle uses energy stored in ATP and NADPH to fix carbon dioxide into sugars.', 'difficulty': 'medium', 'source_chunk_ids': [chunk.pk]},
               ]}
    # These are explicitly synthetic presentation fixtures; no provider is called.
    if index:
        payload['questions'] = [{**q, 'text': f'Practice question {i + 1} for {doc.title}', 'source_chunk_ids': [chunk.pk]} for i, q in enumerate(payload['questions'])]
    saved = QuizPersister().save(doc, user, payload, model_used='synthetic-ui-preview')
    if index == 0:
        quiz = saved
        answers = [{'question_id': q.pk, 'chosen_index': q.correct_choice_index, 'correct_index': q.correct_choice_index, 'is_correct': True} for q in saved.questions.all()]
        attempt = QuizAttempt.objects.create(user=user, quiz=saved, score=3, total_questions=3, answers=answers)
        ChatMessage.objects.create(user=user, document=doc, question='How do the two stages of photosynthesis work together?',
            answer='Think of it as **capture, then build**.&#x20;\n\n* **Capture:** Light-dependent reactions store energy from sunlight in ATP and NADPH.\n* **Build:** The Calvin cycle uses that energy to turn carbon dioxide into sugars.\n\nThe first stage supplies the energy; the second stage uses it to make food for the plant.',
            sources=[{'chunk_id': chunk.pk, 'chunk_index': 0, 'score': .87, 'content': chunk.content}])
    else:
        QuizAttempt.objects.create(user=user, quiz=saved, score=2, total_questions=3)
client = Client()
client.force_login(user)
pages = {'dashboard': '/', 'subjects': '/subjects/', 'subject-form': '/subjects/create/',
         'notes': '/notes/', 'note': f'/notes/{Note.objects.last().pk}/', 'note-form': '/notes/create/',
         'documents': '/documents/', 'upload': '/documents/upload/', 'document': f'/documents/{documents[0].pk}/',
         'qa': f'/ai/documents/{documents[0].pk}/qa/', 'quizzes': '/quizzes/',
         'quiz-detail': f'/quizzes/{quiz.pk}/', 'quiz': f'/quizzes/{quiz.pk}/take/',
         'result': f'/quizzes/attempts/{attempt.pk}/', 'profile': '/accounts/profile/'}
for name, url in pages.items():
    response = client.get(url)
    if response.status_code != 200:
        raise RuntimeError(f'{name}: {response.status_code}')
    html = response.content.decode()
    html = html.replace('/static/css/site.css', (BASE / 'static/css/site.css').as_uri())
    html = html.replace('/static/js/app.js', (BASE / 'static/js/app.js').as_uri())
    (preview / f'{name}.html').write_text(html)
client.logout()
for name, url in {'login': '/accounts/login/', 'register': '/accounts/register/'}.items():
    html = client.get(url).content.decode().replace('/static/css/site.css', (BASE / 'static/css/site.css').as_uri()).replace('/static/js/app.js', (BASE / 'static/js/app.js').as_uri())
    (preview / f'{name}.html').write_text(html)
print(f'Rendered {len(pages) + 2} pages from synthetic data in an isolated in-memory database: {preview}')
