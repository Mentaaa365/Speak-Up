document.addEventListener('DOMContentLoaded', () => {
    const micStatusBox = document.getElementById('mic-status-box');
    const micIcon = document.getElementById('mic-icon');
    const micTitle = document.getElementById('mic-title');
    const micDesc = document.getElementById('mic-desc');
    const startBtn = document.getElementById('start-test-btn');

    async function checkMicrophone() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            micStatusBox.style.background = 'var(--secondary-light)';
            micStatusBox.style.borderColor = 'var(--secondary)';
            micIcon.textContent = '🎤';
            micTitle.textContent = 'Microphone ready and detected! ✓';
            micDesc.textContent = 'Hardware levels are stable. You can now start the diagnostic test.';

            startBtn.disabled = false;
            startBtn.textContent = 'Start Exam';
            startBtn.style.background = 'var(--primary)';
            startBtn.style.color = '#FFFFFF';
            startBtn.style.cursor = 'pointer';

            stream.getTracks().forEach(track => track.stop());

            startBtn.addEventListener('click', () => {
                window.location.href = '/diagnosis/test/';
            });

        } catch (error) {
            console.warn('Hardware access denied:', error);
            micStatusBox.style.background = 'var(--danger-light)';
            micStatusBox.style.borderColor = 'var(--danger)';
            micIcon.textContent = '❌';
            micTitle.textContent = 'Microphone access blocked';
            micDesc.innerHTML = 'The exam requires active recording hardware. <strong>Instructions to continue:</strong><br>' +
                                '1. In <strong>Google Chrome / Firefox</strong>: click the lock icon next to the URL (127.0.0.1).<br>' +
                                '2. Change the "Microphone" permission from "Block" to "Allow".<br>' +
                                '3. Reload the page (F5).';

            startBtn.disabled = true;
            startBtn.textContent = 'Waiting for audio hardware...';
            startBtn.style.background = 'var(--g300)';
            startBtn.style.color = 'var(--g500)';
            startBtn.style.cursor = 'not-allowed';
        }
    }

    checkMicrophone();
});
