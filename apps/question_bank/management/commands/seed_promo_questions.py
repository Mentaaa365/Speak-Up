from django.core.management.base import BaseCommand

from apps.curriculum.models import NivelMCER
from apps.question_bank.models import Option, Question

QUESTIONS = {
    "A1": {
        "SPEAKING": [
            ("Say hello and introduce yourself.", "Hello my name is John and I am a student"),
            ("Say where you are from.", "I am from Ecuador it is a beautiful country"),
            ("Describe your family.", "I have one sister and one brother"),
            ("Say what you like to eat.", "My favorite food is rice and chicken"),
            ("Describe your daily routine.", "I wake up at seven and go to school"),
        ],
        "LISTENING": [
            {
                "text": "Listen and select the correct greeting.",
                "audio_text": "Good morning, how are you today?",
                "options": [
                    ("Good morning, how are you today?", True),
                    ("Good night, see you tomorrow.", False),
                    ("Good afternoon, nice to meet you.", False),
                ],
            },
            {
                "text": "Listen and select what the speaker likes.",
                "audio_text": "I like to play soccer with my friends.",
                "options": [
                    ("Playing soccer", True),
                    ("Playing tennis", False),
                    ("Playing basketball", False),
                ],
            },
            {
                "text": "Listen and select the correct number.",
                "audio_text": "I have three dogs at home.",
                "options": [
                    ("Three", True),
                    ("Two", False),
                    ("Four", False),
                ],
            },
            {
                "text": "Listen and select where the speaker lives.",
                "audio_text": "I live in a small house near the park.",
                "options": [
                    ("Near the park", True),
                    ("Near the school", False),
                    ("Near the hospital", False),
                ],
            },
            {
                "text": "Listen and select the speaker's favorite color.",
                "audio_text": "My favorite color is blue because it reminds me of the sky.",
                "options": [
                    ("Blue", True),
                    ("Red", False),
                    ("Green", False),
                ],
            },
        ],
        "CHOICE": [
            ("Choose the correct option: 'I _____ a student.'", "am", "is", "are", "be"),
            ("Choose the correct option: 'She _____ to school every day.'", "goes", "go", "going", "goed"),
            ("Choose the correct option: '_____ is your name?'", "What", "Where", "When", "Who"),
            ("Choose the correct option: 'I have _____ sister.'", "one", "a one", "the one", "an"),
            ("Choose the correct option: 'They _____ playing in the park.'", "are", "is", "am", "be"),
            ("Choose the correct option: 'My mother _____ at the hospital.'", "works", "work", "working", "to work"),
            ("Choose the correct option: 'I _____ up at seven every morning.'", "wake", "wakes", "waking", "waked"),
        ],
    },
    "A2": {
        "SPEAKING": [
            ("Describe what you did yesterday.", "Yesterday I went to the store and bought some groceries"),
            ("Talk about your best friend.", "My best friend is Maria she is very kind and funny"),
            ("Describe your favorite place.", "My favorite place is the beach because it is relaxing"),
            ("Talk about your last vacation.", "Last summer I traveled to the coast with my family"),
            ("Describe your school or work.", "I study software engineering at the university"),
        ],
        "LISTENING": [
            {
                "text": "Listen and select what the speaker did last weekend.",
                "audio_text": "Last weekend I visited my grandparents in the countryside.",
                "options": [
                    ("Visited grandparents", True),
                    ("Went to the cinema", False),
                    ("Stayed at home", False),
                ],
            },
            {
                "text": "Listen and select the problem the speaker mentions.",
                "audio_text": "I missed the bus this morning so I had to walk to school.",
                "options": [
                    ("Missed the bus", True),
                    ("Lost the keys", False),
                    ("Forgot the homework", False),
                ],
            },
            {
                "text": "Listen and select the speaker's plan.",
                "audio_text": "Next month I am going to start learning French.",
                "options": [
                    ("Start learning French", True),
                    ("Start learning German", False),
                    ("Start learning Italian", False),
                ],
            },
            {
                "text": "Listen and select how often the speaker exercises.",
                "audio_text": "I usually go to the gym three times a week.",
                "options": [
                    ("Three times a week", True),
                    ("Every day", False),
                    ("Once a month", False),
                ],
            },
            {
                "text": "Listen and select what the speaker recommends.",
                "audio_text": "You should try the pasta at that restaurant, it is delicious.",
                "options": [
                    ("The pasta at a restaurant", True),
                    ("The pizza at a cafe", False),
                    ("The salad at a hotel", False),
                ],
            },
        ],
        "CHOICE": [
            ("Complete: 'I _____ to the cinema last night.'", "went", "go", "gone", "going"),
            ("Complete: 'She is _____ than her brother.'", "taller", "more tall", "tallest", "tall"),
            ("Complete: 'We have lived here _____ 2020.'", "since", "for", "during", "ago"),
            ("Complete: 'If it rains, I _____ stay home.'", "will", "would", "am", "did"),
            ("Complete: 'He was _____ when I called him.'", "sleeping", "sleep", "slept", "sleeps"),
            ("Complete: 'I do not have _____ money.'", "any", "some", "many", "a lot"),
            ("Complete: 'Could you speak _____, please?'", "more slowly", "slow", "slower much", "most slow"),
        ],
    },
    "B1": {
        "SPEAKING": [
            ("Give your opinion about social media.", "I think social media has both advantages and disadvantages for young people"),
            ("Describe a challenge you overcame.", "Last year I had to give a presentation in English and I was very nervous but I practiced a lot"),
            ("Talk about the importance of education.", "Education is essential because it helps people develop critical thinking skills"),
            ("Describe how technology changed your life.", "Technology has completely changed the way I communicate with my friends and family"),
            ("Talk about your plans for the future.", "After I graduate I would like to work as a software engineer in a big company"),
        ],
        "LISTENING": [
            {
                "text": "Listen and select the main conclusion.",
                "audio_text": "According to recent studies, regular exercise significantly reduces stress levels and improves mental health.",
                "options": [
                    ("Exercise reduces stress and improves mental health", True),
                    ("Exercise causes more stress", False),
                    ("Mental health is not affected by exercise", False),
                ],
            },
            {
                "text": "Listen and select the speaker's opinion.",
                "audio_text": "To be perfectly honest, I find the new education policy completely counterproductive.",
                "options": [
                    ("The speaker disagrees with the policy", True),
                    ("The speaker supports the policy", False),
                    ("The speaker is neutral about the policy", False),
                ],
            },
            {
                "text": "Listen and select the condition mentioned.",
                "audio_text": "Provided that all requirements are met, the contract will be signed next week.",
                "options": [
                    ("All requirements must be met first", True),
                    ("The contract was already signed", False),
                    ("There are no conditions to meet", False),
                ],
            },
            {
                "text": "Listen and select what the speaker implies.",
                "audio_text": "If I had known about the delay, I would have taken a different route.",
                "options": [
                    ("The speaker did not know about the delay", True),
                    ("The speaker knew about the delay", False),
                    ("The speaker caused the delay", False),
                ],
            },
            {
                "text": "Listen and select the suggestion.",
                "audio_text": "Perhaps we should reconsider our approach before presenting to the board of directors.",
                "options": [
                    ("Reconsider the approach", True),
                    ("Present immediately", False),
                    ("Cancel the presentation", False),
                ],
            },
        ],
        "CHOICE": [
            ("Select: 'By the time we arrived, the show _____.'", "had started", "has started", "started", "starts"),
            ("Select: 'I wish I _____ speak French fluently.'", "could", "can", "will", "am able to"),
            ("Select: 'The car _____ was stolen has been found.'", "which", "who", "whom", "whose"),
            ("Select: 'He apologized for _____ late.'", "being", "be", "to be", "been"),
            ("Select: 'Not only _____ he arrive late, but he also forgot the report.'", "did", "had", "was", "has"),
            ("Select: 'She managed to _____ the problem without help.'", "solve", "solving", "have solved", "solved"),
            ("Select: 'Had I known, I _____ a different decision.'", "would have made", "would make", "made", "had made"),
        ],
    },
}


