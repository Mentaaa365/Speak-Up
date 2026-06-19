document.addEventListener('DOMContentLoaded', () => {
    if (!EJERCICIOS || EJERCICIOS.length === 0) {
        document.getElementById('prompt-text').textContent = 'No hay ejercicios disponibles.';
        return;
    }

    let currentIndex = 0;
    const totalExercises = EJERCICIOS.length;
    const completed = new Set();

    const promptText = document.getElementById('prompt-text');
    const indicator = document.getElementById('exercise-indicator');
    const textarea = document.getElementById('writing-input');
    const btnSubmit = document.getElementById('btn-submit');
    const btnNext = document.getElementById('btn-next');
    const feedbackPanel = document.getElementById('feedback-panel');

    const loadExercise = (index) => {
        currentIndex = index;
        const ex = EJERCICIOS[index];
        promptText.textContent = ex.prompt;
        indicator.textContent = `Ejercicio ${index + 1} de ${totalExercises}`;
        textarea.value = '';
        textarea.disabled = false;
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Evaluar respuesta';
        btnNext.style.display = (currentIndex < totalExercises - 1 || completed.size < totalExercises) ? 'none' : 'none';
        feedbackPanel.style.display = 'none';
    };

    const showFeedback = (data) => {
        feedbackPanel.style.display = 'block';
        document.getElementById('score-grammar').textContent = data.grammar ?? '-';
        document.getElementById('score-coherence').textContent = data.coherence ?? '-';
        document.getElementById('score-vocabulary').textContent = data.vocabulary ?? '-';

        const total = data.puntaje || 0;
        document.getElementById('score-total').textContent = `${total}/100`;
        const bar = document.getElementById('score-bar');
        bar.style.width = `${total}%`;
        bar.style.background = total >= 80 ? '#10B981' : '#F59E0B';

        document.getElementById('suggestions-text').textContent = data.suggestions || '-';

        if (data.pending) {
            document.getElementById('suggestions-text').textContent = data.suggestions;
            bar.style.background = '#9CA3AF';
        }

        if (data.aprobado) {
            completed.add(EJERCICIOS[currentIndex].id);
        }

        if (data.submodulo_completado) {
            btnNext.textContent = 'Volver al Dashboard';
            btnNext.style.display = 'inline-block';
            btnNext.onclick = () => { window.location.href = DASHBOARD_URL; };
        } else if (currentIndex < totalExercises - 1) {
            btnNext.textContent = 'Siguiente ejercicio →';
            btnNext.style.display = 'inline-block';
            btnNext.onclick = () => loadExercise(currentIndex + 1);
        } else if (!data.aprobado) {
            btnSubmit.textContent = 'Reintentar';
            btnSubmit.disabled = false;
            textarea.disabled = false;
        }
    };

    btnSubmit.addEventListener('click', () => {
        const text = textarea.value.trim();
        if (!text) return alert('Por favor, escribe tu respuesta antes de enviar.');

        btnSubmit.disabled = true;
        btnSubmit.textContent = 'Evaluando...';
        textarea.disabled = true;

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch(EVALUAR_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                ejercicio_id: EJERCICIOS[currentIndex].id,
                texto: text,
            }),
        })
        .then(r => r.json())
        .then(data => showFeedback(data))
        .catch(() => {
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Reintentar';
            textarea.disabled = false;
            alert('Error de conexión. Intenta nuevamente.');
        });
    });

    loadExercise(0);
});
