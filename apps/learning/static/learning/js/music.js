document.addEventListener('DOMContentLoaded', () => {
    if (typeof CANCIONES === 'undefined' || CANCIONES.length === 0) {
        document.getElementById('song-title').textContent = 'No hay canciones disponibles.';
        return;
    }

    const audioPlayer = document.getElementById('audio-player');
    const lyricsContainer = document.getElementById('lyrics-container');
    const karaokeBtn = document.getElementById('karaoke-btn');
    const karaokeStatus = document.getElementById('karaoke-status');
    const songIndicator = document.getElementById('song-indicator');
    const songProgress = document.getElementById('song-progress');
    const btnPrev = document.getElementById('song-prev');
    const btnNext = document.getElementById('song-next');

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    let currentSongIndex = 0;
    const totalSongs = CANCIONES.length;
    const songsCompleted = new Set();

    let lyricsData = [];
    let currentLineIndex = -1;
    let lineScores = new Map();
    let bestTranscripts = new Map();
    let songSaved = false;

    // ─── LRC PARSER (preserved from Ian) ───────────────────────────────────
    const parseLRC = (lrc) => {
        const lines = lrc.split('\n');
        const regex = /\[(\d{2}):(\d{2}\.\d{2,3}|\d{2})\](.*)/;
        const parsed = [];
        lines.forEach(line => {
            const match = line.match(regex);
            if (match) {
                const minutes = parseInt(match[1], 10);
                const seconds = parseFloat(match[2]);
                const text = match[3].trim();
                if (text) parsed.push({ time: minutes * 60 + seconds, text: text });
            }
        });
        return parsed;
    };

    // ─── WORD-BY-WORD SCORER (preserved from Ian) ──────────────────────────
    const score = (transcript, target) => {
        const cleanT = transcript.toLowerCase().replace(/[.,!?¿¡()]/g, '').trim().split(/\s+/);
        const cleanA = target.toLowerCase().replace(/[.,!?¿¡()]/g, '').trim().split(/\s+/);
        let correct = 0;
        cleanA.forEach((w, i) => { if (cleanT[i] === w) correct++; });
        return Math.round((correct / cleanA.length) * 100);
    };

    // ─── PROGRESS SAVE — server-side scoring ─────────────────────────────
    // Server recomputes the score from line_transcriptions using the same
    // word-by-word algorithm (shared/utils.py _score_musica). If you change
    // the scoring logic in score() above, update _score_palabra_por_palabra
    // in Python to stay in sync.
    const guardarProgreso = () => {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const lt = {};
        bestTranscripts.forEach((text, idx) => { lt[String(idx)] = text; });
        return fetchWithRetry(GUARDAR_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                ejercicio_id: CANCIONES[currentSongIndex].id,
                line_transcriptions: lt,
            }),
        }).then(r => r.json()).catch(err => console.error("Error al guardar:", err));
    };

    // ─── GLOBAL SCORE COMPUTATION ──────────────────────────────────────────
    const computeGlobalScore = () => {
        if (lyricsData.length === 0) return 0;
        let passed = 0;
        lineScores.forEach(bestScore => { if (bestScore >= 80) passed++; });
        return Math.round((passed / lyricsData.length) * 100);
    };

    const updateProgressUI = () => {
        let passed = 0;
        lineScores.forEach(bestScore => { if (bestScore >= 80) passed++; });
        const globalScore = computeGlobalScore();
        songProgress.textContent = `Líneas: ${passed}/${lyricsData.length} — ${globalScore}%`;
    };

    // ─── NAV UI ────────────────────────────────────────────────────────────
    const updateNavUI = () => {
        songIndicator.textContent = `Canción ${currentSongIndex + 1} de ${totalSongs}`;
        btnPrev.disabled = currentSongIndex <= 0;
        btnPrev.style.opacity = currentSongIndex <= 0 ? '0.4' : '1';
        btnNext.disabled = currentSongIndex >= totalSongs - 1;
        btnNext.style.opacity = currentSongIndex >= totalSongs - 1 ? '0.4' : '1';
    };

    // ─── INIT SONG (teardown/rebuild per song) ─────────────────────────────
    const initSong = (index) => {
        currentSongIndex = index;
        const song = CANCIONES[index];

        document.getElementById('song-title').textContent = song.titulo;

        const audioUrl = song.config.audio_url || '';
        const lrcText = song.config.lrc || '';

        if (!audioUrl) {
            lyricsContainer.innerHTML = '<p style="color:red;">Error: Falla el enlace de audio.</p>';
            return;
        }

        audioPlayer.pause();
        audioPlayer.src = audioUrl;
        audioPlayer.playbackRate = PLAYBACK_RATE;
        audioPlayer.addEventListener('loadedmetadata', () => {
            audioPlayer.playbackRate = PLAYBACK_RATE;
        }, { once: true });

        currentLineIndex = -1;
        lineScores = new Map();
        bestTranscripts = new Map();
        songSaved = songsCompleted.has(song.id);

        lyricsData = parseLRC(lrcText);

        if (lyricsData.length > 0) {
            lyricsContainer.innerHTML = lyricsData.map((line, i) =>
                `<p id="line-${i}" style="font-size: 20px; color: var(--g400); margin: 12px 0; transition: all 0.3s ease;">
                    ${line.text}
                </p>`
            ).join('');
        } else {
            lyricsContainer.innerHTML = '<p style="color: var(--g500); font-style: italic;">Sin letra disponible.</p>';
        }

        karaokeStatus.innerHTML = '';
        if (SpeechRecognition && karaokeBtn) {
            karaokeBtn.style.display = 'inline-block';
            karaokeBtn.textContent = '🎤 Practicar línea actual';
            karaokeBtn.style.background = 'var(--secondary)';
        }

        updateNavUI();
        updateProgressUI();
    };

    // ─── AUDIO SYNC (preserved from Ian) ───────────────────────────────────
    audioPlayer.addEventListener('timeupdate', () => {
        const currentTime = audioPlayer.currentTime;
        let activeIndex = -1;
        for (let i = 0; i < lyricsData.length; i++) {
            if (currentTime >= lyricsData[i].time) {
                activeIndex = i;
            } else {
                break;
            }
        }

        if (activeIndex !== currentLineIndex && activeIndex !== -1) {
            if (currentLineIndex !== -1) {
                const oldLine = document.getElementById(`line-${currentLineIndex}`);
                if (oldLine && !lineScores.has(currentLineIndex)) {
                    oldLine.style.color = 'var(--g400)';
                    oldLine.style.fontWeight = '400';
                    oldLine.style.transform = 'scale(1)';
                }
            }

            const newLine = document.getElementById(`line-${activeIndex}`);
            if (newLine) {
                newLine.style.color = 'var(--primary)';
                newLine.style.fontWeight = '800';
                newLine.style.transform = 'scale(1.1)';
                newLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            currentLineIndex = activeIndex;
        }
    });

    // ─── STT + GLOBAL SCORING ──────────────────────────────────────────────
    if (SpeechRecognition && karaokeBtn) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        karaokeBtn.addEventListener('click', () => {
            if (currentLineIndex === -1 || !lyricsData[currentLineIndex]) {
                karaokeStatus.textContent = "Dale Play a la música primero.";
                return;
            }

            audioPlayer.pause();
            const lineaObjetivo = lyricsData[currentLineIndex].text;
            karaokeBtn.textContent = "🔴 Escuchando...";
            karaokeBtn.style.background = "var(--danger)";
            karaokeStatus.innerHTML = `🎤 Di esto: <strong>"${lineaObjetivo}"</strong>`;

            try { recognition.start(); } catch(e) { recognition.stop(); }
        });

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.trim();
            const lineaObjetivo = lyricsData[currentLineIndex].text;
            const puntaje = score(transcript, lineaObjetivo);
            const lineEl = document.getElementById(`line-${currentLineIndex}`);

            const prev = lineScores.get(currentLineIndex) || 0;
            if (puntaje > prev) {
                bestTranscripts.set(currentLineIndex, transcript);
            }
            lineScores.set(currentLineIndex, Math.max(prev, puntaje));

            if (puntaje >= 80) {
                if (lineEl) { lineEl.style.color = "#10B981"; lineEl.textContent = "✓ " + lineaObjetivo; }
                karaokeStatus.innerHTML = `✅ ¡Perfecto! (${puntaje}%)`;
            } else {
                if (lineEl) { lineEl.style.color = "#F59E0B"; lineEl.textContent = "✗ " + lineaObjetivo; }
                karaokeStatus.innerHTML = `⚠️ (${puntaje}%). Dijiste: "${transcript}". Intenta de nuevo.`;
            }

            updateProgressUI();

            const globalScore = computeGlobalScore();
            if (globalScore >= 80 && !songSaved) {
                songSaved = true;
                songsCompleted.add(CANCIONES[currentSongIndex].id);

                guardarProgreso().then(response => {
                    confetti({
                        particleCount: 150,
                        spread: 80,
                        origin: { y: 0.6 },
                        colors: ['#4F46E5', '#10B981', '#F59E0B', '#EF4444']
                    });

                    const isLastSong = songsCompleted.size >= totalSongs;
                    const isSubmoduleComplete = response && response.submodulo_completado;

                    Swal.fire({
                        title: isSubmoduleComplete ? '¡Submódulo Completado! 🏆' : '¡Canción Superada! 🎉',
                        text: isSubmoduleComplete
                            ? '¡Completaste todas las canciones de este nivel!'
                            : `Puntaje: ${globalScore}%. ${totalSongs - songsCompleted.size} canción(es) restante(s).`,
                        icon: 'success',
                        confirmButtonText: isSubmoduleComplete ? 'Volver al Dashboard' : 'Siguiente canción',
                        confirmButtonColor: '#4F46E5',
                        allowOutsideClick: false,
                    }).then((result) => {
                        if (result.isConfirmed) {
                            if (isSubmoduleComplete) {
                                window.location.href = DASHBOARD_URL;
                            } else {
                                const next = findNextIncomplete();
                                if (next !== -1) initSong(next);
                            }
                        }
                    });
                });
            }

            karaokeBtn.textContent = "🎤 Practicar línea actual";
            karaokeBtn.style.background = "var(--secondary)";
        };

        recognition.onerror = (e) => {
            karaokeStatus.textContent = `Error: ${e.error}`;
            karaokeBtn.textContent = "🎤 Practicar línea actual";
            karaokeBtn.style.background = "var(--secondary)";
        };

        recognition.onend = () => {
            if (karaokeBtn.textContent.includes("Escuchando")) {
                karaokeBtn.textContent = "🎤 Practicar línea actual";
                karaokeBtn.style.background = "var(--secondary)";
                karaokeStatus.textContent = "No se escuchó nada. Intenta de nuevo.";
            }
        };
    } else if (karaokeStatus) {
        karaokeStatus.textContent = "Tu navegador no soporta evaluación de voz.";
    }

    // ─── SONG NAVIGATION ───────────────────────────────────────────────────
    const findNextIncomplete = () => {
        for (let i = 0; i < totalSongs; i++) {
            if (!songsCompleted.has(CANCIONES[i].id)) return i;
        }
        return -1;
    };

    btnPrev.addEventListener('click', () => {
        if (currentSongIndex > 0) initSong(currentSongIndex - 1);
    });

    btnNext.addEventListener('click', () => {
        if (currentSongIndex < totalSongs - 1) initSong(currentSongIndex + 1);
    });

    // ─── BOOT ──────────────────────────────────────────────────────────────
    initSong(0);
});
