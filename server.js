// ============================================================
// IMMEDIATE PORT BINDING — Railway Metal requires < 5s response
// ============================================================
require('dotenv').config();
const express = require('express');
const path = require('path');
const fs = require('fs');
const app = express();
const PORT = process.env.PORT || 3000;

// Health check responds before anything else loads
app.get('/healthz', (req, res) => res.status(200).send('ok'));

// Bind port FIRST — before loading any heavy modules
const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Alex: Sales Agent live on port ${PORT}`);
});
server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        app.listen(PORT + 1, '0.0.0.0', () => console.log(`🚀 Fallback port ${PORT + 1}`));
    } else { console.error('❌ Server error:', err.message); process.exit(1); }
});

// ============================================================
// Now load heavy modules (port is already open)
// ============================================================
const nunjucks = require('nunjucks');
const session = require('express-session');
const bcrypt = require('bcryptjs');
let createClient, Groq, Telegraf;
try { ({ createClient } = require('@supabase/supabase-js')); } catch(e) { console.warn('⚠️  supabase-js not available'); }
try { ({ Groq } = require('groq-sdk')); } catch(e) { console.warn('⚠️  groq-sdk not available'); }
try { ({ Telegraf } = require('telegraf')); } catch(e) { console.warn('⚠️  telegraf not available'); }
app.set('trust proxy', 1); // Railway is behind a reverse proxy
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Session middleware
app.use(session({
    secret: process.env.SESSION_SECRET || 'openhuman-secret-key-change-me',
    resave: false,
    saveUninitialized: false,
    proxy: true,
    cookie: { secure: process.env.NODE_ENV === 'production' ? true : false, maxAge: 7 * 24 * 60 * 60 * 1000, sameSite: 'lax' }
}));

// Absolute static pathing – serves CSS/JS/images with correct MIME types
app.use('/static', express.static(path.join(__dirname, 'static'), {
    setHeaders(res, filePath) {
        if (filePath.endsWith('.css'))  res.setHeader('Content-Type', 'text/css');
        if (filePath.endsWith('.js'))   res.setHeader('Content-Type', 'application/javascript');
    }
}));
app.use('/templates', express.static(path.join(__dirname, 'templates')));

// Configure Nunjucks with absolute template path (Jinja2-compatible)
nunjucks.configure(path.join(__dirname, 'templates'), {
    autoescape: true,
    express: app,
    watch: false,
    noCache: process.env.NODE_ENV !== 'production'
});
app.set('view engine', 'html');

// ============================================================
// Simple JSON-based user store
// ============================================================
const USERS_FILE = path.join(__dirname, 'users.json');
const APP_PASSWORD = (process.env.APP_PASSWORD || '').trim();
const ADMIN_EMAIL_ENV = (process.env.ADMIN_EMAIL || '').trim().toLowerCase();
const GOOGLE_CLIENT_ID = (process.env.GOOGLE_CLIENT_ID || '').trim();
const GOOGLE_CLIENT_SECRET = (process.env.GOOGLE_CLIENT_SECRET || '').trim();
const googleOAuthEnabled = !!(GOOGLE_CLIENT_ID && GOOGLE_CLIENT_SECRET);

// Supabase client for auth
const SUPABASE_URL = (process.env.SUPABASE_URL || '').trim();
const SUPABASE_ANON_KEY = (process.env.SUPABASE_ANON_KEY || '').trim();
const supabase = (SUPABASE_URL && SUPABASE_ANON_KEY)
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : null;
if (supabase) console.log('✅ Supabase auth connected');
else console.warn('⚠️  SUPABASE_URL/SUPABASE_ANON_KEY missing – using local auth fallback');

function loadUsers() {
    try { return JSON.parse(fs.readFileSync(USERS_FILE, 'utf8')); }
    catch (e) { return []; }
}
function saveUsers(users) {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}
function findUser(email) {
    return loadUsers().find(u => u.email === email.toLowerCase());
}

// Auth middleware
function requireLogin(req, res, next) {
    if (req.session && req.session.user) return next();
    return res.redirect('/login');
}
function requireAdmin(req, res, next) {
    if (req.session && req.session.user && req.session.user.is_admin) return next();
    return res.redirect('/login');
}

// ============================================================
// Public pages
// ============================================================
app.get('/', (req, res) => res.render('landing.html', {}));
app.get('/about', (req, res) => res.render('about.html', {}));
app.get('/contact', (req, res) => res.render('contact.html', {}));
app.get('/help', (req, res) => res.render('help.html', {}));
app.get('/privacy', (req, res) => res.render('privacy.html', {}));
app.get('/terms', (req, res) => res.render('terms.html', {}));
app.get('/compliance', (req, res) => res.render('compliance.html', {}));
app.get('/blog', (req, res) => res.render('blog_page.html', {}));

// ============================================================
// Auth routes: Login, Signup, Logout
// ============================================================
app.get('/login', (req, res) => {
    if (req.session && req.session.user) return res.redirect('/index');
    res.render('login.html', { signup: false, error: null, info_message: null, google_oauth: googleOAuthEnabled, app_password_set: !!APP_PASSWORD });
});

app.get('/signup', (req, res) => {
    if (req.session && req.session.user) return res.redirect('/index');
    res.render('login.html', { signup: true, error: null, info_message: null, google_oauth: googleOAuthEnabled, app_password_set: !!APP_PASSWORD });
});

app.post('/signup', async (req, res) => {
    const { name, email, password, confirm_password } = req.body;
    const renderErr = (err) => res.render('login.html', { signup: true, error: err, info_message: null, google_oauth: googleOAuthEnabled, app_password_set: !!APP_PASSWORD });

    if (!email || !password) return renderErr('Email and password are required.');
    if (password.length < 8) return renderErr('Password must be at least 8 characters.');
    if (confirm_password && password !== confirm_password) return renderErr('Passwords do not match.');

    const cleanEmail = email.toLowerCase().trim();
    const displayName = (name || '').trim() || cleanEmail.split('@')[0];

    // Try Supabase first
    if (supabase) {
        try {
            const { data, error } = await supabase.auth.signUp({
                email: cleanEmail,
                password: password,
                options: { data: { display_name: displayName } }
            });
            if (error) return renderErr(error.message);

            // If email confirmation is required
            if (data.user && !data.session) {
                return res.render('login.html', { signup: false, error: null, info_message: 'Account created! Please check your email to confirm, then sign in.', google_oauth: googleOAuthEnabled, app_password_set: !!APP_PASSWORD });
            }

            // Auto-confirmed — save locally and login
            const users = loadUsers();
            const newUser = { id: users.length + 1, name: displayName, email: cleanEmail, password_hash: '', is_admin: cleanEmail === ADMIN_EMAIL_ENV, profile_image_url: null, profile_name: displayName, created_at: new Date().toISOString(), supabase_id: data.user?.id, leads: 0, calls: 0, active_number: 'None' };
            users.push(newUser);
            saveUsers(users);
            req.session.user = { id: newUser.id, email: newUser.email, name: newUser.name, is_admin: newUser.is_admin, profile_name: newUser.profile_name, profile_image_url: null };
            return res.redirect('/index');
        } catch (err) {
            console.error('Supabase signup error:', err.message);
            return renderErr('Signup failed: ' + err.message);
        }
    }

    // Fallback: local auth
    if (findUser(cleanEmail)) return renderErr('An account with this email already exists.');
    const users = loadUsers();
    const hash = bcrypt.hashSync(password, 10);
    const newUser = { id: users.length + 1, name: displayName, email: cleanEmail, password_hash: hash, is_admin: cleanEmail === ADMIN_EMAIL_ENV, profile_image_url: null, profile_name: displayName, created_at: new Date().toISOString(), leads: 0, calls: 0, active_number: 'None' };
    users.push(newUser);
    saveUsers(users);
    req.session.user = { id: newUser.id, email: newUser.email, name: newUser.name, is_admin: newUser.is_admin, profile_name: newUser.profile_name, profile_image_url: null };
    res.redirect('/index');
});

app.post('/login', async (req, res) => {
    const login_mode = req.body.login_mode || 'user';
    const isAjax = req.headers['x-requested-with'] === 'XMLHttpRequest';
    const sendSuccess = () => isAjax ? res.json({ success: true, redirect: '/index' }) : res.redirect('/index');
    const sendError = (err) => isAjax ? res.json({ success: false, error: err }) : res.render('login.html', { signup: false, error: err, info_message: null, google_oauth: googleOAuthEnabled, app_password_set: !!APP_PASSWORD });

    // Admin login via APP_PASSWORD
    if (login_mode === 'admin' && APP_PASSWORD) {
        const app_password = (req.body.app_password || '').trim();
        if (app_password === APP_PASSWORD) {
            let users = loadUsers();
            let admin = users.find(u => u.email === 'admin@openhuman.local');
            if (!admin) {
                admin = { id: users.length + 1, name: 'Admin', email: 'admin@openhuman.local', password_hash: bcrypt.hashSync(APP_PASSWORD, 10), is_admin: true, profile_name: 'Admin', profile_image_url: null, created_at: new Date().toISOString(), leads: 0, calls: 0, active_number: 'None' };
                users.push(admin);
                saveUsers(users);
            }
            req.session.user = { id: admin.id, email: admin.email, name: admin.name, is_admin: true, profile_name: 'Admin', profile_image_url: null };
            return sendSuccess();
        }
        return sendError('Invalid admin password.');
    }

    // Regular user login
    const { email, password } = req.body;
    if (!email || !password) return sendError('Please enter email and password.');
    const cleanEmail = email.toLowerCase().trim();

    // Try Supabase first
    if (supabase) {
        try {
            const { data, error } = await supabase.auth.signInWithPassword({ email: cleanEmail, password });
            if (error) return sendError(error.message);

            let users = loadUsers();
            let user = users.find(u => u.email === cleanEmail);
            if (!user) {
                user = { id: users.length + 1, name: cleanEmail.split('@')[0], email: cleanEmail, password_hash: '', is_admin: cleanEmail === ADMIN_EMAIL_ENV, profile_image_url: null, profile_name: data.user?.user_metadata?.display_name || cleanEmail.split('@')[0], created_at: new Date().toISOString(), supabase_id: data.user?.id, leads: 0, calls: 0, active_number: 'None' };
                users.push(user);
                saveUsers(users);
            }
            req.session.user = { id: user.id, email: user.email, name: user.name, is_admin: user.is_admin || cleanEmail === ADMIN_EMAIL_ENV, profile_name: user.profile_name, profile_image_url: user.profile_image_url };
            return sendSuccess();
        } catch (err) {
            console.error('Supabase login error:', err.message);
            return sendError('Login failed: ' + err.message);
        }
    }

    // Fallback: local auth
    const user = findUser(cleanEmail);
    if (!user || !bcrypt.compareSync(password, user.password_hash)) {
        return sendError('Invalid email or password.');
    }
    req.session.user = { id: user.id, email: user.email, name: user.name, is_admin: user.is_admin || user.email === ADMIN_EMAIL_ENV, profile_name: user.profile_name, profile_image_url: user.profile_image_url };
    sendSuccess();
});

app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

// ============================================================
// Google OAuth Login
// ============================================================
if (googleOAuthEnabled) {
    app.get('/google_login', (req, res) => {
        const redirectUri = `${req.protocol}://${req.get('host')}/google_callback`;
        const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=select_account`;
        res.redirect(url);
    });

    app.get('/google_callback', async (req, res) => {
        const { code } = req.query;
        if (!code) return res.redirect('/login');

        try {
            const redirectUri = `${req.protocol}://${req.get('host')}/google_callback`;
            // Exchange code for tokens
            const tokenResp = await fetch('https://oauth2.googleapis.com/token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    code, client_id: GOOGLE_CLIENT_ID, client_secret: GOOGLE_CLIENT_SECRET,
                    redirect_uri: redirectUri, grant_type: 'authorization_code'
                })
            });
            const tokenData = await tokenResp.json();
            if (!tokenData.access_token) throw new Error('No access token');

            // Get user info
            const userResp = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
                headers: { Authorization: `Bearer ${tokenData.access_token}` }
            });
            const profile = await userResp.json();
            if (!profile.email) throw new Error('No email from Google');

            // Find or create user
            let users = loadUsers();
            let user = users.find(u => u.email === profile.email.toLowerCase());
            if (!user) {
                user = {
                    id: users.length + 1,
                    name: profile.name || profile.email.split('@')[0],
                    email: profile.email.toLowerCase(),
                    password_hash: '',
                    is_admin: profile.email.toLowerCase() === ADMIN_EMAIL_ENV,
                    profile_image_url: profile.picture || null,
                    profile_name: profile.name || profile.email.split('@')[0],
                    created_at: new Date().toISOString(),
                    leads: 0, calls: 0, active_number: 'None'
                };
                users.push(user);
                saveUsers(users);
            }

            req.session.user = { id: user.id, email: user.email, name: user.name, is_admin: user.is_admin || user.email === ADMIN_EMAIL_ENV, profile_name: user.profile_name, profile_image_url: user.profile_image_url || profile.picture };
            res.redirect('/index');
        } catch (err) {
            console.error('Google OAuth error:', err.message);
            res.render('login.html', { signup: false, error: 'Google login failed. Please try again.', info_message: null, google_oauth: googleOAuthEnabled, app_password_set: !!APP_PASSWORD });
        }
    });
} else {
    app.get('/google_login', (req, res) => res.redirect('/login'));
}