class Command(BaseCommand):
    help = 'Seed promotion exam questions for all MCER levels (idempotent)'

    def handle(self, *args, **options):
        created_total = 0

        for nivel in NivelMCER.objects.all():
            codigo = nivel.codigo
            level_data = QUESTIONS.get(codigo)
            if not level_data:
                continue

            for text, target in level_data['SPEAKING']:
                _, created = Question.objects.get_or_create(
                    level=codigo,
                    question_type='SPEAKING',
                    bank_context='PROMOTION_EXAM',
                    text=text,
                    defaults={'target_phrase': target},
                )
                if created:
                    created_total += 1

            for item in level_data['LISTENING']:
                lq, created = Question.objects.get_or_create(
                    level=codigo,
                    question_type='LISTENING',
                    bank_context='PROMOTION_EXAM',
                    text=item['text'],
                    defaults={'audio_text': item['audio_text']},
                )
                if created:
                    created_total += 1
                    for opt_text, is_correct in item['options']:
                        Option.objects.get_or_create(
                            question=lq,
                            text=opt_text,
                            defaults={'is_correct': is_correct},
                        )

            for row in level_data['CHOICE']:
                text, correct, *wrongs = row
                cq, created = Question.objects.get_or_create(
                    level=codigo,
                    question_type='CHOICE',
                    bank_context='PROMOTION_EXAM',
                    text=text,
                )
                if created:
                    created_total += 1
                    Option.objects.get_or_create(question=cq, text=correct, defaults={'is_correct': True})
                    for wrong in wrongs:
                        Option.objects.get_or_create(question=cq, text=wrong, defaults={'is_correct': False})

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created {created_total} new questions '
            f'({Question.objects.filter(bank_context="PROMOTION_EXAM").count()} total).'
        ))
