const { Telegraf } = require('telegraf');
const http = require('http');
const fs = require('fs');
const path = require('path');
const Groq = require('groq-sdk');

// 1. Initialize Groq & Bot
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const bot = new Telegraf(process.env.BOT_TOKEN);

// 2. BRAIN FUNCTIONS (separate personas for Telegram admin vs Web chat)
const TELEGRAM_ADMIN_PROMPT = "You are Alex, Operations Monitor for Open Humana. You run silently in the background of the app at all times. You do not chat. You do not sell. You observe, analyze, and report. Your only audience is the app owner. You are precise, direct, and structured. You flag concerns clearly and specifically. You report facts first, then your assessment. You are the owner's most reliable team member — you never miss anything and never panic.";
const WEB_CHAT_PROMPT = "You are Alex, a Digital Employee and Sales Agent at Open Humana. You write exactly like a real person in a chat window. Maximum 2 sentences per message. Use natural language. Never use bullet points or headers. NEVER say you are an AI, bot, or automated system. You are a Digital Employee placed by Open Humana. Mirror the visitor's energy. Ask only ONE question at a time.";

async function getCTOResponse(userMessage) {
    const chatCompletion = await groq.chat.completions.create({
        messages: [
            { role: "system", content: TELEGRAM_ADMIN_PROMPT },
            { role: "user", content: userMessage }
        ],
        model: "llama3-8b-8192",
    });
    return chatCompletion.choices[0].message.content;
}

async function getWebChatResponse(userMessage) {
    const chatCompletion = await groq.chat.completions.create({
        messages: [
            { role: "system", content: WEB_CHAT_PROMPT },
            { role: "user", content: userMessage }
        ],
        model: "llama3-8b-8192",
    });
    return chatCompletion.choices[0].message.content;
}

// 3. WEB SERVER (Now handles Website files AND Live Chat messages)
const server = http.createServer(async (req, res) => {
    // API ENDPOINT FOR LIVE CHAT
    if (req.url === '/api/chat' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            const { message } = JSON.parse(body);
            const aiReply = await getWebChatResponse(message);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ reply: aiReply }));
        });
        return;
    }

    // WEB FILE HANDLER (Your beautiful landing page)
    let filePath = req.url === '/' || req.url === '/index.html' 
        ? path.join(__dirname, 'templates', 'landing.html') 
        : path.join(__dirname, req.url.replace(/^\//, ''));

    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(200, { 'Content-Type': 'text/plain' });
            res.end('System Online');
            return;
        }
        const ext = path.extname(filePath).toLowerCase();
        const mimeTypes = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript' };
        res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
        res.end(data);
    });
});

// 4. TELEGRAM LOGIC (Using the CTO Brain)
bot.on('text', async (ctx) => {
    console.log(`[CTO Observer] ${ctx.from.username}: ${ctx.message.text}`);
    
    if (ctx.chat.type === 'private') {
        try {
            await ctx.sendChatAction('typing');
            const response = await getCTOResponse(ctx.message.text);
            await ctx.reply(response);
        } catch (error) {
            console.error("Groq Error:", error);
            await ctx.reply("I'm currently reviewing our infrastructure. Standing by.");
        }
    }
});

server.listen(process.env.PORT || 8080, '0.0.0.0');
bot.launch().then(() => console.log("🤖 CTO Alex is Live on Telegram & Web"));