// ============================================================
// Protected pages
// ============================================================
app.get('/index', requireLogin, (req, res) => {
    res.render('index.html', { user: req.session.user, secure_from: '' });
});

app.get('/verify-otp', (req, res) => res.render('verify_otp.html', { email: '', error: null }));

app.get('/profile-setup', requireLogin, (req, res) => {
    res.render('profile_setup.html', { user: req.session.user });
});

app.get('/super-admin', requireAdmin, (req, res) => {
    const users = loadUsers().map(u => ({
        id: u.id,
        name: u.profile_name || u.name || 'Unknown',
        email: u.email,
        leads: u.leads || 0,
        calls: u.calls || 0,
        active_number: u.active_number || 'None',
        created_at: u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'
    }));
    res.render('super_admin.html', { users: users });
});

// (Port already bound at top of file)

// ============================================================
// Non-blocking service initialization (after port is open)
// ============================================================
const GROQ_API_KEY = (process.env.GROQ_API_KEY || '').trim();
const BOT_TOKEN = (process.env.BOT_TOKEN || '').trim();
const ADMIN_CHAT_ID = (process.env.ADMIN_CHAT_ID || '').trim();

const groq = GROQ_API_KEY ? new Groq({ apiKey: GROQ_API_KEY }) : null;
const bot = BOT_TOKEN ? new Telegraf(BOT_TOKEN) : null;

