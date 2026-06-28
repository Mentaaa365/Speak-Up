document.addEventListener('DOMContentLoaded', () => {
    if (!EJERCICIOS || EJERCICIOS.length === 0) {
        document.getElementById('prompt-text').textContent = 'No exercises available.';
        return;
    }

    const totalExercises = EJERCICIOS.length;
    const completed = new Set();

    const _passedIds = (typeof PASSED_IDS !== 'undefined' && Array.isArray(PASSED_IDS)) ? PASSED_IDS : [];
    _passedIds.forEach(id => completed.add(id));

    const findNextPending = (afterIndex) => {
        for (let i = afterIndex + 1; i < totalExercises; i++) {
            if (!completed.has(EJERCICIOS[i].id)) return i;
        }
        for (let i = 0; i <= afterIndex; i++) {
            if (!completed.has(EJERCICIOS[i].id)) return i;
        }
        return -1;
    };

    let currentIndex = findNextPending(-1);
    if (currentIndex === -1) {
        showCompletionMessage(true);
        return;
    }

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
        indicator.textContent = `Ejercicio ${index + 1} de ${totalExercises} · ${completed.size} passed`;
        textarea.value = '';
        textarea.disabled = false;
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Submit answer';
        btnNext.style.display = 'none';
        feedbackPanel.style.display = 'none';
    };

    function showCompletionMessage(submoduloCompletado) {
        document.querySelector('#prompt-container').style.display = 'none';
        document.querySelector('#writing-input').style.display = 'none';
        btnSubmit.style.display = 'none';
        btnNext.style.display = 'none';
        feedbackPanel.style.display = 'none';

        indicator.textContent = `${totalExercises} de ${totalExercises} passed`;

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'text-align:center; padding:40px 20px;';

        const nextUrl = (typeof MI_NIVEL_URL !== 'undefined') ? MI_NIVEL_URL : DASHBOARD_URL;

        if (submoduloCompletado) {
            wrapper.innerHTML =
                '<p style="font-size:22px; font-weight:800; color:#10B981; margin:0 0 8px 0;">🎉 Submodule completed!</p>' +
                '<p style="font-size:14px; color:#6B7280; margin:0 0 20px 0;">You passed all writing exercises.</p>' +
                '<a href="' + nextUrl + '" style="display:inline-block; padding:12px 28px; border-radius:10px; background:var(--primary); color:#FFFFFF; font-size:15px; font-weight:700; text-decoration:none; margin-right:12px;">Next submodule</a>' +
                '<a href="' + DASHBOARD_URL + '" style="display:inline-block; padding:12px 28px; border-radius:10px; background:var(--g200); color:var(--g700); font-size:15px; font-weight:700; text-decoration:none;">Back to Dashboard</a>';
        } else {
            wrapper.innerHTML =
                '<p style="font-size:22px; font-weight:800; color:var(--primary); margin:0 0 8px 0;">✅ Exercises completed!</p>' +
                '<p style="font-size:14px; color:#6B7280; margin:0 0 20px 0;">You completed all available exercises.</p>' +
                '<a href="' + DASHBOARD_URL + '" style="display:inline-block; padding:12px 28px; border-radius:10px; background:var(--primary); color:#FFFFFF; font-size:15px; font-weight:700; text-decoration:none;">Back to Dashboard</a>';
        }

        document.querySelector('#prompt-container').parentNode.appendChild(wrapper);
    }

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
            indicator.textContent = `Ejercicio ${currentIndex + 1} de ${totalExercises} · ${completed.size} passed`;
        }

        if (completed.size >= totalExercises) {
            btnNext.textContent = '🎉 Submodule completed';
            btnNext.style.display = 'inline-block';
            btnNext.onclick = () => showCompletionMessage(data.submodulo_completado);
        } else {
            const next = findNextPending(currentIndex);
            if (next !== -1 && data.aprobado) {
                btnNext.textContent = 'Next exercise';
                btnNext.style.display = 'inline-block';
                btnNext.onclick = () => loadExercise(next);
            } else if (!data.aprobado) {
                btnSubmit.textContent = 'Retry';
                btnSubmit.disabled = false;
                textarea.disabled = false;
            }
        }
    };

    btnSubmit.addEventListener('click', () => {
        const text = textarea.value.trim();
        if (!text) return alert('Please write your answer before submitting.');

        btnSubmit.disabled = true;
        btnSubmit.textContent = 'Evaluating...';
        textarea.disabled = true;

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetchWithRetry(EVALUAR_URL, {
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
            btnSubmit.textContent = 'Retry';
            textarea.disabled = false;
            alert('Connection error. Try again.');
        });
    });

    loadExercise(currentIndex);
});
