/**
 * vocabulary.js — Motor STT/TTS para el Submódulo de Vocabulario y Lectura
 * HU-03 / HU-04 · RF-04
 *
 * Flujo por ejercicio:
 *   1. TTS lee la palabra/frase objetivo (máx. 2 veces, velocidad 1.0×)
 *   2. STT graba la pronunciación del estudiante
 *   3. Se compara palabra por palabra y se colorea el feedback (verde/rojo)
 *   4. Si puntaje ≥ 80 → ejercicio aprobado, se guarda progreso en BD
 *   5. Si puntaje < 80 → permite reintentar (intentos ilimitados)
 */

document.addEventListener('DOMContentLoaded', () => {

    // ─── Estado del ejercicio ────────────────────────────────────────────────
    let targetText     = '';      // frase/palabra objetivo
    let lastTranscript = '';      // última transcripción del STT
    let ttsPlayCount   = 0;       // reproducciones TTS (máx 2)
    let isRecording    = false;

    // ─── Elementos del DOM ───────────────────────────────────────────────────
    const targetWordEl      = document.getElementById('target-word');
    const ttsBtn            = document.getElementById('tts-btn');
    const recordBox         = document.getElementById('record-box');
    const micIcon           = document.getElementById('mic-icon');
    const recordStatus      = document.getElementById('record-status');
    const feedbackContainer = document.getElementById('feedback-container');
    const retryBtn          = document.getElementById('retry-btn');
    const scoreWarning      = document.querySelector('[id^="score"]') || null;

    // ─── Inicializar con el ejercicio actual ──────────────────────────────────
    // targetText viene del template Django como variable global
    // Si no hay variable global, usamos el texto del DOM como fallback
    if (typeof EXERCISE_TARGET !== 'undefined') {
        targetText = EXERCISE_TARGET;
    } else {
        targetText = targetWordEl
            ? targetWordEl.textContent.replace(/['"]/g, '').trim()
            : '';
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  MOTOR TTS — Síntesis de voz (Web Speech API)
    // ─────────────────────────────────────────────────────────────────────────
    const speakTarget = () => {
        if (!targetText) return;

        // Cancelar cualquier síntesis en curso
        window.speechSynthesis.cancel();

        const utterance    = new SpeechSynthesisUtterance(targetText);
        utterance.lang     = 'en-US';
        utterance.rate     = 1.0;   // velocidad natural, igual que el badge "TTS 1.0×"
        utterance.pitch    = 1.0;

        // Elegir voz nativa en inglés si está disponible
        const voices = window.speechSynthesis.getVoices();
        const enVoice = voices.find(v => v.lang.startsWith('en') && v.localService);
        if (enVoice) utterance.voice = enVoice;

        window.speechSynthesis.speak(utterance);

        ttsPlayCount++;
        if (ttsPlayCount >= 2) {
            ttsBtn.disabled          = true;
            ttsBtn.style.opacity     = '0.5';
            ttsBtn.innerHTML         = '🔊 Límite de reproducciones alcanzado';
        }
    };

    if (ttsBtn) {
        ttsBtn.addEventListener('click', speakTarget);

        // Reproducción automática al cargar (primera vez)
        // Necesita un pequeño delay porque algunas voces tardan en cargar
        setTimeout(() => {
            if (window.speechSynthesis.getVoices().length === 0) {
                window.speechSynthesis.onvoiceschanged = () => speakTarget();
            } else {
                speakTarget();
            }
        }, 600);
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  MOTOR STT — Reconocimiento de voz (Web Speech API)
    // ─────────────────────────────────────────────────────────────────────────
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    const startRecording = () => {
        if (!SpeechRecognition) {
            _showError('Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.');
            return;
        }
        if (isRecording) return;

        isRecording = true;
        _setRecordingUI(true);

        const recognition          = new SpeechRecognition();
        recognition.lang           = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.start();

        // Timeout de seguridad: si no hay resultado en 8s, cancela
        const safetyTimer = setTimeout(() => {
            recognition.stop();
        }, 8000);

        recognition.onresult = (event) => {
            clearTimeout(safetyTimer);
            lastTranscript = event.results[0][0].transcript.trim();
            isRecording    = false;
            _setRecordingUI(false);
            _evaluarPronunciacion(lastTranscript);
        };

        recognition.onerror = (e) => {
            clearTimeout(safetyTimer);
            isRecording = false;
            _setRecordingUI(false);
            _showError(`Error de micrófono: ${e.error}. Verifica permisos e intenta de nuevo.`);
        };

        recognition.onend = () => {
            clearTimeout(safetyTimer);
            if (isRecording) {
                isRecording = false;
                _setRecordingUI(false);
            }
        };
    };

    if (recordBox) {
        recordBox.addEventListener('click', startRecording);
    }

    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            lastTranscript = '';
            ttsPlayCount   = 0;
            if (ttsBtn) {
                ttsBtn.disabled      = false;
                ttsBtn.style.opacity = '1';
                ttsBtn.innerHTML     = '🔊 Escuchar modelo TTS (1.0×)';
            }
            _clearFeedback();
            _setRecordingUI(false);
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  EVALUACIÓN — Comparación palabra por palabra
    // ─────────────────────────────────────────────────────────────────────────
    const _evaluarPronunciacion = (transcript) => {
        const targetWords = _normalizar(targetText).split(' ');
        const spokenWords = _normalizar(transcript).split(' ');

        let correctas = 0;
        const resultados = targetWords.map((palabra, i) => {
            const dicha = spokenWords[i] || '';
            const ok    = _similitud(dicha, palabra) >= 0.75;
            if (ok) correctas++;
            return { palabra, ok };
        });

        const puntaje = Math.round((correctas / targetWords.length) * 100);
        _mostrarFeedback(resultados, puntaje, transcript);

        if (puntaje >= 80) {
            _guardarProgreso(puntaje);
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  UI — Helpers
    // ─────────────────────────────────────────────────────────────────────────
    const _mostrarFeedback = (resultados, puntaje, transcript) => {
        if (!feedbackContainer) return;

        feedbackContainer.innerHTML = resultados.map(({ palabra, ok }) =>
            `<span style="padding:6px 12px; border-radius:8px; font-size:14px; font-weight:700;
                background:${ok ? 'var(--secondary-light)' : 'var(--danger-light)'};
                color:${ok ? 'var(--secondary)' : 'var(--danger)'};">
                ${ok ? '✓' : '✗'} ${palabra}
            </span>`
        ).join('');

        // Actualizar el badge de puntaje si existe en el DOM
        const scoreEl = document.querySelector('[id="score-badge"]');
        if (scoreEl) {
            const color = puntaje >= 80 ? 'var(--secondary)' : 'var(--warning)';
            scoreEl.style.color = color;
            scoreEl.textContent = `Puntaje: ${puntaje}% · ${puntaje >= 80 ? '✅ ¡Superado!' : 'Necesitas ≥80% · Reintento ilimitado'}`;
        }

        // También actualizar el bloque de advertencia existente en el HTML
        const warningEl = document.querySelector('.score-warning');
        if (warningEl) {
            if (puntaje >= 80) {
                warningEl.style.background    = 'var(--secondary-light)';
                warningEl.style.borderColor   = 'rgba(16,185,129,0.4)';
                warningEl.querySelector('p').style.color = 'var(--secondary)';
                warningEl.querySelector('p').textContent =
                    `✅ Puntaje: ${puntaje}% · ¡Ejercicio superado! Continúa al siguiente.`;
            } else {
                warningEl.querySelector('p').textContent =
                    `⚠️ Puntaje: ${puntaje}% · Necesitas ≥80% para completar · Reintento ilimitado`;
            }
        }

        // Mostrar transcripción recibida debajo del feedback
        const transcriptEl = document.getElementById('transcript-result');
        if (transcriptEl) {
            transcriptEl.textContent = `Escuchamos: "${transcript}"`;
            transcriptEl.style.display = 'block';
        }
    };

    const _clearFeedback = () => {
        if (feedbackContainer) feedbackContainer.innerHTML = '';
        const transcriptEl = document.getElementById('transcript-result');
        if (transcriptEl) transcriptEl.style.display = 'none';
    };

    const _setRecordingUI = (grabando) => {
        if (!recordBox || !micIcon || !recordStatus) return;

        if (grabando) {
            micIcon.style.background    = 'var(--danger)';
            micIcon.style.boxShadow     = '0 4px 16px rgba(239,68,68,0.5)';
            recordStatus.textContent    = 'Escuchando... 🔴';
            recordStatus.style.color    = 'var(--danger)';
            recordBox.style.borderColor = 'var(--danger)';
            recordBox.style.cursor      = 'not-allowed';
        } else {
            micIcon.style.background    = 'var(--secondary)';
            micIcon.style.boxShadow     = '0 4px 12px rgba(16,185,129,0.3)';
            recordStatus.textContent    = lastTranscript
                ? '🔄 Toca para intentar de nuevo'
                : '🎙️ Toca para empezar a hablar';
            recordStatus.style.color    = 'var(--secondary)';
            recordBox.style.borderColor = 'var(--secondary)';
            recordBox.style.cursor      = 'pointer';
        }
    };

    const _showError = (msg) => {
        if (!feedbackContainer) return;
        feedbackContainer.innerHTML =
            `<p style="color:var(--danger); font-size:13px; font-weight:600;">⚠️ ${msg}</p>`;
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  PERSISTENCIA — Guarda progreso en el servidor
    // ─────────────────────────────────────────────────────────────────────────
    const _guardarProgreso = (puntaje) => {
        const exerciseId = document.getElementById('exercise-id')?.value;
        if (!exerciseId) return;  // sin exercise_id no guardamos

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch('/progress/guardar-ejercicio/', {
            method:  'POST',
            headers: {
                'Content-Type':     'application/json',
                'X-CSRFToken':      csrfToken,
            },
            body: JSON.stringify({
                exercise_id: exerciseId,
                puntaje:     puntaje,
            }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                // Mostrar botón de continuar si el ejercicio fue aprobado
                const nextBtn = document.getElementById('next-exercise-btn');
                if (nextBtn) nextBtn.style.display = 'inline-flex';
            }
        })
        .catch(err => console.error('Error guardando progreso:', err));
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  UTILIDADES
    // ─────────────────────────────────────────────────────────────────────────

    /** Quita puntuación, minúsculas y espacios extra */
    const _normalizar = (texto) =>
        texto.toLowerCase()
             .replace(/[.,!?;:'"()\-]/g, '')
             .replace(/\s+/g, ' ')
             .trim();

    /** Similitud entre dos strings (0.0 – 1.0) usando Longest Common Subsequence */
    const _similitud = (a, b) => {
        if (a === b) return 1;
        if (!a || !b) return 0;
        const m = a.length, n = b.length;
        const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
        for (let i = 1; i <= m; i++)
            for (let j = 1; j <= n; j++)
                dp[i][j] = a[i-1] === b[j-1]
                    ? dp[i-1][j-1] + 1
                    : Math.max(dp[i-1][j], dp[i][j-1]);
        return (2 * dp[m][n]) / (m + n);
    };

});
