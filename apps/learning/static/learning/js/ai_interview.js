/**
 * ai_interview.js — Browser engine for the RF-05 AI oral interview.
 *
 * Globals injected by ai_interview.html:
 *   SESION_ID, NIVEL_CODIGO, TTS_RATE, TIEMPO_RESPUESTA, TURNO_URL, FINALIZAR_URL
 *
 * Flow:
 *   1. User clicks "Start interview" -> POST TURNO_URL (empty historial) -> agent's opening question
 *   2. TTS speaks the question; STT auto-starts after TTS ends
 *   3. Countdown runs; auto-submits at 0, or user clicks "Finalizar respuesta"
 *   4. POST TURNO_URL with transcript + historial -> agent reply -> TTS -> STT loop
 *   5. "Finalizar entrevista" appears after first student exchange
 *   6. User clicks it -> POST FINALIZAR_URL -> show scores panel
 */

document.addEventListener('DOMContentLoaded', () => {

    // ─── Globals validation ───────────────────────────────────────────────────
    const REQUIRED = ['SESION_ID', 'NIVEL_CODIGO', 'TTS_RATE', 'TIEMPO_RESPUESTA', 'TURNO_URL', 'FINALIZAR_URL'];
    for (const key of REQUIRED) {
        if (typeof window[key] === 'undefined') {
            console.warn(`ai_interview.js: global ${key} not found. Aborting.`);
            return;
        }
    }

    // ─── State ────────────────────────────────────────────────────────────────
    let historial          = [];
    let currentTranscript  = '';
    let isRecording        = false;
    let isBusy             = false;
    let interviewFinished  = false;
    let completedExchanges = 0;
    let countdownInterval  = null;
    let recognition        = null;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    // ─── DOM refs ─────────────────────────────────────────────────────────────
    const chatContainer      = document.getElementById('chat-container');
    const chatPlaceholder    = document.getElementById('chat-placeholder');
    const countdownEl        = document.getElementById('countdown');
    const transcripcionEl    = document.getElementById('transcripcion-display');
    const recordBtn          = document.getElementById('record-btn');
    const recordBtnIcon      = document.getElementById('record-btn-icon');
    const recordBtnLabel     = document.getElementById('record-btn-label');
    const turnActions        = document.getElementById('turn-actions');
    const regrabarBtn        = document.getElementById('regrabar-btn');
    const submitTurnBtn      = document.getElementById('submit-turn-btn');
    const finalizarBtn       = document.getElementById('finalizar-btn');
    const resultadoPanel     = document.getElementById('resultado-panel');
    const puntajeDisplay     = document.getElementById('puntaje-display');
    const aprobadoLabel      = document.getElementById('aprobado-label');
    const scoresDetail       = document.getElementById('scores-detail');
    const sugerenciasDisplay = document.getElementById('sugerencias-display');
    const sugerenciasText    = document.getElementById('sugerencias-text');
    const examenNotice       = document.getElementById('examen-notice');
    const errorPanel         = document.getElementById('error-panel');
    const errorMsg           = document.getElementById('error-msg');
    const hintBox            = document.getElementById('hint-box');

    // ─── CSRF ─────────────────────────────────────────────────────────────────
    const getCsrf = () =>
        document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    // ─── Error display ────────────────────────────────────────────────────────
    const showError = (msg) => {
        errorPanel.style.display = 'block';
        errorMsg.textContent     = msg;
    };

    const hideError = () => {
        errorPanel.style.display = 'none';
    };

    // ─── Markdown cleanup ──────────────────────────────────────────────────────
    const stripMarkdown = (text) =>
        text.replace(/[*_#`~>]+/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').trim();

    // ─── Chat bubbles ─────────────────────────────────────────────────────────
    const appendMessage = (role, text) => {
        text = stripMarkdown(text);
        if (chatPlaceholder) chatPlaceholder.style.display = 'none';
        const bubble  = document.createElement('div');
        const isAgent = role === 'assistant';
        bubble.style.cssText = [
            'padding: 10px 14px',
            'border-radius: 10px',
            'font-size: 14px',
            'line-height: 1.5',
            'max-width: 85%',
            `align-self: ${isAgent ? 'flex-start' : 'flex-end'}`,
            `background: ${isAgent ? 'var(--primary-light)' : 'var(--secondary-light)'}`,
            `color: ${isAgent ? 'var(--primary)' : 'var(--secondary)'}`,
            'font-weight: 600',
        ].join('; ');
        bubble.textContent = text;
        chatContainer.appendChild(bubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    // ─── TTS ──────────────────────────────────────────────────────────────────
    const speak = (text, onEnd) => {
        window.speechSynthesis.cancel();
        const utter   = new SpeechSynthesisUtterance(stripMarkdown(text));
        utter.lang    = 'en-US';
        utter.rate    = TTS_RATE;
        utter.pitch   = 1.0;
        const voices  = window.speechSynthesis.getVoices();
        const enVoice = voices.find(v => v.lang.startsWith('en') && v.localService)
                     || voices.find(v => v.lang.startsWith('en'));
        if (enVoice) utter.voice = enVoice;
        if (onEnd) utter.onend = onEnd;
        window.speechSynthesis.speak(utter);
    };

    // ─── Countdown timer ──────────────────────────────────────────────────────
    const startCountdown = () => {
        stopCountdown();
        let timeLeft = TIEMPO_RESPUESTA;
        countdownEl.textContent = `${timeLeft}s`;
        countdownEl.style.color = 'var(--primary)';

        countdownInterval = setInterval(() => {
            timeLeft--;
            if (timeLeft < 0) timeLeft = 0;
            countdownEl.textContent = `${timeLeft}s`;
            if (timeLeft <= 10) countdownEl.style.color = 'var(--danger)';
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                countdownInterval = null;
                if (isRecording && !isBusy) pauseForReview();
            }
        }, 1000);
    };

    const stopCountdown = () => {
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
        countdownEl.textContent = `${TIEMPO_RESPUESTA}s`;
        countdownEl.style.color = 'var(--primary)';
    };

    // ─── STT (continuous, interim results) ───────────────────────────────────
    const startSTT = () => {
        if (!SpeechRecognition) {
            showError('Your browser does not support speech recognition. Use Chrome or Edge.');
            return;
        }
        if (isRecording || interviewFinished) return;

        currentTranscript = '';
        transcripcionEl.innerHTML = '<span style="color:var(--g400);">Listening...</span>';
        isRecording = true;
        _setRecordingUI(true);

        recognition                 = new SpeechRecognition();
        recognition.lang            = 'en-US';
        recognition.interimResults  = true;
        recognition.continuous      = true;
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => {
            let interim = '';
            let final   = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) final += t + ' ';
                else interim += t;
            }
            if (final) currentTranscript += final;
            transcripcionEl.textContent = (currentTranscript + interim).trim() || '…';
        };

        let sttRetries = 0;
        recognition.onerror = (e) => {
            if (e.error === 'no-speech') return;
            if ((e.error === 'network' || e.error === 'aborted') && sttRetries < 3) {
                sttRetries++;
                setTimeout(() => {
                    if (isRecording && !interviewFinished && !isBusy) {
                        try { recognition.start(); } catch (_) {}
                    }
                }, 300);
                return;
            }
            isRecording = false;
            _setRecordingUI(false);
            if (e.error === 'network') {
                showError('Voice service connection error. Check your internet and try again.');
            } else if (e.error === 'not-allowed') {
                showError('Microphone permission denied. Enable it in browser settings.');
            } else {
                showError('Microphone error. Check your settings and try again.');
            }
        };

        recognition.onend = () => {
            if (isRecording && !interviewFinished && !isBusy) {
                try { recognition.start(); } catch (_) {}
            }
        };

        recognition.start();
        startCountdown();
    };

    const stopSTT = () => {
        isRecording = false;
        if (recognition) {
            try { recognition.stop(); } catch (_) {}
            recognition = null;
        }
        stopCountdown();
        _setRecordingUI(false);
    };

    // ─── Pause for review (user decides: re-record or submit) ──────────────
    const pauseForReview = () => {
        stopSTT();
        if (!currentTranscript.trim()) return;
        turnActions.style.display   = 'flex';
        recordBtn.style.display     = 'none';
    };

    const regrabar = () => {
        stopSTT();
        currentTranscript = '';
        transcripcionEl.innerHTML = '<span style="color:var(--g400);">Listening...</span>';
        startSTT();
        turnActions.style.display = 'flex';
        recordBtn.style.display   = 'none';
    };

    // ─── Recording UI state ───────────────────────────────────────────────────
    const _setRecordingUI = (grabando) => {
        if (grabando) {
            recordBtn.style.display     = 'none';
            turnActions.style.display   = 'flex';
        } else {
            recordBtn.style.display     = 'flex';
            recordBtn.style.background  = 'var(--secondary)';
            recordBtnIcon.textContent   = '🎙️';
            recordBtnLabel.textContent  = historial.length > 0 ? 'Record response' : 'Start interview';
            turnActions.style.display   = 'none';
        }
    };

    // ─── Submit current student turn ──────────────────────────────────────────
    const submitCurrentTurn = () => {
        if (isBusy) return;
        const transcript = currentTranscript.trim();
        stopSTT();
        turnActions.style.display = 'none';
        recordBtn.style.display   = 'flex';
        if (!transcript) return;
        appendMessage('user', transcript);
        sendTurn(transcript);
    };

    // ─── POST to TURNO_URL ────────────────────────────────────────────────────
    const sendTurn = (transcripcion) => {
        const isFirstTurn = historial.length === 0;
        isBusy = true;
        recordBtn.disabled = true;
        hideError();

        fetch(TURNO_URL, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  getCsrf(),
            },
            body: JSON.stringify({
                sesion_id:     SESION_ID,
                transcripcion: transcripcion,
                historial:     historial,
            }),
        })
        .then(r => {
            if (!r.ok) {
                return r.text().then(body => {
                    try { return Promise.reject(JSON.parse(body)); }
                    catch (_) { return Promise.reject({ error: `Server error (${r.status})` }); }
                });
            }
            return r.json();
        })
        .then(data => {
            historial = data.historial;
            appendMessage('assistant', data.respuesta);

            if (!isFirstTurn) {
                completedExchanges++;
                if (completedExchanges >= 1) finalizarBtn.style.display = 'block';
            }

            isBusy = false;
            recordBtn.disabled = false;
            recordBtn.style.background = 'var(--secondary)';
            transcripcionEl.innerHTML =
                '<span style="color:var(--g400);">Your voice will appear here as you speak...</span>';

            speak(data.respuesta, () => {
                if (!isBusy && !interviewFinished) startSTT();
            });
        })
        .catch(err => {
            isBusy = false;
            recordBtn.disabled = false;
            recordBtn.style.background = 'var(--secondary)';
            recordBtnIcon.textContent  = '🎙️';
            recordBtnLabel.textContent = 'Start interview';
            showError(err?.error || 'Connection error. Try again.');
        });
    };

    // ─── POST to FINALIZAR_URL ────────────────────────────────────────────────
    const finalizarEntrevista = () => {
        if (isBusy || interviewFinished) return;
        interviewFinished = true;
        stopSTT();
        window.speechSynthesis.cancel();
        finalizarBtn.disabled = true;
        recordBtn.disabled    = true;
        hideError();

        fetch(FINALIZAR_URL, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  getCsrf(),
            },
            body: JSON.stringify({ sesion_id: SESION_ID }),
        })
        .then(r => {
            if (!r.ok) return r.json().then(d => Promise.reject(d));
            return r.json();
        })
        .then(data => showResultado(data))
        .catch(err => {
            interviewFinished = false;
            finalizarBtn.disabled = false;
            recordBtn.disabled    = false;
            showError(err?.error || 'Error finishing the interview.');
        });
    };

    // ─── Results panel ────────────────────────────────────────────────────────
    const CATEGORY_LABELS = {
        pronunciacion:  'Pronunciation',
        vocabulario:    'Vocabulary',
        fluidez:        'Fluency',
        coherencia:     'Coherence',
        riqueza_lexica: 'Lexical richness',
    };

    const showResultado = (data) => {
        recordBtn.style.display     = 'none';
        submitTurnBtn.style.display = 'none';
        finalizarBtn.style.display  = 'none';
        if (hintBox) hintBox.style.display = 'none';

        puntajeDisplay.textContent = `${data.puntaje}%`;
        aprobadoLabel.textContent  = data.aprobado ? '✅ Aprobado' : '❌ No aprobado';
        aprobadoLabel.style.color  = data.aprobado ? 'var(--secondary)' : 'var(--danger)';

        scoresDetail.innerHTML = Object.entries(data.scores)
            .filter(([k]) => k !== 'sugerencias_mejora')
            .map(([k, v]) => `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:13px;color:var(--g600);">${CATEGORY_LABELS[k] || k}</span>
                    <span style="font-size:13px;font-weight:700;color:${v >= 80 ? 'var(--secondary)' : 'var(--warning)'};">${v}/100</span>
                </div>
            `).join('');

        if (data.scores.sugerencias_mejora) {
            sugerenciasText.textContent      = data.scores.sugerencias_mejora;
            sugerenciasDisplay.style.display = 'block';
        }

        if (data.submodulo_completado) examenNotice.style.display = 'block';

        resultadoPanel.style.display = 'block';
    };

    // ─── Event listeners ──────────────────────────────────────────────────────
    recordBtn.addEventListener('click', () => {
        if (isBusy || interviewFinished) return;

        if (historial.length === 0) {
            recordBtnLabel.textContent = 'Connecting to AI... please wait';
            recordBtnIcon.textContent  = '⏳';
            recordBtn.disabled         = true;
            recordBtn.style.background = 'var(--g400)';
            sendTurn('');
            return;
        }

        if (!isRecording) {
            // User clicked to skip TTS and start recording early
            window.speechSynthesis.cancel();
            startSTT();
        }
        // If already recording, "Finalizar respuesta" handles submission
    });

    submitTurnBtn.addEventListener('click', () => {
        if (!isBusy) submitCurrentTurn();
    });

    regrabarBtn.addEventListener('click', () => {
        if (!isBusy) regrabar();
    });

    finalizarBtn.addEventListener('click', () => {
        finalizarEntrevista();
    });

    // Trigger async voice list load for TTS
    if (typeof window.speechSynthesis !== 'undefined') {
        window.speechSynthesis.getVoices();
    }

    // Initialize countdown display
    countdownEl.textContent = `${TIEMPO_RESPUESTA}s`;
});
