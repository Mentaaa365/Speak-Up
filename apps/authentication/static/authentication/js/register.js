/**
 * Lógica de validación para HU-01 / RF-01 (Registro)
 * Controla los requisitos de la contraseña e inhabilita el botón de envío
 * según los criterios de aceptación del diseño técnico.
 */
document.addEventListener('DOMContentLoaded', () => {
    const nameInput = document.getElementById('name-input');
    const emailInput = document.getElementById('email-input');
    const instInput = document.getElementById('inst-input');
    const passwordInput = document.getElementById('password-input');
    const submitBtn = document.getElementById('submit-btn');
    const emailError = document.getElementById('email-error');

    // Elementos del checklist de la contraseña
    const reqLength = document.getElementById('req-length');
    const reqUpper = document.getElementById('req-upper');
    const reqNumber = document.getElementById('req-number');

    function actualizarIndicador(elemento, cumple) {
        const iconSpan = elemento.querySelector('.icon');
        if (cumple) {
            elemento.style.color = 'var(--secondary)';
            iconSpan.textContent = '✓';
        } else {
            elemento.style.color = 'var(--danger)';
            iconSpan.textContent = '✗';
        }
    }

    function validarFormulario() {
        const nameVal = nameInput.value.trim();
        const emailVal = emailInput.value.trim();
        const instVal = instInput.value.trim();
        const passVal = passwordInput.value;

        // 1. Validar Formato de Correo
        const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal);
        if (emailVal !== "" && !emailValido) {
            emailError.style.display = 'block';
            emailInput.style.borderColor = 'var(--danger)';
        } else {
            emailError.style.display = 'none';
            emailInput.style.borderColor = emailValido ? 'var(--secondary)' : 'var(--g200)';
        }

        // 2. Validar Criterios de Contraseña individualmente
        const tieneLargo = passVal.length >= 8;
        const tieneMayuscula = /[A-Z]/.test(passVal);
        const tieneNumero = /[0-9]/.test(passVal);

        actualizarIndicador(reqLength, tieneLargo);
        actualizarIndicador(reqUpper, tieneMayuscula);
        actualizarIndicador(reqNumber, tieneNumero);

        const passwordValida = tieneLargo && tieneMayuscula && tieneNumero;

        // 3. Control del Estado del Botón de Envío (Paso 3 de la Secuencia Normal)
        if (nameVal.length > 0 && emailValido && instVal.length > 0 && passwordValida) {
            submitBtn.disabled = false;
            submitBtn.style.background = 'var(--primary)';
            submitBtn.style.color = '#FFFFFF';
            submitBtn.style.cursor = 'pointer';
        } else {
            submitBtn.disabled = true;
            submitBtn.style.background = 'var(--g300)';
            submitBtn.style.color = 'var(--g500)';
            submitBtn.style.cursor = 'not-allowed';
        }
    }

    // Escuchadores de eventos para validación reactiva en tiempo real
    const inputs = [nameInput, emailInput, instInput, passwordInput];
    inputs.forEach(input => {
        if (input) {
            input.addEventListener('input', validarFormulario);
        }
    });
});