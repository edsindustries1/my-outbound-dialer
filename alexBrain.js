const Groq = require("groq-sdk");
const { getHistory, saveHistory } = require('./memory'); // Import your new memory tool

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

async function askAlex(userId, userMessage) {
    try {
        // 1. Pull the last 10 exchanges from the "journal"
        const history = getHistory(userId);
        
        // 2. Build the full conversation context
        const messages = [
            { 
                role: "system", 
                content: "You are Alex, the lead strategist for Open Humana. You remember previous context to provide better strategic advice." 
            },
            ...history, // This injects the past messages
            { role: "user", content: userMessage }
        ];

        // 3. Send the whole thread to Groq
        const chatCompletion = await groq.chat.completions.create({
            messages: messages,
            model: "llama-3.3-70b-versatile", // Or your preferred Groq model
        });

        const aiResponse = chatCompletion.choices[0].message.content;

        // 4. Save this new interaction to the journal
        saveHistory(userId, userMessage, aiResponse);

        return aiResponse;
    } catch (error) {
        console.error("Groq Brain Error:", error);
        return "My apologies, I'm having trouble accessing my memory banks right now.";
    }
}

module.exports = { askAlex };