if (!groq) console.warn('⚠️  GROQ_API_KEY missing – chat disabled.');
if (!bot) console.warn('⚠️  BOT_TOKEN missing – Telegram disabled.');

// Resend email SDK (replaces Nodemailer)
const { Resend } = require('resend');
const RESEND_API_KEY = (process.env.RESEND_API_KEY || '').trim();
const resend = RESEND_API_KEY ? new Resend(RESEND_API_KEY) : null;

if (resend) console.log('✅ Resend email SDK initialized');
else console.warn('⚠️  RESEND_API_KEY missing – email features disabled');

app.post('/api/lead', async (req, res) => {
    const { name, phone, email, company } = req.body;
    if (!name || !email) {
        return res.status(400).json({ error: 'Name and email are required.' });
    }

    // Send Telegram notification to admin
    if (bot && ADMIN_CHAT_ID) {
        bot.telegram.sendMessage(ADMIN_CHAT_ID,
            `🔥 **New Lead Captured**\n\nName: ${name}\nPhone: ${phone || 'N/A'}\nEmail: ${email}\nCompany: ${company || 'N/A'}`
        ).catch(err => console.error('Telegram lead error:', err.message));
    }

    // Send "Digital Resume" email via Resend (no attachments, pure HTML)
    if (resend) {
        try {
            const onboardingUrl = 'https://openhumana.com/onboarding';
            const logoUrl = 'https://openhumana.com/static/images/logo.png';

            const html = `
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7f6;padding:24px 0;">
              <tr>
                <td align="center">
                  <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:#1a202c;box-shadow:0 10px 30px rgba(0,0,0,0.06);">
                    <tr>
                      <td align="center" style="padding:28px 24px 12px 24px;">
                        <img src="${logoUrl}" alt="Open Humana" style="max-width:180px;height:auto;display:block;" />
                      </td>
                    </tr>
                    <tr>
                      <td align="center" style="padding:4px 24px 24px 24px;">
                        <div style="font-size:22px;font-weight:700;letter-spacing:0.2px;">Alex: Senior Digital Associate</div>
                        <div style="margin-top:6px;font-size:15px;color:#4a5568;">Reclaiming your hours, one lead at a time.</div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 32px 8px 32px;">
                        <p style="margin:0;font-size:14px;line-height:1.7;color:#1a202c;">Dear ${name}, Thank you for your interest in Open Humana. I am not a tool; I am the recovery of your wasted time. I take the exhaustion of the workday so you can live life—vacations, adventure, and family.</p>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:24px 32px 12px 32px;">
                        <div style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#1a202c;">Core Competencies</div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 24px 8px 24px;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                          <tr>
                            ${[
                              { title: 'Extreme Persistence', desc: '12+ touchpoints per lead without fatigue.' },
                              { title: 'Voice Execution', desc: 'Hyper-personalized voicemails that sound human.' },
                              { title: 'Instant Bridge', desc: '200ms connection speed to your desk.' }
                            ].map(item => `
                              <td width="33.33%" style="vertical-align:top;padding:0 8px 16px 8px;">
                                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px;">
                                  <div style="font-size:14px;font-weight:700;color:#1a202c;">${item.title}</div>
                                  <div style="margin-top:6px;font-size:13px;line-height:1.6;color:#4a5568;">${item.desc}</div>
                                </div>
                              </td>
                            `).join('')}
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:8px 32px 12px 32px;">
                        <div style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#1a202c;">The Candidate Advantage</div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 24px 24px 24px;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
                          <tr style="background:#f8fafc;">
                            <th align="left" style="padding:12px 14px;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;color:#1a202c;border-bottom:1px solid #e2e8f0;">Comparison</th>
                            <th align="left" style="padding:12px 14px;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;color:#1a202c;border-bottom:1px solid #e2e8f0;">Open Humana</th>
                            <th align="left" style="padding:12px 14px;font-size:13px;text-transform:uppercase;letter-spacing:0.5px;color:#1a202c;border-bottom:1px solid #e2e8f0;">Legacy Staff</th>
                          </tr>
                          ${[
                            { label: 'Management', oh: 'Zero overhead', legacy: 'Constant supervision' },
                            { label: 'Activity', oh: '24/7/365', legacy: '40-hour weeks' },
                            { label: 'Cost', oh: '$99/mo (Flat Fee)', legacy: 'Salaries + Benefits' }
                          ].map(row => `
                            <tr>
                              <td style="padding:12px 14px;font-size:13px;color:#1a202c;border-bottom:1px solid #e2e8f0;">${row.label}</td>
                              <td style="padding:12px 14px;font-size:13px;color:#3182ce;font-weight:700;border-bottom:1px solid #e2e8f0;">${row.oh}</td>
                              <td style="padding:12px 14px;font-size:13px;color:#4a5568;border-bottom:1px solid #e2e8f0;">${row.legacy}</td>
                            </tr>
                          `).join('')}
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td align="center" style="padding:8px 24px 32px 24px;">
                        <a href="${onboardingUrl}" style="display:inline-block;background:#3182ce;color:#ffffff;text-decoration:none;padding:14px 26px;border-radius:999px;font-size:15px;font-weight:700;box-shadow:0 8px 20px rgba(49,130,206,0.35);">
                          Finalize My Onboarding &amp; Reclaim My Time
                        </a>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:0 32px 32px 32px;">
                        <p style="margin:0;font-size:12px;line-height:1.6;color:#718096;">Company: ${company || 'N/A'} | Phone: ${phone || 'N/A'}</p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>`;

            const { data, error: sendErr } = await resend.emails.send({
                from: 'Alex <alex@openhumana.com>',
                to: [email],
                subject: 'Alex’s Credentials — Your New Era of Productivity Starts Now',
                html
            });

            if (sendErr) {
                console.error('Resend error:', sendErr);
            } else {
                console.log(`📧 Digital Resume email sent to ${email} (Resend ID: ${data?.id})`);
            }
        } catch (err) {
            console.error('Email send error:', err.message);
        }
    }

    res.json({ success: true, message: 'Thanks! We\'ll be in touch within 15 minutes.' });
});

