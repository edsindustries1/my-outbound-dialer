const fs = require('fs');
const path = require('path');

const memoryPath = path.join(__dirname, 'history.json');

// Initialize the history file if it doesn't exist
if (!fs.existsSync(memoryPath)) {
    fs.writeFileSync(memoryPath, JSON.stringify({}));
}

function getHistory(userId) {
    const data = JSON.parse(fs.readFileSync(memoryPath));
    return data[userId] || [];
}

function saveHistory(userId, message, response) {
    const data = JSON.parse(fs.readFileSync(memoryPath));
    if (!data[userId]) data[userId] = [];
    
    // Add the new interaction
    data[userId].push({ role: 'user', content: message });
    data[userId].push({ role: 'assistant', content: response });

    // Keep only the last 10 messages so the brain doesn't get overwhelmed
    if (data[userId].length > 20) data[userId] = data[userId].slice(-20);

    fs.writeFileSync(memoryPath, JSON.stringify(data, null, 2));
}

module.exports = { getHistory, saveHistory };