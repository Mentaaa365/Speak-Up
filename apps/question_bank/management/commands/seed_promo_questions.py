from django.core.management.base import BaseCommand

from apps.curriculum.models import NivelMCER
from apps.question_bank.models import Option, Question

QUESTIONS = {
    'SPEAKING': [
        ('Introduce yourself briefly.', 'My name is {name} and I am a student.'),
        ('Describe your daily routine.', 'I wake up early and go to school every day.'),
        ('Talk about your favorite hobby.', 'My favorite hobby is reading books.'),
        ('Describe your hometown.', 'My hometown is a small and peaceful city.'),
        ('Talk about a recent trip.', 'Last weekend I visited a museum with my family.'),
    ],
    'LISTENING': [
        'Listen and identify the main topic of the conversation.',
        'What time does the event start according to the audio?',
        'Where does the speaker say the meeting will take place?',
        'What problem does the speaker mention?',
        'What solution does the speaker suggest?',
    ],
    'CHOICE': [
        ('Which sentence is grammatically correct?', 'She goes to school every day.', 'She go to school every day.', 'She going to school every day.', 'She goed to school every day.'),
        ('Choose the correct past tense form of "go".', 'went', 'goed', 'going', 'goes'),
        ('Select the appropriate preposition: "I am interested ___ music."', 'in', 'on', 'at', 'by'),
        ('Which word means the opposite of "ancient"?', 'modern', 'old', 'antique', 'historical'),
        ('Complete: "If I ___ you, I would study more."', 'were', 'was', 'am', 'be'),
        ('Choose the correct article: "___ umbrella is on the table."', 'An', 'A', 'The', 'Some'),
        ('Which sentence uses the present perfect correctly?', 'I have visited Paris twice.', 'I visited Paris twice yesterday.', 'I am visiting Paris twice.', 'I was visiting Paris twice.'),
        ('Select the correct comparative: "This exercise is ___ than the last one."', 'harder', 'more hard', 'hardest', 'most hard'),
        ('What does "to postpone" mean?', 'to delay to a later time', 'to cancel permanently', 'to move forward', 'to repeat again'),
        ('Choose the correct passive voice: "The letter ___ yesterday."', 'was written', 'wrote', 'has written', 'is writing'),
    ],
}


class Command(BaseCommand):
    help = 'Seed promotion exam questions for all MCER levels (idempotent)'

    def handle(self, *args, **options):
        niveles = NivelMCER.objects.all()
        created_total = 0

        for nivel in niveles:
            codigo = nivel.codigo

            for i, (text, target) in enumerate(QUESTIONS['SPEAKING']):
                _, created = Question.objects.get_or_create(
                    level=codigo,
                    question_type='SPEAKING',
                    bank_context='PROMOTION_EXAM',
                    text=text,
                    defaults={'target_phrase': target},
                )
                if created:
                    created_total += 1

            for text in QUESTIONS['LISTENING']:
                lq, created = Question.objects.get_or_create(
                    level=codigo,
                    question_type='LISTENING',
                    bank_context='PROMOTION_EXAM',
                    text=text,
                )
                if created:
                    created_total += 1
                    Option.objects.get_or_create(question=lq, text='Option A — correct answer', defaults={'is_correct': True})
                    Option.objects.get_or_create(question=lq, text='Option B', defaults={'is_correct': False})
                    Option.objects.get_or_create(question=lq, text='Option C', defaults={'is_correct': False})

            for row in QUESTIONS['CHOICE']:
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

        if options['verbosity'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f'Done. Created {created_total} new questions '
                f'({Question.objects.filter(bank_context="PROMOTION_EXAM").count()} total).'
            ))
