document.addEventListener('DOMContentLoaded', () => {
    if (typeof CANCIONES === 'undefined' || CANCIONES.length === 0) {
        document.getElementById('song-title').textContent = 'No hay canciones disponibles.';
        return;
    }

    const currentSong = CANCIONES[0];
    document.getElementById('song-title').textContent = currentSong.titulo;

    const audioPlayer = document.getElementById('audio-player');
    const lyricsContainer = document.getElementById('lyrics-container');

    const audioUrl = currentSong.config.audio_url || '';
    const lrcText = currentSong.config.lrc || '';

    if (!audioUrl) {
        lyricsContainer.innerHTML = '<p style="color:red;">Error: Falla el enlace de audio.</p>';
        return;
    }

    audioPlayer.src = audioUrl;

    // ─── 1. PARSEAR EL ARCHIVO LRC ─────────────────────────────────────────
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
                parsed.push({ time: minutes * 60 + seconds, text: text });
            }
        });
        return parsed;
    };

    const lyricsData = parseLRC(lrcText);

    // ─── 2. RENDERIZAR LAS LÍNEAS ──────────────────────────────────────────
    if (lyricsData.length > 0) {
        lyricsContainer.innerHTML = lyricsData.map((line, index) => 
            `<p id="line-${index}" style="font-size: 20px; color: var(--g400); margin: 12px 0; transition: all 0.3s ease;">
                ${line.text || '🎵'}
            </p>`
        ).join('');
    }

    // ─── 3. SINCRONIZAR CON EL AUDIO ───────────────────────────────────────
    let currentLineIndex = -1;

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
                if (oldLine) {
                    oldLine.style.color = 'var(--g400)';
                    oldLine.style.fontWeight = '400';
                    oldLine.style.transform = 'scale(1)';
                }
            }

            const newLine = document.getElementById(`line-${activeIndex}`);
            if (newLine) {
                newLine.style.color = 'var(--primary)'; // Azul principal
                newLine.style.fontWeight = '800';
                newLine.style.transform = 'scale(1.1)';
                newLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            currentLineIndex = activeIndex;
        }
    });

    // ─── 4. MOTOR DE KARAOKE ACTIVO (SISTEMA DE RACHA - 4 LÍNEAS) ──────────
    const karaokeBtn = document.getElementById('karaoke-btn');
    const karaokeStatus = document.getElementById('karaoke-status');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition && karaokeBtn) {
        karaokeBtn.style.display = 'inline-block';
    } else if (karaokeStatus) {
        karaokeStatus.textContent = "Tu navegador no soporta evaluación de voz.";
    }

    const score = (transcript, target) => {
        const cleanT = transcript.toLowerCase().replace(/[.,!?¿¡()]/g, '').trim().split(/\s+/);
        const cleanA = target.toLowerCase().replace(/[.,!?¿¡()]/g, '').trim().split(/\s+/);
        let correct = 0;
        cleanA.forEach((w, i) => { if (cleanT[i] === w) correct++; });
        return Math.round((correct / cleanA.length) * 100);
    };

    const guardarProgreso = (puntaje, transcripcion) => {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        fetch(GUARDAR_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                ejercicio_id: currentSong.id,
                puntaje: puntaje,
                transcripcion: transcripcion,
            }),
        }).then(r => r.json()).catch(err => console.error("Error al guardar:", err));
    };

    // 🔥 VARIABLES PARA EL SISTEMA DE RACHAS
    let rachaActual = 0;
    let ultimaLineaCantada = -1;

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
            const activeLineElement = document.getElementById(`line-${currentLineIndex}`);
            
            if (puntaje >= 80) {
                // Verificar si es la línea inmediatamente siguiente a la anterior
                if (rachaActual === 0 || currentLineIndex === ultimaLineaCantada + 1) {
                    rachaActual++;
                } else if (currentLineIndex !== ultimaLineaCantada) {
                    // Si saltó a otra parte de la canción, la racha empieza de nuevo en 1
                    rachaActual = 1; 
                }

                ultimaLineaCantada = currentLineIndex;

                activeLineElement.style.color = "#10B981"; // Verde
                karaokeStatus.innerHTML = `✅ ¡Perfecto! (${puntaje}%). <br><span style="color: #F59E0B; font-weight: bold; font-size: 16px;">🔥 Racha: ${rachaActual}/4</span>`;
                
                // CONDICIÓN DE VICTORIA
                if (rachaActual === 4) {
                    karaokeStatus.innerHTML = `🎉 <strong>¡ESTROFA COMPLETADA!</strong> Has demostrado un excelente dominio.`;
                    karaokeBtn.style.display = "none"; // Ocultamos el botón

                    // 1. Disparar explosión de confeti
                    confetti({
                        particleCount: 150,
                        spread: 80,
                        origin: { y: 0.6 },
                        colors: ['#4F46E5', '#10B981', '#F59E0B', '#EF4444']
                    });

                    // 2. Mostrar la alerta animada y moderna
                    Swal.fire({
                        title: '¡Módulo Superado! 🏆',
                        text: '¡Cantaste una estrofa completa a la perfección!',
                        icon: 'success',
                        confirmButtonText: 'Volver al Dashboard',
                        confirmButtonColor: '#4F46E5', // Tu color azul principal
                        background: '#ffffff',
                        backdrop: `rgba(0,0,10,0.4)`, // Fondo oscuro elegante
                        allowOutsideClick: false, // Obliga a darle al botón
                        showClass: {
                            popup: 'animate__animated animate__bounceIn'
                        }
                    }).then((result) => {
                        // 3. Redirigir al dashboard cuando hagan clic en el botón
                        if (result.isConfirmed) {
                            window.location.href = '/learning/dashboard'; // Cambia esta URL si la tuya es diferente
                        }
                    });
                }

            } else {
                // Si falla el 80%, la racha muere
                rachaActual = 0;
                activeLineElement.style.color = "#F59E0B"; // Naranja
                karaokeStatus.innerHTML = `⚠️ Fallaste (${puntaje}%). Dijiste: "${transcript}". <br><span style="color: red; font-weight: bold;">❌ Racha perdida. Vuelve a empezar.</span>`;
            }

            guardarProgreso(puntaje, transcript);
            
            if (rachaActual < 4) {
                karaokeBtn.textContent = "🎤 Practicar línea actual";
                karaokeBtn.style.background = "var(--secondary)";
            }
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
    }
});