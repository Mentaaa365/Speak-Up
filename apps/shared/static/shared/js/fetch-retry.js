function fetchWithRetry(url, options, maxRetries = 3) {
    let attempt = 0;
    const execute = () => {
        attempt++;
        return fetch(url, options).then(response => {
            if (!response.ok && attempt < maxRetries) return execute();
            return response;
        }).catch(error => {
            if (attempt < maxRetries) return execute();
            throw error;
        });
    };
    return execute();
}
