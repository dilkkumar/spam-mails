document.getElementById('checkSpam').addEventListener('click', () => {
    chrome.tabs.executeScript({
        code: "window.getSelection().toString();"
    }, (selection) => {
        fetch('http://13.233.121.132:5000/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `email_content=${encodeURIComponent(selection[0])}`
        })
        .then(response => response.json())
        .then(data => {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: data.is_spam ? 'SPAM DETECTED!' : 'Safe Email',
                message: `Confidence: ${data.probability}%`
            });
        })
        .catch(error => {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: 'Error',
                message: 'Could not contact the server.'
            });
            console.error('Fetch error:', error);
        });
    });
});