// 3. Alex's Sales Job (Website Chat)
app.post('/api/chat', async (req, res) => {
    const { message } = req.body;
    if (!groq) {
        return res.status(503).json({ error: "Chat service is not configured (missing GROQ_API_KEY)." });
    }
    try {
        // JOB 1: THE SALES AGENT (Talk to website user)
        const completion = await groq.chat.completions.create({
            messages: [
                { role: "system", content: "You are Alex, a high-performance Digital BDR for Open Humana. Be professional and drive sales." },
                { role: "user", content: message }
            ],
            model: "llama-3.1-8b-instant",
        });

        const alexReply = completion.choices[0].message.content;

        // JOB 2: THE REPORTER (Ping the Digital Office)
        if (bot && ADMIN_CHAT_ID) {
            bot.telegram.sendMessage(ADMIN_CHAT_ID, 
                `💼 **Alex Interaction Report**\n\nLead said: "${message}"\n\nAlex replied: "${alexReply}"`
            ).catch(err => console.error("Telegram error:", err.message));
        }

        res.json({ reply: alexReply });
    } catch (error) {
        console.error("Alex Glitch:", error);
        res.status(500).json({ error: "Alex is taking a short break." });
    }
});

// 4. Alex's Two-Way Telegram Intelligence (Digital Chief of Staff)
if (bot) {
    const ADMIN_SYSTEM_PROMPT = 'You are Alex, the man in charge of the OpenHumana Digital Office. You are speaking to your CEO. Be professional, witty, and report on the digital office status when asked. Keep responses concise but insightful.';

    bot.on('text', async (ctx) => {
        const senderId = String(ctx.chat.id);

        // Safety Guard: only the boss can talk to Alex
        if (senderId !== ADMIN_CHAT_ID) {
            return ctx.reply('👋 Hey there! I\'m Alex, the Digital Chief of Staff at Open Humana. I only take orders from the CEO. Visit openhumana.com if you\'d like to learn more!');
        }

        // Boss detected — route to Groq AI with Admin persona
        if (!groq) {
            return ctx.reply('⚠️ Boss, my brain (Groq API) is offline. Check the GROQ_API_KEY in Railway.');
        }

        try {
            const completion = await groq.chat.completions.create({
                messages: [
                    { role: 'system', content: ADMIN_SYSTEM_PROMPT },
                    { role: 'user', content: ctx.message.text }
                ],
                model: 'llama-3.1-8b-instant',
            });

            const reply = completion.choices[0].message.content;
            await ctx.reply(reply);
        } catch (err) {
            console.error('Alex Admin Glitch:', err.message);
            await ctx.reply('😅 Sorry boss, I hit a snag. Give me a sec and try again.');
        }
    });
}

// 5. Launch Telegram bot in background (non-blocking, after port is already open)
if (bot) {
    bot.launch()
        .then(() => console.log('✅ Alex: Connected to Telegram'))
        .catch(err => console.error('❌ Telegram failed:', err.message));
}

// Graceful shutdown
process.once('SIGINT', () => { if (bot) bot.stop('SIGINT'); process.exit(0); });
process.once('SIGTERM', () => { if (bot) bot.stop('SIGTERM'); process.exit(0); });
