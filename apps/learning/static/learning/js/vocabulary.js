/**
 * vocabulary.js — Motor STT/TTS para el Submódulo de Vocabulario y Lectura
 * HU-03 / HU-04 · RF-04
 *
 * Consume los globales inyectados por vocabulary.html:
 * const EXERCISES  = [{ id, texto_objetivo, nivel }, ...];
 * const GUARDAR_URL = "/progress/guardar-ejercicio/";
 *
 * Flujo por ejercicio:
 * 1. showExercise(index) muestra la card correspondiente
 * 2. TTS lee el texto objetivo (máx 2 veces, velocidad 1.0×)
 * 3. STT graba la pronunciación del estudiante
 * 4. score() compara palabra por palabra → puntaje 0–100
 * 5. submitAttempt() POST a GUARDAR_URL con ejercicio_id + puntaje + transcripcion
 * 6. showResult() colorea feedback, actualiza barra de progreso
 * 7. Si aprobado (puntaje ≥ 80) avanza al siguiente ejercicio tras 1.5 s
 */

document.addEventListener('DOMContentLoaded', () => {

    // ─── Validación de globales ───────────────────────────────────────────────
    if (typeof EXERCISES === 'undefined' || !Array.isArray(EXERCISES) || EXERCISES.length === 0) {
        console.warn('vocabulary.js: EXERCISES global not found or empty. Aborting.');
        return;
    }
    if (typeof GUARDAR_URL === 'undefined') {
        console.warn('vocabulary.js: GUARDAR_URL global not found. Aborting.');
        return;
    }

    // ─── Estado de sesión ─────────────────────────────────────────────────────
    let isRecording     = false;
    let lastTranscript  = '';
    let ttsPlayCount    = 0;
    const passedSet     = new Set();
    const wordErrors    = new Map();

    const _passedIds = (typeof PASSED_IDS !== 'undefined' && Array.isArray(PASSED_IDS)) ? PASSED_IDS : [];
    _passedIds.forEach(id => {
        const idx = EXERCISES.findIndex(e => e.id === id);
        if (idx !== -1) passedSet.add(idx);
    });

    let totalCompleted  = passedSet.size;
    let currentIndex    = EXERCISES.findIndex((_, i) => !passedSet.has(i));
    if (currentIndex === -1) currentIndex = 0;

    // ─────────────────────────────────────────────────────────────────────────
    //  NAVEGACIÓN — Muestra / oculta cards
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Oculta todas las cards, muestra la del ejercicio en `index`,
     * y resetea los elementos de interacción de esa card.
     */
    const showExercise = (index) => {
        // Ocultar todas las cards
        document.querySelectorAll('div[id^="ejercicio-"]').forEach(el => {
            el.style.display = 'none';
        });

        const ejercicio = EXERCISES[index];
        if (!ejercicio) return;

        const card = document.getElementById(`ejercicio-${ejercicio.id}`);
        if (!card) return;
        card.style.display = 'block';

        // Reset feedback al placeholder
        const feedbackContainer = card.querySelector('#feedback-container');
        if (feedbackContainer) {
            feedbackContainer.innerHTML =
                '<span style="font-size:13px; color:var(--g400); font-style:italic;">Graba tu pronunciación para ver la retroalimentación.</span>';
        }

        // Ocultar score-box
        const scoreBox = card.querySelector('#score-box');
        if (scoreBox) scoreBox.style.display = 'none';

        // Resetear record-status
        const recordStatus = card.querySelector('#record-status');
        if (recordStatus) {
            recordStatus.textContent  = 'Presioná para grabar';
            recordStatus.style.color  = 'var(--secondary)';
        }

        // Resetear record-box border
        const recordBox = card.querySelector('#record-box');
        if (recordBox) {
            recordBox.style.borderColor = 'var(--secondary)';
            recordBox.style.cursor      = 'pointer';
        }

        // Resetear mic-icon
        const micIcon = card.querySelector('#mic-icon');
        if (micIcon) {
            micIcon.style.background = 'var(--secondary)';
            micIcon.style.boxShadow  = '0 4px 12px rgba(16,185,129,0.3)';
        }

        // Resetear TTS button
        const ttsBtn = card.querySelector('#tts-btn');
        if (ttsBtn) {
            ttsBtn.disabled      = false;
            ttsBtn.style.opacity = '1';
            ttsBtn.innerHTML     = '🔊 Listen to sentence';
        }

        // Resetear live transcript
        const liveText = card.querySelector('#live-text');
        if (liveText) {
            liveText.textContent = 'Your voice will appear here as you speak...';
            liveText.style.fontStyle = 'italic';
            liveText.style.color = 'var(--g400)';
        }

        // Resetear estado local
        lastTranscript = '';
        accumulatedTranscript = '';
        ttsPlayCount   = 0;
        isRecording    = false;
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  PRIORIZACIÓN — Claude reorders exercises by error patterns (RF-04)
    //
    //  One API call after the first pass. Claude considers phonetic similarity,
    //  word families, and linguistic patterns — not just string matching.
    //  Falls back to local deterministic sort if Claude fails or is unavailable.
    // ─────────────────────────────────────────────────────────────────────────

    let claudeOrder = null;  // populated after first pass via PRIORITIZE_URL

    const errorOverlap = (texto) => {
        const words = texto.toLowerCase().replace(/[.,!?¿¡]/g, '').split(/\s+/);
        return words.reduce((sum, w) => sum + (wordErrors.get(w) || 0), 0);
    };

    const findNextLocal = () => {
        const unpassed = [];
        for (let i = 0; i < EXERCISES.length; i++) {
            if (!passedSet.has(i)) unpassed.push(i);
        }
        if (unpassed.length === 0) return -1;
        unpassed.sort((a, b) => errorOverlap(EXERCISES[b].texto_objetivo) - errorOverlap(EXERCISES[a].texto_objetivo));
        return unpassed[0];
    };

    const findNextPrioritized = () => {
        if (claudeOrder) {
            const next = claudeOrder.find(id => {
                const idx = EXERCISES.findIndex(e => e.id === id);
                return idx !== -1 && !passedSet.has(idx);
            });
            if (next !== undefined) return EXERCISES.findIndex(e => e.id === next);
        }
        return findNextLocal();
    };

    const requestClaudePrioritization = () => {
        const pending = EXERCISES
            .filter((_, i) => !passedSet.has(i))
            .map(e => ({ id: e.id, texto_objetivo: e.texto_objetivo }));
        if (pending.length === 0) return;

        const errors = {};
        wordErrors.forEach((count, word) => { errors[word] = count; });
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetch(PRIORITIZE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ word_errors: errors, pending_exercises: pending }),
        })
        .then(r => r.json())
        .then(data => { if (data.ordered_ids) claudeOrder = data.ordered_ids; })
        .catch(() => {});
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  PROGRESO — Barra superior
    // ─────────────────────────────────────────────────────────────────────────

    const updateProgressBar = () => {
        const pct      = EXERCISES.length > 0
            ? Math.round((totalCompleted / EXERCISES.length) * 100)
            : 0;
        const bar      = document.getElementById('progress-bar');
        const pctLabel = document.getElementById('progress-pct');
        if (bar)      bar.style.width  = `${pct}%`;
        if (pctLabel) pctLabel.textContent = `${pct}%`;
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  TTS — Síntesis de voz (Web Speech API)
    // ─────────────────────────────────────────────────────────────────────────

    const speakTarget = (texto, ttsBtn) => {
        if (!texto) return;
        window.speechSynthesis.cancel();

        const utterance    = new SpeechSynthesisUtterance(texto);
        utterance.lang     = 'en-US';
        utterance.rate     = 1.0;
        utterance.pitch    = 1.0;

        const voices  = window.speechSynthesis.getVoices();
        const enVoice = voices.find(v => v.lang.startsWith('en') && v.localService);
        if (enVoice) utterance.voice = enVoice;

        window.speechSynthesis.speak(utterance);

        ttsPlayCount++;
        if (ttsPlayCount >= 2 && ttsBtn) {
            ttsBtn.disabled      = true;
            ttsBtn.style.opacity = '0.5';
            ttsBtn.innerHTML     = '🔊 Playback limit reached';
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  STT — Reconocimiento de voz (Web Speech API)
    // ─────────────────────────────────────────────────────────────────────────

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let sttRetries = 0;
    const MAX_STT_RETRIES = 3;
    let currentRecognition = null;
    let accumulatedTranscript = '';

    const _updateLiveText = (card, text) => {
        const el = card.querySelector('#live-text');
        if (el) {
            el.textContent = text || '…';
            el.style.fontStyle = text ? 'normal' : 'italic';
            el.style.color = text ? 'var(--g800)' : 'var(--g400)';
        }
    };

    const startRecording = (card) => {
        if (!SpeechRecognition) {
            _showError(card, 'Your browser does not support speech recognition. Use Chrome or Edge.');
            return;
        }
        if (isRecording) return;

        isRecording = true;
        sttRetries  = 0;
        accumulatedTranscript = '';
        _updateLiveText(card, '');
        _setRecordingUI(card, true);
        _launchSTT(card);
    };

    const _launchSTT = (card) => {
        const recognition       = new SpeechRecognition();
        recognition.lang        = 'en-US';
        recognition.interimResults = true;
        recognition.continuous     = true;
        recognition.maxAlternatives = 1;
        currentRecognition = recognition;

        const safetyTimer = setTimeout(() => {
            if (isRecording) {
                recognition.stop();
                const transcript = accumulatedTranscript.trim();
                if (transcript) {
                    isRecording = false;
                    lastTranscript = transcript;
                    _setRecordingUI(card, false);
                    submitAttempt(transcript);
                }
            }
        }, 10000);

        recognition.onresult = (event) => {
            let interim = '';
            let finalText = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) finalText += t + ' ';
                else interim += t;
            }
            if (finalText) accumulatedTranscript += finalText;
            _updateLiveText(card, (accumulatedTranscript + interim).trim());
        };

        recognition.onerror = (e) => {
            clearTimeout(safetyTimer);
            if ((e.error === 'network' || e.error === 'aborted') && sttRetries < MAX_STT_RETRIES) {
                sttRetries++;
                setTimeout(() => { if (isRecording) _launchSTT(card); }, 300);
                return;
            }
            if (e.error === 'no-speech') return;
            isRecording = false;
            currentRecognition = null;
            _setRecordingUI(card, false);
            if (e.error === 'network') {
                _showError(card, 'Voice service connection error. Check your internet and try again.');
            } else if (e.error === 'not-allowed') {
                _showError(card, 'Microphone permission denied. Enable it in browser settings.');
            } else {
                _showError(card, `Microphone error: ${e.error}. Try again.`);
            }
        };

        recognition.onend = () => {
            clearTimeout(safetyTimer);
            if (isRecording && !accumulatedTranscript.trim()) {
                isRecording = false;
                currentRecognition = null;
                _setRecordingUI(card, false);
            }
        };

        recognition.start();
    };

    const stopAndSubmit = () => {
        if (!isRecording) return;
        isRecording = false;
        if (currentRecognition) {
            try { currentRecognition.stop(); } catch (_) {}
            currentRecognition = null;
        }
        const transcript = accumulatedTranscript.trim();
        if (transcript) {
            lastTranscript = transcript;
            const card = document.getElementById(`ejercicio-${EXERCISES[currentIndex].id}`);
            _setRecordingUI(card, false);
            submitAttempt(transcript);
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  SCORING — Comparación simple palabra por palabra
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Compara `transcript` contra `target`.
     * Retorna un entero 0–100 (porcentaje de palabras en posición correcta).
     */
    const score = (transcript, target) => {
        // 🔥 Limpieza: eliminamos signos de puntuación antes de separar
        const cleanTranscript = transcript.toLowerCase().replace(/[.,!?¿¡]/g, '').trim();
        const cleanTarget = target.toLowerCase().replace(/[.,!?¿¡]/g, '').trim();

        const tWords = cleanTranscript.split(/\s+/);
        const aWords = cleanTarget.split(/\s+/);
        let correct  = 0;
        aWords.forEach((w, i) => {
            if (tWords[i] === w) correct++;
        });
        return Math.round((correct / aWords.length) * 100);
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  PERSISTENCIA — POST a GUARDAR_URL
    // ─────────────────────────────────────────────────────────────────────────

    const submitAttempt = (transcript) => {
        const ejercicio = EXERCISES[currentIndex];
        if (!ejercicio) return;

        const puntaje   = score(transcript, ejercicio.texto_objetivo);
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        fetchWithRetry(GUARDAR_URL, {
            method:  'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  csrfToken,
            },
            body: JSON.stringify({
                ejercicio_id:  ejercicio.id,
                puntaje:       puntaje,
                transcripcion: transcript,
            }),
        })
        .then(r => r.json())
        .then(data => showResult(data, transcript))
        .catch(err => {
            const card = document.getElementById(`ejercicio-${ejercicio.id}`);
            if (card) _showError(card, `Error saving progress: ${err.message}`);
        });
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  RESULTADO — Renderiza feedback y gestiona avance
    // ─────────────────────────────────────────────────────────────────────────

    const showResult = (data, transcript) => {
        const ejercicio = EXERCISES[currentIndex];
        if (!ejercicio) return;

        const card = document.getElementById(`ejercicio-${ejercicio.id}`);
        if (!card) return;

        // ── Feedback palabra por palabra ──────────────────────────────────────
        // 🔥 Limpieza visual: para que las etiquetas verdes/rojas coincidan con el puntaje
        const cleanTarget = ejercicio.texto_objetivo.toLowerCase().replace(/[.,!?¿¡]/g, '').trim();
        const cleanSpoken = transcript.toLowerCase().replace(/[.,!?¿¡]/g, '').trim();

        const targetWords  = cleanTarget.split(/\s+/);
        const spokenWords  = cleanSpoken.split(/\s+/);

        targetWords.forEach((w, i) => {
            if (spokenWords[i] !== w) wordErrors.set(w, (wordErrors.get(w) || 0) + 1);
        });

        const feedbackContainer = card.querySelector('#feedback-container');
        if (feedbackContainer) {
            feedbackContainer.innerHTML = targetWords.map((word, i) => {
                const ok = spokenWords[i] === word;
                return `<span style="padding:6px 12px; border-radius:8px; font-size:14px; font-weight:700;
                    background:${ok ? 'var(--secondary-light)' : 'var(--danger-light)'};
                    color:${ok ? 'var(--secondary)' : 'var(--danger)'};">
                    ${ok ? '✓' : '✗'} ${word}
                </span>`;
            }).join('');
        }

        // ── Score box ─────────────────────────────────────────────────────────
        const scoreBox = card.querySelector('#score-box');
        const scoreMsg = card.querySelector('#score-msg');
        if (scoreBox && scoreMsg) {
            scoreBox.style.display    = 'block';
            if (data.aprobado) {
                scoreBox.style.background = 'var(--secondary-light)';
                scoreBox.style.border     = '1px solid rgba(16,185,129,0.4)';
                scoreMsg.style.color      = 'var(--secondary)';
                scoreMsg.textContent      = `✅ Score: ${data.puntaje}% · Exercise passed! Moving to next...`;
            } else {
                scoreBox.style.background = '#FFF8E1';
                scoreBox.style.border     = '1px solid rgba(245,158,11,0.4)';
                scoreMsg.style.color      = 'var(--warning)';
                scoreMsg.textContent      = `⚠️ Score: ${data.puntaje}% · You need ≥80% · Unlimited retries`;
            }
        }

        // ── Avance automático si aprobado ─────────────────────────────────────
        if (data.aprobado) {
            passedSet.add(currentIndex);
            totalCompleted++;
            updateProgressBar();

            if (passedSet.size === 1) requestClaudePrioritization();

            setTimeout(() => {
                const next = findNextPrioritized();
                if (next !== -1) {
                    currentIndex = next;
                    showExercise(currentIndex);
                } else {
                    _showCompletionMessage(data.submodulo_completado);
                }
            }, 1500);
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  MENSAJE DE COMPLETADO
    // ─────────────────────────────────────────────────────────────────────────

    const _showCompletionMessage = (submoduloCompletado) => {
        // Ocultar todas las cards
        document.querySelectorAll('div[id^="ejercicio-"]').forEach(el => {
            el.style.display = 'none';
        });

        // Actualizar barra al 100 %
        totalCompleted = EXERCISES.length;
        updateProgressBar();

        // Mostrar mensaje en el contenedor de ejercicios
        const container = document.querySelector('[style*="overflow-y: auto"]');
        const wrapper   = document.createElement('div');
        wrapper.style.cssText = 'background:#FFFFFF; border-radius:12px; border:1px solid var(--g200); padding:40px; text-align:center; margin-top:16px;';
        const dashboardBtn = `<a href="${DASHBOARD_URL}" style="display:inline-block; margin-top:16px; padding:10px 24px; border-radius:9px; background:var(--primary); color:#FFFFFF; font-size:14px; font-weight:700; text-decoration:none;">Back to Dashboard</a>`;
        wrapper.innerHTML = submoduloCompletado
            ? `<p style="font-size:22px; font-weight:800; color:var(--secondary); margin:0 0 8px 0;">🎉 Submodule completed!</p>
               <p style="font-size:14px; color:var(--g500); margin:0 0 0 0;">You passed all vocabulary exercises.</p>
               ${dashboardBtn}`
            : `<p style="font-size:22px; font-weight:800; color:var(--primary); margin:0 0 8px 0;">✅ Exercises completed!</p>
               <p style="font-size:14px; color:var(--g500); margin:0 0 0 0;">You completed all available exercises in this session.</p>
               ${dashboardBtn}`;

        if (container) container.appendChild(wrapper);
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  UI HELPERS
    // ─────────────────────────────────────────────────────────────────────────

    const _setRecordingUI = (card, grabando) => {
        if (!card) return;
        const recordBox    = card.querySelector('#record-box');
        const micIcon      = card.querySelector('#mic-icon');
        const recordStatus = card.querySelector('#record-status');
        if (!recordBox || !micIcon || !recordStatus) return;

        if (grabando) {
            micIcon.style.background    = 'var(--danger)';
            micIcon.style.boxShadow     = '0 4px 16px rgba(239,68,68,0.5)';
            recordStatus.textContent    = '🔴 Listening... Tap to submit';
            recordStatus.style.color    = 'var(--danger)';
            recordBox.style.borderColor = 'var(--danger)';
            recordBox.style.cursor      = 'pointer';
        } else {
            micIcon.style.background    = 'var(--secondary)';
            micIcon.style.boxShadow     = '0 4px 12px rgba(16,185,129,0.3)';
            recordStatus.textContent    = lastTranscript
                ? '🔄 Tap to try again'
                : '🎙️ Tap to record';
            recordStatus.style.color    = 'var(--secondary)';
            recordBox.style.borderColor = 'var(--secondary)';
            recordBox.style.cursor      = 'pointer';
        }
    };

    const _showError = (card, msg) => {
        if (!card) return;
        const feedbackContainer = card.querySelector('#feedback-container');
        if (feedbackContainer) {
            feedbackContainer.innerHTML =
                `<p style="color:var(--danger); font-size:13px; font-weight:600;">⚠️ ${msg}</p>`;
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  DELEGACIÓN DE EVENTOS — Usa event delegation para manejar todas las cards
    // ─────────────────────────────────────────────────────────────────────────

    document.addEventListener('click', (event) => {
        // Encontrar la card ancestro del elemento clickeado
        const card = event.target.closest('div[id^="ejercicio-"]');
        if (!card) return;

        // TTS button
        if (event.target.closest('#tts-btn')) {
            const ejercicio = EXERCISES[currentIndex];
            if (ejercicio) {
                const ttsBtn = card.querySelector('#tts-btn');
                speakTarget(ejercicio.texto_objetivo, ttsBtn);
            }
            return;
        }

        // Record box: start recording or stop and submit
        if (event.target.closest('#record-box')) {
            if (isRecording) {
                stopAndSubmit();
            } else {
                startRecording(card);
            }
            return;
        }

        // Retry button
        if (event.target.closest('#retry-btn')) {
            showExercise(currentIndex);
            return;
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    //  INICIALIZACIÓN
    // ─────────────────────────────────────────────────────────────────────────

    showExercise(currentIndex);
    updateProgressBar();

});