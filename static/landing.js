/* ============================================================
   Open Humana – Landing Page JS
   Modules: nav, scroll animations, hero reveal, hero canvas,
            lead form modal, Alex chat, Reddit testimonials shuffle
   ============================================================ */

(function () {
  'use strict';

  /* ========== NAV SCROLL ========== */
  var nav = document.querySelector('.nav');
  var navProgress = document.getElementById('navProgress');

  function onScroll() {
    var scrollY = window.scrollY;
    if (nav) nav.classList.toggle('scrolled', scrollY > 60);
    if (navProgress) {
      var docH = document.documentElement.scrollHeight - window.innerHeight;
      var progress = docH > 0 ? Math.min(scrollY / docH, 1) : 0;
      navProgress.style.transform = 'scaleX(' + progress + ')';
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ========== MOBILE MENU ========== */
  var navMobile = document.getElementById('navMobile');
  var navLinks = document.getElementById('navLinks');

  if (navMobile && navLinks) {
    navMobile.addEventListener('click', function () {
      navMobile.classList.toggle('active');
      navLinks.classList.toggle('open');
    });
  }

  /* ========== NAV DROPDOWNS ========== */
  document.querySelectorAll('.nav-dropdown').forEach(function (dd) {
    var trigger = dd.querySelector('.nav-dropdown-trigger');
    if (!trigger) return;

    trigger.addEventListener('click', function (e) {
      e.preventDefault();
      var wasActive = dd.classList.contains('active');
      document.querySelectorAll('.nav-dropdown.active').forEach(function (d) { d.classList.remove('active'); });
      if (!wasActive) dd.classList.add('active');
    });

    dd.querySelectorAll('.mega-item[data-target]').forEach(function (item) {
      item.addEventListener('click', function () {
        var target = document.getElementById(item.dataset.target);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        dd.classList.remove('active');
        if (navLinks) navLinks.classList.remove('open');
        if (navMobile) navMobile.classList.remove('active');
      });
    });
  });

  document.addEventListener('click', function (e) {
    if (!e.target.closest('.nav-dropdown')) {
      document.querySelectorAll('.nav-dropdown.active').forEach(function (d) { d.classList.remove('active'); });
    }
  });

  /* ========== SCROLL ANIMATIONS ========== */
  var animEls = document.querySelectorAll('.anim-fade, .anim-up');

  if ('IntersectionObserver' in window && animEls.length) {
    animEls.forEach(function (el) {
      el.style.opacity = '0';
      el.style.transform = el.classList.contains('anim-up') ? 'translateY(32px)' : 'translateY(0)';
      el.style.transition = 'opacity .7s ease, transform .7s ease';
    });

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    animEls.forEach(function (el) { observer.observe(el); });
  }

  /* ========== HERO TITLE WORD REVEAL ========== */
  var titleWords = document.querySelectorAll('.title-word');
  if (titleWords.length) {
    var heroObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          titleWords.forEach(function (w) { w.classList.add('revealed'); });
          heroObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });
    var heroSection = document.querySelector('.hero');
    if (heroSection) heroObserver.observe(heroSection);
  }

  /* ========== HERO CANVAS (particle network) ========== */
  var canvas = document.getElementById('heroCanvas');
  if (canvas) {
    var ctx = canvas.getContext('2d');
    var particles = [];
    var particleCount = 50;

    function resizeCanvas() {
      canvas.width = canvas.parentElement.offsetWidth;
      canvas.height = canvas.parentElement.offsetHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    for (var i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.5 + 0.5,
        a: Math.random() * 0.3 + 0.05
      });
    }

    function drawParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var j = 0; j < particles.length; j++) {
        var p = particles[j];
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,' + p.a + ')';
        ctx.fill();
      }
      for (var a = 0; a < particles.length; a++) {
        for (var b = a + 1; b < particles.length; b++) {
          var dx = particles[a].x - particles[b].x;
          var dy = particles[a].y - particles[b].y;
          var dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[a].x, particles[a].y);
            ctx.lineTo(particles[b].x, particles[b].y);
            ctx.strokeStyle = 'rgba(255,255,255,' + (0.06 * (1 - dist / 120)) + ')';
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(drawParticles);
    }
    drawParticles();
  }

  /* ========== SMOOTH SCROLL FOR ANCHOR LINKS ========== */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var href = a.getAttribute('href');
      if (href === '#') return;
      var target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  /* ==========================================================
     LEAD FORM MODAL
     ========================================================== */
  var modalHTML =
    '<div class="lead-overlay" id="leadOverlay">' +
      '<div class="lead-backdrop" id="leadBackdrop"></div>' +
      '<div class="lead-modal" id="leadModal">' +
        '<button class="lead-close" id="leadClose"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>' +
        '<div class="lead-modal-inner">' +
          '<div class="lead-left">' +
            '<div class="lead-left-content">' +
              '<div class="lead-logo-wrap"><img src="/static/images/logo.png" alt="Open Humana" class="lead-logo-img"></div>' +
              '<h2>Hire Your First Digital Employee</h2>' +
              '<p>Get Alex\'s resume and see why 2,000+ sales teams trust Open Humana to scale their outbound.</p>' +
              '<div class="lead-features">' +
                '<div class="lead-feat"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> 3,000+ dials per day</div>' +
                '<div class="lead-feat"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> AI personalized voicemails</div>' +
                '<div class="lead-feat"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Live call transfer to your phone</div>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="lead-right">' +
            '<h3>Get Started</h3>' +
            '<p class="lead-right-sub">Fill in your details and we\'ll send Alex\'s resume to your inbox.</p>' +
            '<form class="lead-form" id="leadForm">' +
              '<div class="lead-field">' +
                '<label>Full Name *</label>' +
                '<div class="lead-input-wrap"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg><input type="text" name="name" required placeholder="John Smith"></div>' +
              '</div>' +
              '<div class="lead-field">' +
                '<label>Phone Number</label>' +
                '<div class="lead-input-wrap"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg><input type="tel" name="phone" placeholder="+1 (555) 000-0000"></div>' +
              '</div>' +
              '<div class="lead-field">' +
                '<label>Email Address *</label>' +
                '<div class="lead-input-wrap"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg><input type="email" name="email" required placeholder="john@company.com"></div>' +
              '</div>' +
              '<div class="lead-field">' +
                '<label>Company</label>' +
                '<div class="lead-input-wrap"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg><input type="text" name="company" placeholder="Acme Corp"></div>' +
              '</div>' +
              '<button type="submit" class="lead-submit" id="leadSubmit"><span>Get Alex\'s Resume</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></button>' +
            '</form>' +
            '<div class="lead-success" id="leadSuccess">' +
              '<div class="lead-success-icon" style="font-size:3rem;color:#22c55e;">&#10003;</div>' +
              '<h3>You\'re In!</h3>' +
              '<p>Check your email for Alex\'s resume. Our team will reach out within 15 minutes.</p>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';

  var modalContainer = document.createElement('div');
  modalContainer.innerHTML = modalHTML;
  document.body.appendChild(modalContainer);

  var leadOverlay = document.getElementById('leadOverlay');
  var leadBackdrop = document.getElementById('leadBackdrop');
  var leadModal = document.getElementById('leadModal');
  var leadClose = document.getElementById('leadClose');
  var leadForm = document.getElementById('leadForm');
  var leadSuccess = document.getElementById('leadSuccess');

  function openLeadModal() {
    leadOverlay.classList.add('active');
    setTimeout(function () { leadModal.classList.add('show'); }, 50);
    document.body.style.overflow = 'hidden';
  }
  function closeLeadModal() {
    leadModal.classList.remove('show');
    setTimeout(function () { leadOverlay.classList.remove('active'); }, 400);
    document.body.style.overflow = '';
  }

  leadClose.addEventListener('click', closeLeadModal);
  leadBackdrop.addEventListener('click', closeLeadModal);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeLeadModal(); });

  // data-open-lead buttons open lead modal
  document.querySelectorAll('[data-open-lead]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      openLeadModal();
    });
  });

  leadForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    var submitBtn = document.getElementById('leadSubmit');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<svg class="lead-spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg> Sending...';

    var formData = {
      name: leadForm.querySelector('[name="name"]').value.trim(),
      phone: leadForm.querySelector('[name="phone"]').value.trim(),
      email: leadForm.querySelector('[name="email"]').value.trim(),
      company: leadForm.querySelector('[name="company"]').value.trim()
    };

    try {
      await fetch('/api/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
    } catch (err) { /* still show success */ }

    leadForm.style.display = 'none';
    leadSuccess.style.display = 'flex';
    setTimeout(function () { leadSuccess.classList.add('show'); }, 50);

    setTimeout(closeLeadModal, 4000);
    setTimeout(function () {
      leadForm.style.display = '';
      leadSuccess.style.display = '';
      leadSuccess.classList.remove('show');
      leadForm.reset();
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>Get Alex\'s Resume</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
    }, 5000);
  });

  /* ==========================================================
     ALEX CHAT WIDGET
     ========================================================== */
  var chatHTML =
    '<div class="alex-chat-bubble" id="alexBubble">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>' +
      '<div class="alex-badge"></div>' +
    '</div>' +
    '<div class="alex-chat-window" id="alexWindow">' +
      '<div class="alex-chat-header">' +
        '<div class="alex-chat-avatar">A</div>' +
        '<div class="alex-chat-header-info">' +
          '<div class="alex-chat-header-name">Alex — Digital BDR</div>' +
          '<div class="alex-chat-header-status">Online now</div>' +
        '</div>' +
        '<button class="alex-chat-close" id="alexClose"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>' +
      '</div>' +
      '<div class="alex-chat-messages" id="alexMessages">' +
        '<div class="alex-msg bot">Hi! I\'m Alex, your Digital BDR at Open Humana. How can I help you scale your outbound today?</div>' +
      '</div>' +
      '<div class="alex-chat-input-area">' +
        '<input class="alex-chat-input" id="alexInput" type="text" placeholder="Type your message..." autocomplete="off">' +
        '<button class="alex-chat-send" id="alexSend"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button>' +
      '</div>' +
    '</div>';

  var chatContainer = document.createElement('div');
  chatContainer.innerHTML = chatHTML;
  document.body.appendChild(chatContainer);

  var bubble = document.getElementById('alexBubble');
  var chatWindow = document.getElementById('alexWindow');
  var closeBtn = document.getElementById('alexClose');
  var messagesEl = document.getElementById('alexMessages');
  var inputEl = document.getElementById('alexInput');
  var sendBtn = document.getElementById('alexSend');

  function toggleChat() {
    chatWindow.classList.toggle('open');
    if (chatWindow.classList.contains('open')) inputEl.focus();
  }

  if (bubble) bubble.addEventListener('click', toggleChat);
  if (closeBtn) closeBtn.addEventListener('click', toggleChat);

  function addMessage(text, type) {
    var msg = document.createElement('div');
    msg.className = 'alex-msg ' + type;
    msg.textContent = text;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msg;
  }

  function addTyping() {
    var msg = document.createElement('div');
    msg.className = 'alex-msg bot';
    msg.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return msg;
  }

  async function sendMessage() {
    var text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = '';
    sendBtn.disabled = true;
    addMessage(text, 'user');
    var typingEl = addTyping();

    try {
      var resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      var data = await resp.json();
      typingEl.remove();
      addMessage(data.reply || data.error || 'Sorry, something went wrong.', 'bot');
    } catch (err) {
      typingEl.remove();
      addMessage('Connection error. Please try again.', 'bot');
    }
    sendBtn.disabled = false;
    inputEl.focus();
  }

  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (inputEl) inputEl.addEventListener('keydown', function (e) { if (e.key === 'Enter') sendMessage(); });

  /* ==========================================================
     REDDIT TESTIMONIALS SHUFFLE (12 posts, 3 visible, 5s cycle)
     ========================================================== */
  var testimonials = [
    { user: 'u/BrandonMercer', flair: 'Keystone Property Solutions', votes: 847, img: '/static/images/testimonial-1.png',
      title: 'Replaced my entire cold calling operation — closed 3 extra deals last month',
      text: 'I used to spend 10 hours a day cold calling homeowners. Now I load my list into Open Humana, hit launch, and it dials through 500 numbers while I\'m out on appointments.', comments: 24 },
    { user: 'u/SarahKimRE', flair: 'Pinnacle Realty Group', votes: 632, img: '/static/images/testimonial-2.png',
      title: 'My team\'s connect rate went from 2% to 11% in the first week',
      text: 'The personalized voicemails are a game-changer. Prospects actually call us back because the message mentions their name and property address. It feels genuinely human.', comments: 18 },
    { user: 'u/MikeDelRosario', flair: 'Apex Solar Solutions', votes: 1203, img: '/static/images/testimonial-3.png',
      title: 'We booked 47 appointments in one day. One. Day.',
      text: 'Our old dialer did maybe 200 calls/day. Alex did 2,800 before lunch. The live transfer feature means my closers only talk to real humans. ROI paid for itself in 48 hours.', comments: 56 },
    { user: 'u/JessicaTPatel', flair: 'Horizon Insurance Agency', votes: 489, img: '/static/images/testimonial-4.png',
      title: 'Finally a tool that doesn\'t require a PhD to operate',
      text: 'I uploaded my CSV, picked my settings, and hit launch. Within 10 minutes I had my first live transfer. The UI is clean, fast, and actually enjoyable to use.', comments: 12 },
    { user: 'u/DanielOBrienSales', flair: 'Northeast Home Buyers', votes: 721, img: '/static/images/testimonial-5.png',
      title: 'Fired my VA team of 5. Alex does more than all of them combined.',
      text: 'I was paying $3,500/mo for virtual assistants to cold call. Now I pay $99/mo and get 10x the output. The transcription feature alone saves me hours of note-taking.', comments: 31 },
    { user: 'u/AshleyNguyen_CRE', flair: 'Pacific Commercial RE', votes: 558, img: '/static/images/testimonial-6.png',
      title: 'The voicemail drop quality is insane — prospects think I personally called them',
      text: 'I\'ve tried every voicemail tool on the market. None of them sound this natural. Alex clones my voice and adds the prospect\'s name seamlessly. Callback rate is through the roof.', comments: 22 },
    { user: 'u/RyanCooperMtg', flair: 'Summit Mortgage Co', votes: 934, img: '/static/images/testimonial-1.png',
      title: 'Went from 3 loans/month to 11 loans/month — same team size',
      text: 'The bottleneck was always outbound prospecting. Now Alex handles the dialing, leaves personalized VMs, and transfers live pickups. My loan officers just close.', comments: 43 },
    { user: 'u/KarenLeeInsurance', flair: 'Shield Life Insurance', votes: 412, img: '/static/images/testimonial-2.png',
      title: 'Best $99 I\'ve ever spent in my business. Not even close.',
      text: 'I was skeptical about AI calling. But the live transfer feature won me over — when someone picks up, my phone rings instantly. It\'s like having a 24/7 assistant.', comments: 15 },
    { user: 'u/TonyRussoREI', flair: 'Ironclad Investments', votes: 1087, img: '/static/images/testimonial-3.png',
      title: 'We closed a $2.3M deal from a cold call Alex made at 6am',
      text: 'Nobody on my team would be calling at 6am on a Tuesday. But Alex was. The owner picked up, Alex transferred the call, and we locked the contract by noon. Unreal.', comments: 67 },
    { user: 'u/PriyaSharmaFin', flair: 'Global Wealth Advisory', votes: 376, img: '/static/images/testimonial-4.png',
      title: 'The analytics dashboard alone is worth the subscription',
      text: 'Real-time call tracking, transcription, sentiment analysis — I can see exactly which scripts work and which don\'t. Data-driven outbound is the future.', comments: 9 },
    { user: 'u/ChrisHendersonDev', flair: 'BuildRight Construction', votes: 645, img: '/static/images/testimonial-5.png',
      title: 'My competitors have no idea how we\'re getting so many leads',
      text: 'While they\'re manually dialing 80 numbers a day, we\'re hitting 3,000. The unfair advantage is real. I almost feel bad for them. Almost.', comments: 28 },
    { user: 'u/LauraFitzSaaS', flair: 'ScaleUp Marketing', votes: 793, img: '/static/images/testimonial-6.png',
      title: 'We white-label Open Humana for our clients — they love it',
      text: 'We run outbound campaigns for 20+ clients. Open Humana lets us manage everything from one dashboard. The ROI reports we generate make our clients ecstatic.', comments: 37 }
  ];

  var redditFeed = document.getElementById('redditFeed');

  function buildRedditPost(t) {
    return '' +
      '<div class="reddit-post">' +
        '<div class="reddit-votes">' +
          '<button class="vote-btn upvote active"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4l-8 8h5v8h6v-8h5z"/></svg></button>' +
          '<span class="vote-count">' + t.votes + '</span>' +
          '<button class="vote-btn downvote"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 20l8-8h-5V4H9v8H4z"/></svg></button>' +
        '</div>' +
        '<div class="reddit-body">' +
          '<div class="reddit-meta">' +
            '<img src="' + t.img + '" alt="' + t.user + '" class="reddit-avatar">' +
            '<span class="reddit-user">' + t.user + '</span>' +
            '<span class="reddit-flair">' + t.flair + '</span>' +
          '</div>' +
          '<h3 class="reddit-title">' + t.title + '</h3>' +
          '<p class="reddit-text">' + t.text + '</p>' +
          '<div class="reddit-actions">' +
            '<span class="reddit-action">' + t.comments + ' Comments</span>' +
            '<span class="reddit-action">Share</span>' +
            '<span class="reddit-action reddit-sub-tag">r/OpenHumana</span>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  function shuffleArray(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    return arr;
  }

  var currentIndex = 0;

  function showTestimonials() {
    if (!redditFeed) return;
    // Fade out
    redditFeed.style.opacity = '0';

    setTimeout(function () {
      var visible = [];
      for (var k = 0; k < 3; k++) {
        visible.push(testimonials[(currentIndex + k) % testimonials.length]);
      }
      redditFeed.innerHTML = visible.map(buildRedditPost).join('');
      // Re-attach vote handlers
      attachVoteHandlers();
      // Fade in
      redditFeed.style.opacity = '1';
      currentIndex = (currentIndex + 3) % testimonials.length;
    }, 400);
  }

  if (redditFeed) {
    redditFeed.style.transition = 'opacity .4s ease';
    shuffleArray(testimonials);
    showTestimonials();
    setInterval(showTestimonials, 5000);
  }

  /* ========== REDDIT VOTE BUTTONS ========== */
  function attachVoteHandlers() {
    document.querySelectorAll('.reddit-feed .vote-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var parent = btn.closest('.reddit-votes');
        var countEl = parent.querySelector('.vote-count');
        var count = parseInt(countEl.textContent, 10);

        if (btn.classList.contains('upvote')) {
          if (btn.classList.contains('active')) {
            btn.classList.remove('active'); countEl.textContent = count - 1;
          } else {
            btn.classList.add('active');
            parent.querySelector('.downvote').classList.remove('active');
            countEl.textContent = count + 1;
          }
        } else {
          if (btn.classList.contains('active')) {
            btn.classList.remove('active'); countEl.textContent = count + 1;
          } else {
            btn.classList.add('active');
            var upBtn = parent.querySelector('.upvote');
            if (upBtn.classList.contains('active')) {
              upBtn.classList.remove('active'); countEl.textContent = count - 2;
            } else {
              countEl.textContent = count - 1;
            }
          }
        }
      });
    });
  }

})();
