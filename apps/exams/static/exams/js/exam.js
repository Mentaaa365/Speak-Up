document.addEventListener('DOMContentLoaded', () => {
    let questions = [];
    let currentIndex = 0;
    let userAnswers = [];
    let playCount = 0;
    let lastTranscript = "";

    const TTS_RATE = {A1: 0.85, A2: 1.0, B1: 1.0}[NIVEL] || 1.0;

    const questionCategory = document.getElementById('question-category');
    const questionText = document.getElementById('question-text');
    const optionsContainer = document.getElementById('options-container');
    const btnNext = document.getElementById('btn-next');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressPercentage = document.getElementById('progress-percentage');
    const inlineAlert = document.getElementById('inline-alert');

    const showInlineAlert = (msg) => {
        inlineAlert.textContent = '⚠️ ' + msg;
        inlineAlert.style.display = 'block';
        setTimeout(() => { inlineAlert.style.display = 'none'; }, 4000);
    };
    const btnTts = document.getElementById('btn-tts');
    const btnStt = document.getElementById('btn-stt');
    const sttFeedback = document.getElementById('stt-feedback');

    const STORAGE_KEY = 'exam_progress';

    const inicializar = () => {
        questions = PREGUNTAS;
        if (!questions || questions.length === 0) {
            questionText.textContent = 'No hay preguntas disponibles.';
            btnNext.style.display = 'none';
            return;
        }

        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                currentIndex = data.currentIndex || 0;
                userAnswers = data.answers || [];
            } catch (e) {
                currentIndex = 0;
                userAnswers = [];
            }
        }

        if (currentIndex >= questions.length) {
            localStorage.removeItem(STORAGE_KEY);
            currentIndex = 0;
            userAnswers = [];
        }

        loadQuestion();
    };

    // TTS engine with level-specific rate and 2-play cap
    const speakText = (text) => {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = TTS_RATE;
        window.speechSynthesis.speak(utterance);
    };

    btnTts.onclick = () => {
        if (playCount < 2) {
            speakText(questions[currentIndex].audioText);
            playCount++;
            if (playCount >= 2) {
                btnTts.disabled = true;
                btnTts.style.opacity = "0.5";
                btnTts.textContent = "🔊 Límite de reproducciones alcanzado";
            }
        }
    };

    // STT engine — continuous mode with live transcript
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
            btnStt.disabled   = false;
            btnStt.innerHTML  = '🔄 Try again';
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

    const loadQuestion = () => {
        const q = questions[currentIndex];

        const progress = (currentIndex / questions.length) * 100;
        progressBar.style.width = `${progress}%`;
        progressPercentage.textContent = `${Math.round(progress)}%`;
        progressText.textContent = `Pregunta ${currentIndex + 1} de ${questions.length}`;

        questionCategory.style.display = 'inline-block';
        questionCategory.textContent = q.type;
        questionText.innerHTML = q.text;

        optionsContainer.innerHTML = '';
        btnTts.style.display = 'none';
        btnTts.disabled = false;
        btnTts.style.opacity = "1";
        btnTts.innerHTML = "🔊 Escuchar Audio";

        btnStt.style.display = 'none';
        btnStt.innerHTML = "🎙️ Empezar a hablar";
        btnStt.disabled = false;

        sttFeedback.style.display = 'none';
        sttFeedback.innerHTML = '';

        playCount             = 0;
        lastTranscript        = '';
        accumulatedTranscript = '';
        if (currentRecognition) { try { currentRecognition.stop(); } catch (_) {} currentRecognition = null; }

        if (q.type === 'CHOICE' || q.type === 'LISTENING') {
            optionsContainer.style.display = 'grid';
            q.options.forEach(opt => {
                const label = document.createElement('label');
                label.style.cssText = "display: flex; align-items: center; gap: 16px; padding: 18px; border: 2px solid var(--g200); border-radius: 12px; cursor: pointer; transition: all 0.2s ease;";
                label.innerHTML = `
                    <input type="radio" name="answer" value="${opt.id}" style="width: 20px; height: 20px; accent-color: var(--primary);">
                    <span style="font-size: 15px; color: var(--g800);">${opt.text}</span>
                `;
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

    btnNext.addEventListener('click', () => {
        const q = questions[currentIndex];
        let answerToSave = "";

        if (q.type === 'WRITING') {
            const textarea = document.getElementById('writing-answer');
            if (!textarea || !textarea.value.trim()) return showInlineAlert("Please write your answer before continuing.");
            answerToSave = textarea.value.trim();
        } else if (q.type === 'SPEAKING') {
            if (!lastTranscript) return showInlineAlert("Please record your answer using the microphone.");
            answerToSave = lastTranscript;
        } else {
            const selected = document.querySelector('input[name="answer"]:checked');
            if (!selected) return showInlineAlert("Please select an option before continuing.");
            answerToSave = selected.value;
        }

        userAnswers.push({
            questionId: q.id,
            type: q.type,
            answer: answerToSave,
            optionId: (q.type !== 'SPEAKING' && q.type !== 'WRITING') ? answerToSave : '',
            targetPhrase: q.targetPhrase || '',
        });

        currentIndex++;

        if (currentIndex < questions.length) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                currentIndex: currentIndex,
                answers: userAnswers,
            }));
            loadQuestion();
        } else {
            btnNext.disabled = true;
            btnNext.textContent = "Evaluando...";

            localStorage.removeItem(STORAGE_KEY);

            const form = document.createElement('form');
            form.method = 'POST';
            form.action = POST_URL;

            const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = csrfTokenElement ? csrfTokenElement.value : '';
            form.appendChild(csrfInput);

            const dataInput = document.createElement('input');
            dataInput.type = 'hidden';
            dataInput.name = 'answers_data';
            dataInput.value = JSON.stringify(userAnswers);
            form.appendChild(dataInput);

            document.body.appendChild(form);
            form.submit();
        }
    });

    inicializar();
});
