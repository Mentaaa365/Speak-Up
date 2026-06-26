document.addEventListener('DOMContentLoaded', () => {
    // 1. VARIABLES GLOBALES
    let questions = [];
    let currentIndex = 0;

    // Stores exact answers (or transcripts) to send to the backend
    let userAnswers = [];

    // Control variables
    let playCount = 0;
    let lastTranscript = "";

    // Timer state
    let secondsLeft   = DIAGNOSIS_TIMEOUT_SECONDS;
    let timerInterval = null;
    const timerEl     = document.getElementById('diagnosis-timer');

    // DOM elements
    const questionCategory = document.getElementById('question-category');
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    const btnNext = document.getElementById('btn-next');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressPercentage = document.getElementById('progress-percentage');

    const btnTts = document.getElementById('btn-tts');
    const btnStt = document.getElementById('btn-stt');
    const sttFeedback = document.getElementById('stt-feedback');

    // ── TIMER HELPERS ──────────────────────────────────────────────────────────

    const formatTime = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    };

    const expireDiagnostic = () => {
        clearInterval(timerInterval);
        // Fill all unanswered questions with empty answers (Opción B)
        const answered = new Set(userAnswers.map(a => a.questionId));
        questions.forEach(q => {
            if (!answered.has(q.id)) {
                userAnswers.push({
                    questionId:   q.id,
                    type:         q.type,
                    answer:       '',
                    optionId:     '',
                    targetPhrase: q.targetPhrase || '',
                });
            }
        });
        submitDiagnostic(userAnswers);
    };

    const startTimer = () => {
        timerEl.textContent = formatTime(secondsLeft);
        timerInterval = setInterval(() => {
            secondsLeft--;
            timerEl.textContent = formatTime(secondsLeft);
            if (secondsLeft <= 300) {
                timerEl.style.color = 'var(--danger)';
            }
            if (secondsLeft <= 0) {
                expireDiagnostic();
            }
        }, 1000);
    };

    // ── FORM SUBMISSION ────────────────────────────────────────────────────────

    const submitDiagnostic = (answers) => {
        clearInterval(timerInterval);
        localStorage.removeItem('diagnostic_progress');

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/diagnosis/results/';

        const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfTokenElement ? csrfTokenElement.value : '';
        form.appendChild(csrfInput);

        const dataInput = document.createElement('input');
        dataInput.type = 'hidden';
        dataInput.name = 'answers_data';
        dataInput.value = JSON.stringify(answers);
        form.appendChild(dataInput);

        document.body.appendChild(form);
        form.submit();
    };

    // 2. INITIALIZATION AND LOCAL CACHE RECOVERY
    const inicializarExamen = () => {
        const savedProgress = localStorage.getItem('diagnostic_progress');
        if (savedProgress) {
            const data = JSON.parse(savedProgress);
            currentIndex = data.currentIndex;
            userAnswers = data.answers;
        }
        cargarPreguntasDesdeBD();
    };

    const cargarPreguntasDesdeBD = () => {
        fetch('/diagnosis/api/get-questions/')
            .then(response => response.json())
            .then(data => {
                questions = data.questions;
                if (currentIndex >= questions.length) {
                    // Cache index out of bounds — reset
                    localStorage.removeItem('diagnostic_progress');
                    currentIndex = 0;
                    userAnswers = [];
                }
                loadQuestion();
                startTimer();
            })
            .catch(error => {
                console.error("Error al cargar:", error);
                alert("Error al conectar con la base de datos.");
            });
    };

    // 3. TTS ENGINE (limit of 2 plays)
    const speakText = (text) => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
    };

    btnTts.onclick = () => {
        if (playCount < 2) {
            speakText(questions[currentIndex].audioText);
            playCount++;
            if (playCount >= 2) {
                btnTts.disabled = true;
                btnTts.style.opacity = "0.5";
                btnTts.textContent = "🔊 Playback limit reached";
            }
        }
    };

    // 4. STT ENGINE — continuous mode with live transcript
    let accumulatedTranscript = '';
    let currentRecognition    = null;
    let sttRetries            = 0;
    const MAX_STT_RETRIES     = 3;

    const _sttError = (code) => {
        if (code === 'not-allowed') return 'Microphone access denied. Enable it in browser settings.';
        if (code === 'network')     return 'Voice service unavailable. Check your connection.';
        return 'Microphone error. Try again.';
    };

    const _updateLive = (text) => {
        sttFeedback.style.display = 'block';
        sttFeedback.innerHTML = text
            ? `<em style="color:var(--g700);">${text}</em>`
            : `<span style="color:var(--secondary);font-weight:700;">Listening… 🎙️</span>`;
    };

    const _launchSTT = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang            = 'en-US';
        recognition.continuous      = true;
        recognition.interimResults  = true;
        recognition.maxAlternatives = 1;
        currentRecognition = recognition;

        const safetyTimer = setTimeout(() => {
            if (currentRecognition) { currentRecognition.stop(); currentRecognition = null; }
        }, 10000);

        recognition.onresult = (event) => {
            let interim = '';
            let final   = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) final += t + ' ';
                else interim += t;
            }
            if (final) accumulatedTranscript += final;
            _updateLive((accumulatedTranscript + interim).trim());
        };

        recognition.onerror = (e) => {
            clearTimeout(safetyTimer);
            if ((e.error === 'network' || e.error === 'aborted') && sttRetries < MAX_STT_RETRIES) {
                sttRetries++;
                setTimeout(() => { if (btnStt.disabled) _launchSTT(); }, 300);
                return;
            }
            if (e.error === 'no-speech') return;
            currentRecognition = null;
            btnStt.disabled    = false;
            const msg = _sttError(e.error);
            if (msg) sttFeedback.innerHTML = `<p style="color:var(--danger);font-size:13px;font-weight:600;">${msg}</p>`;
        };

        recognition.onend = () => {
            clearTimeout(safetyTimer);
            currentRecognition = null;
            if (!accumulatedTranscript.trim()) { btnStt.disabled = false; return; }
            lastTranscript = accumulatedTranscript.trim();
            sttFeedback.innerHTML = `Your recorded answer: <b>"${lastTranscript}"</b>`;
            btnStt.disabled  = false;
            btnStt.innerHTML = '🔄 Try again';
        };

        recognition.start();
    };

    const startListening = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            sttFeedback.style.display = 'block';
            sttFeedback.innerHTML = '<p style="color:var(--danger);font-size:13px;">Your browser does not support speech recognition. Use Chrome or Edge.</p>';
            return;
        }
        if (currentRecognition) { currentRecognition.stop(); currentRecognition = null; return; }
        accumulatedTranscript = '';
        sttRetries            = 0;
        btnStt.disabled       = true;
        _updateLive('');
        _launchSTT();
    };

    btnStt.onclick = startListening;

    // 5. RENDER QUESTION
    const loadQuestion = () => {
        const q = questions[currentIndex];

        // Update progress bar
        const progress = (currentIndex / questions.length) * 100;
        progressBar.style.width = `${progress}%`;
        progressPercentage.textContent = `${Math.round(progress)}%`;
        progressText.textContent = `Question ${currentIndex + 1} of ${questions.length}`;

        // Clear previous state
        questionCategory.style.display = 'inline-block';
        questionCategory.textContent = q.type;
        questionText.innerHTML = q.text;

        optionsContainer.innerHTML = '';
        btnTts.style.display = 'none';
        btnTts.disabled = false;
        btnTts.style.opacity = "1";
        btnTts.innerHTML = "🔊 Listen to audio";

        btnStt.style.display = 'none';
        btnStt.innerHTML = "🎙️ Speak your answer";
        btnStt.disabled = false;

        sttFeedback.style.display = 'none';
        sttFeedback.innerHTML = '';

        playCount             = 0;
        lastTranscript        = '';
        accumulatedTranscript = '';
        if (currentRecognition) { try { currentRecognition.stop(); } catch (_) {} currentRecognition = null; }

        // Render elements based on question type
        if (q.type === 'CHOICE' || q.type === 'LISTENING') {
            optionsContainer.style.display = 'grid';
            q.options.forEach(opt => {
                const label = document.createElement('label');
                label.style.cssText = "display: flex; align-items: center; gap: 16px; padding: 18px; border: 2px solid var(--g200); border-radius: 12px; cursor: pointer; transition: all 0.2s ease;";
                label.innerHTML = `
                    <input type="radio" name="answer" value="${opt.id}" style="width: 20px; height: 20px; accent-color: var(--primary);">
                    <span style="font-size: 15px; color: var(--g800);">${opt.text}</span>
                `;
                // Visual highlight on selection
                label.addEventListener('click', () => {
                    document.querySelectorAll('#options-container label').forEach(l => l.style.borderColor = 'var(--g200)');
                    label.style.borderColor = 'var(--primary)';
                });
                optionsContainer.appendChild(label);
            });

            if (q.type === 'LISTENING') {
                btnTts.style.display = 'inline-flex';
            }
        } else if (q.type === 'SPEAKING') {
            optionsContainer.style.display = 'none';
            btnStt.style.display = 'inline-flex';
        } else if (q.type === 'WRITING') {
            optionsContainer.style.display = 'block';
            optionsContainer.innerHTML = `
                <textarea id="writing-answer" rows="6" placeholder="Write your answer in English..."
                    style="width: 100%; padding: 16px; border: 2px solid var(--g200); border-radius: 12px;
                    font-size: 15px; font-family: inherit; resize: vertical; box-sizing: border-box;"></textarea>
            `;
        }
    };

    // 6. NAVIGATION AND SAFE SUBMISSION
    btnNext.addEventListener('click', () => {
        const q = questions[currentIndex];
        let answerToSave = "";

        if (q.type === 'WRITING') {
            const textarea = document.getElementById('writing-answer');
            if (!textarea || !textarea.value.trim()) return alert("Por favor, escribe tu respuesta para continuar.");
            answerToSave = textarea.value.trim();
        } else if (q.type === 'SPEAKING') {
            if (!lastTranscript) return alert("Por favor, graba tu respuesta usando el micrófono.");
            answerToSave = lastTranscript;
        } else {
            const selected = document.querySelector('input[name="answer"]:checked');
            if (!selected) return alert("Por favor, selecciona una opción para continuar.");
            answerToSave = selected.value;
        }

        userAnswers.push({
            questionId:   q.id,
            type:         q.type,
            answer:       answerToSave,
            optionId:     (q.type !== 'SPEAKING' && q.type !== 'WRITING') ? answerToSave : '',
            targetPhrase: q.targetPhrase || '',
        });

        // Advance to next question
        currentIndex++;

        if (currentIndex < questions.length) {
            localStorage.setItem('diagnostic_progress', JSON.stringify({
                currentIndex: currentIndex,
                answers: userAnswers
            }));
            loadQuestion();
        } else {
            // TEST FINISHED
            btnNext.disabled = true;
            btnNext.textContent = "Evaluando...";
            submitDiagnostic(userAnswers);
        }
    });

    // Boot
    inicializarExamen();
});
