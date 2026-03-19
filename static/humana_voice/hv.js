/* Humana Voice — frontend JS */
(function () {
  'use strict';

  /* ── Utility ─────────────────────────────────────────── */
  function toast(msg, type) {
    var el = document.getElementById('hvToast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'hv-toast ' + (type || '');
    void el.offsetWidth;
    el.classList.add('show');
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.remove('show'); }, 3200);
  }

  function apiPost(url, body, opts) {
    var isForm = body instanceof FormData;
    return fetch(url, Object.assign({
      method: 'POST',
      headers: isForm ? {} : { 'Content-Type': 'application/json' },
      body: isForm ? body : JSON.stringify(body),
    }, opts || {}));
  }

  /* ── Tab switching ───────────────────────────────────── */
  var tabs = document.querySelectorAll('.hv-tab');
  var panels = document.querySelectorAll('.hv-tab-panel');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); });
      panels.forEach(function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      var target = document.getElementById('panel-' + tab.dataset.tab);
      if (target) target.classList.add('active');
    });
  });

  /* ══════════════════════════════════════════════════════
     TAB 1 — Voice Library
  ═══════════════════════════════════════════════════════ */
  var libraryGrid = document.getElementById('hvLibraryGrid');
  var libSearch = document.getElementById('hvSearchInput');
  var libSearchBtn = document.getElementById('hvSearchBtn');
  var libLoadMore = document.getElementById('hvLoadMore');
  var libPage = 1;
  var libTotal = 0;
  var libQuery = '';

  function skeletonCards(n) {
    var html = '';
    for (var i = 0; i < n; i++) {
      html += '<div class="hv-skeleton-card">' +
        '<div class="hv-skeleton" style="width:56px;height:56px;border-radius:12px;"></div>' +
        '<div class="hv-skeleton" style="height:14px;width:70%;"></div>' +
        '<div class="hv-skeleton" style="height:11px;width:90%;"></div>' +
        '<div style="display:flex;gap:8px;"><div class="hv-skeleton" style="height:28px;flex:1;border-radius:7px;"></div>' +
        '<div class="hv-skeleton" style="height:28px;flex:1;border-radius:7px;"></div></div></div>';
    }
    return html;
  }

  var _avatarPalette = [
    ['#6366f1','#eef2ff'], ['#8b5cf6','#f5f3ff'], ['#ec4899','#fdf2f8'],
    ['#0ea5e9','#f0f9ff'], ['#10b981','#f0fdf4'], ['#f59e0b','#fffbeb'],
    ['#ef4444','#fef2f2'], ['#14b8a6','#f0fdfa'], ['#f97316','#fff7ed'],
    ['#06b6d4','#ecfeff'],
  ];

  function _voiceAvatar(title, coverUrl) {
    var ch = (title || '?').replace(/\s+/g,'')[0] || '?';
    var letter = ch.toUpperCase();
    var idx = ch.charCodeAt(0) % _avatarPalette.length;
    var fg = _avatarPalette[idx][0];
    var imgTag = coverUrl
      ? '<img src="' + escHtml(coverUrl) + '" alt="" class="hv-avatar-img" onerror="this.style.display=\'none\'">'
      : '';
    return '<div class="hv-card-avatar">' +
      '<div class="hv-avatar-inner" style="background:' + fg + ';">' +
        '<span class="hv-avatar-letter">' + escHtml(letter) + '</span>' +
        imgTag +
      '</div>' +
    '</div>';
  }

  function renderVoiceCard(v) {
    var div = document.createElement('div');
    div.className = 'hv-voice-card';
    div.dataset.voiceId = v.id;
    div.dataset.voiceName = v.title;

    var langs = (v.languages || []).slice(0, 3).map(function (l) {
      return '<span class="hv-lang-tag">' + escHtml(l) + '</span>';
    }).join('');

    div.innerHTML = _voiceAvatar(v.title, v.cover_image) +
      '<div class="hv-card-info">' +
        '<div class="hv-card-title" title="' + escHtml(v.title) + '">' + escHtml(v.title) + '</div>' +
        (v.description ? '<div class="hv-card-desc">' + escHtml(v.description) + '</div>' : '') +
      '</div>' +
      (langs ? '<div class="hv-lang-tags">' + langs + '</div>' : '') +
      '<div class="hv-card-actions">' +
        (v.sample_url ? '<button class="hv-btn hv-btn-sm hv-lib-preview"><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Preview</button>' : '') +
        '<button class="hv-btn hv-btn-sm hv-btn-primary hv-lib-add">+ Add</button>' +
      '</div>';

    var prevBtn = div.querySelector('.hv-lib-preview');
    if (prevBtn && v.sample_url) {
      var sampleUrl = v.sample_url;
      prevBtn.addEventListener('click', function () { hvPreviewExternal(sampleUrl, prevBtn); });
    }
    var addBtn = div.querySelector('.hv-lib-add');
    if (addBtn) {
      var voiceId = v.id, voiceName = v.title;
      addBtn.addEventListener('click', function () { hvAddVoice(voiceId, voiceName, addBtn); });
    }
    return div;
  }

  function loadLibrary(reset) {
    if (reset) {
      libPage = 1;
      libraryGrid.innerHTML = skeletonCards(8);
      if (libLoadMore) libLoadMore.style.display = 'none';
    } else {
      libraryGrid.insertAdjacentHTML('beforeend', skeletonCards(4));
    }

    fetch('/humana-voice/api/library?query=' + encodeURIComponent(libQuery) + '&page=' + libPage)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { toast(data.error, 'error'); return; }
        var items = data.items || [];
        libTotal = data.total || items.length;

        var skels = libraryGrid.querySelectorAll('.hv-skeleton-card');
        skels.forEach(function (s) { s.remove(); });

        if (reset && items.length === 0) {
          libraryGrid.innerHTML = '<div class="hv-empty"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg><div>No voices found. Try a different search.</div></div>';
          return;
        }

        items.forEach(function (v) {
          libraryGrid.appendChild(renderVoiceCard(v));
        });

        var loaded = libraryGrid.querySelectorAll('.hv-voice-card').length;
        if (libLoadMore) {
          libLoadMore.style.display = loaded < libTotal ? 'block' : 'none';
        }
      })
      .catch(function (err) {
        toast('Failed to load voices', 'error');
        libraryGrid.querySelectorAll('.hv-skeleton-card').forEach(function (s) { s.remove(); });
      });
  }

  if (libSearchBtn) {
    libSearchBtn.addEventListener('click', function () {
      libQuery = libSearch ? libSearch.value.trim() : '';
      loadLibrary(true);
    });
  }
  if (libSearch) {
    libSearch.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { libQuery = libSearch.value.trim(); loadLibrary(true); }
    });
  }
  if (libLoadMore) {
    libLoadMore.addEventListener('click', function () {
      libPage++;
      loadLibrary(false);
    });
  }

  window.hvPreviewExternal = function (url, btn) {
    var audio = btn._audio;
    if (audio && !audio.paused) { audio.pause(); btn.textContent = '▶ Preview'; return; }
    if (!audio) {
      audio = new Audio(url);
      btn._audio = audio;
      audio.addEventListener('ended', function () { btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Preview'; });
    }
    btn.textContent = '■ Stop';
    audio.play().catch(function () { btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Preview'; });
  };

  window.hvAddVoice = function (voiceId, voiceName, btn) {
    btn.disabled = true;
    btn.textContent = '...';
    apiPost('/humana-voice/api/select', { voice_id: voiceId, voice_name: voiceName })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { toast(data.error, 'error'); }
        else { toast(voiceName + ' added to My Voices', 'success'); btn.textContent = '✓ Added'; loadMyVoices(); }
      })
      .catch(function () { toast('Failed to add voice', 'error'); })
      .finally(function () { btn.disabled = false; });
  };

  /* ══════════════════════════════════════════════════════
     TAB 2 — Clone Your Voice
  ═══════════════════════════════════════════════════════ */

  /* --- Upload --- */
  var dropzone = document.getElementById('hvDropzone');
  var fileInput = document.getElementById('hvFileInput');
  var fileChosen = document.getElementById('hvFileChosen');
  var uploadNameInput = document.getElementById('hvUploadName');
  var uploadBtn = document.getElementById('hvUploadBtn');
  var uploadProgress = document.getElementById('hvUploadProgress');
  var uploadProgressBar = document.getElementById('hvUploadProgressBar');
  var selectedFile = null;

  if (dropzone) {
    dropzone.addEventListener('click', function () { fileInput && fileInput.click(); });
    dropzone.addEventListener('dragover', function (e) { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', function () { dropzone.classList.remove('dragover'); });
    dropzone.addEventListener('drop', function (e) {
      e.preventDefault(); dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length) { setUploadFile(e.dataTransfer.files[0]); }
    });
  }
  if (fileInput) {
    fileInput.addEventListener('change', function () {
      if (fileInput.files.length) setUploadFile(fileInput.files[0]);
    });
  }

  function setUploadFile(f) {
    selectedFile = f;
    if (fileChosen) fileChosen.textContent = f.name + ' (' + (f.size / 1024 / 1024).toFixed(1) + ' MB)';
  }

  if (uploadBtn) {
    uploadBtn.addEventListener('click', function () {
      if (!selectedFile) { toast('Please select an audio file first', 'error'); return; }
      var name = uploadNameInput ? uploadNameInput.value.trim() : '';
      if (!name) { toast('Please enter a voice name', 'error'); return; }
      var fd = new FormData();
      fd.append('audio', selectedFile, selectedFile.name);
      fd.append('voice_name', name);
      uploadBtn.disabled = true;
      if (uploadProgress) uploadProgress.style.display = 'block';
      var bar = uploadProgressBar;
      var pct = 0;
      var sim = setInterval(function () {
        pct = Math.min(pct + 8, 85);
        if (bar) bar.style.width = pct + '%';
      }, 250);
      apiPost('/humana-voice/api/clone/upload', fd)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          clearInterval(sim); if (bar) bar.style.width = '100%';
          if (data.error) { toast(data.error, 'error'); }
          else { toast('"' + name + '" voice created!', 'success'); loadMyVoices(); switchTab('my-voices'); }
        })
        .catch(function () { clearInterval(sim); toast('Upload failed', 'error'); })
        .finally(function () {
          uploadBtn.disabled = false;
          setTimeout(function () { if (uploadProgress) uploadProgress.style.display = 'none'; if (bar) bar.style.width = '0'; }, 1500);
        });
    });
  }

  /* --- Recorder --- */
  var recordBtn = document.getElementById('hvRecordBtn');
  var timerEl = document.getElementById('hvTimer');
  var waveformEl = document.getElementById('hvWaveform');
  var recordPlayback = document.getElementById('hvRecordPlayback');
  var recordNameInput = document.getElementById('hvRecordName');
  var createRecordBtn = document.getElementById('hvCreateRecordBtn');
  var mediaRecorder = null;
  var audioChunks = [];
  var recordingBlob = null;
  var timerInterval = null;
  var recordSeconds = 0;
  var analyser = null;
  var animFrame = null;
  var waveBars = [];

  if (waveformEl) {
    for (var i = 0; i < 20; i++) {
      var bar = document.createElement('div');
      bar.className = 'hv-wave-bar';
      bar.style.height = '4px';
      waveformEl.appendChild(bar);
      waveBars.push(bar);
    }
  }

  function formatTime(s) {
    var m = Math.floor(s / 60);
    return (m < 10 ? '0' + m : m) + ':' + (s % 60 < 10 ? '0' + (s % 60) : s % 60);
  }

  function drawWave() {
    if (!analyser) return;
    var data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    var step = Math.floor(data.length / waveBars.length);
    waveBars.forEach(function (bar, i) {
      var val = data[i * step] || 0;
      var h = Math.max(4, Math.round(val / 255 * 36));
      bar.style.height = h + 'px';
      bar.classList.toggle('active', val > 30);
    });
    animFrame = requestAnimationFrame(drawWave);
  }

  if (recordBtn) {
    recordBtn.addEventListener('click', function () {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        recordBtn.classList.remove('recording');
        recordBtn.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24" fill="#fff"><circle cx="12" cy="12" r="8"/></svg>';
        clearInterval(timerInterval);
        cancelAnimationFrame(animFrame);
        waveBars.forEach(function (b) { b.style.height = '4px'; b.classList.remove('active'); });
      } else {
        audioChunks = [];
        recordingBlob = null;
        navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
          var ctx = new (window.AudioContext || window.webkitAudioContext)();
          var src = ctx.createMediaStreamSource(stream);
          analyser = ctx.createAnalyser();
          analyser.fftSize = 256;
          src.connect(analyser);
          mediaRecorder = new MediaRecorder(stream);
          var recMimeType = mediaRecorder.mimeType || 'audio/webm';
          mediaRecorder.ondataavailable = function (e) { if (e.data.size > 0) audioChunks.push(e.data); };
          mediaRecorder.onstop = function () {
            recordingBlob = new Blob(audioChunks, { type: recMimeType });
            recordingBlob._mimeType = recMimeType;
            var url = URL.createObjectURL(recordingBlob);
            if (recordPlayback) { recordPlayback.src = url; recordPlayback.style.display = 'block'; }
            if (createRecordBtn) createRecordBtn.style.display = 'block';
            stream.getTracks().forEach(function (t) { t.stop(); });
          };
          mediaRecorder.start();
          recordBtn.classList.add('recording');
          recordBtn.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
          recordSeconds = 0;
          if (timerEl) timerEl.textContent = '00:00';
          timerInterval = setInterval(function () {
            recordSeconds++;
            if (timerEl) timerEl.textContent = formatTime(recordSeconds);
          }, 1000);
          drawWave();
        }).catch(function () { toast('Microphone access denied', 'error'); });
      }
    });
  }

  if (createRecordBtn) {
    createRecordBtn.addEventListener('click', function () {
      if (!recordingBlob) { toast('No recording found', 'error'); return; }
      var name = recordNameInput ? recordNameInput.value.trim() : '';
      if (!name) { toast('Please enter a voice name', 'error'); return; }
      var fd = new FormData();
      var recExt = (recordingBlob._mimeType || '').includes('mp4') ? 'm4a'
                 : (recordingBlob._mimeType || '').includes('ogg') ? 'ogg'
                 : 'webm';
      fd.append('audio', recordingBlob, 'recording.' + recExt);
      fd.append('voice_name', name);
      createRecordBtn.disabled = true;
      createRecordBtn.textContent = 'Creating...';
      apiPost('/humana-voice/api/clone/record', fd)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) { toast(data.error, 'error'); }
          else { toast('"' + name + '" voice created!', 'success'); loadMyVoices(); switchTab('my-voices'); }
        })
        .catch(function () { toast('Failed to create voice', 'error'); })
        .finally(function () { createRecordBtn.disabled = false; createRecordBtn.textContent = 'Create Voice'; });
    });
  }

  /* ══════════════════════════════════════════════════════
     TAB 3 — My Voices
  ═══════════════════════════════════════════════════════ */
  var myVoicesList = document.getElementById('hvMyVoicesList');
  var activeNameEl = document.getElementById('hvActiveName');
  var activeDot = document.getElementById('hvActiveDot');

  function loadMyVoices() {
    if (!myVoicesList) return;
    myVoicesList.innerHTML = '<div style="padding:20px;color:var(--gads-text-tertiary);font-size:13px;">Loading...</div>';
    fetch('/humana-voice/api/my-voices')
      .then(function (r) { return r.json(); })
      .then(function (voices) {
        renderMyVoices(voices);
        var active = voices.find(function (v) { return v.is_active; });
        if (activeNameEl) activeNameEl.textContent = active ? active.voice_name : '';
        if (activeDot) {
          activeDot.style.display = active ? 'flex' : 'none';
          var noBadge = document.getElementById('hvNoActive');
          if (noBadge) noBadge.style.display = active ? 'none' : 'inline';
        }
      })
      .catch(function () { toast('Failed to load voices', 'error'); });
  }

  function renderMyVoices(voices) {
    if (!myVoicesList) return;
    if (!voices.length) {
      myVoicesList.innerHTML = '<div class="hv-empty"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg><div>No voices yet. Browse the library or clone your voice.</div></div>';
      return;
    }
    var html = '';
    voices.forEach(function (v) {
      var typeClass = v.voice_type === 'cloned' ? 'hv-badge-cloned' : 'hv-badge-library';
      var typeLabel = v.voice_type === 'cloned' ? 'Cloned' : 'Library';
      html += '<div class="hv-voice-row" data-row-id="' + v.voice_id + '">' +
        '<div class="hv-voice-row-main">' +
          '<div class="hv-voice-row-info">' +
            '<div class="hv-voice-row-name">' + escHtml(v.voice_name) + '</div>' +
            '<div class="hv-voice-row-meta">' +
              '<span class="hv-badge ' + typeClass + '">' + typeLabel + '</span>' +
              (v.is_active ? '<span class="hv-badge hv-badge-active">Active</span>' : '') +
            '</div>' +
          '</div>' +
          '<div class="hv-voice-row-actions">' +
            (!v.is_active ? '<button class="hv-btn hv-btn-sm hv-btn-success" onclick="hvSetActive(\'' + v.voice_id + '\',this)">Set Active</button>' : '') +
            '<button class="hv-btn hv-btn-sm" onclick="hvPreviewVoice(\'' + v.voice_id + '\',this)"><svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Preview</button>' +
            '<button class="hv-btn hv-btn-sm" onclick="hvToggleExpand(this)">Style ▾</button>' +
            '<button class="hv-btn hv-btn-sm hv-btn-danger" onclick="hvDeleteVoice(\'' + v.voice_id + '\',\'' + escHtml(v.voice_name).replace(/'/g, '\\&#39;') + '\',this)">✕</button>' +
          '</div>' +
        '</div>' +
        '<div class="hv-voice-expand">' +
          '<div class="hv-style-row">' +
            '<div class="hv-slider-wrap">' +
              '<div class="hv-slider-label"><span>Speed</span><span id="speedVal-' + v.voice_id + '">' + (v.style_speed || 1.0).toFixed(1) + 'x</span></div>' +
              '<input class="hv-slider" type="range" min="0.5" max="2.0" step="0.1" value="' + (v.style_speed || 1.0) + '" oninput="document.getElementById(\'speedVal-' + v.voice_id + '\').textContent=parseFloat(this.value).toFixed(1)+\'x\'" onchange="hvSaveStyle(\'' + v.voice_id + '\',this.value,null)">' +
            '</div>' +
            '<div>' +
              '<div class="hv-label">Emotion</div>' +
              '<select class="hv-select" onchange="hvSaveStyle(\'' + v.voice_id + '\',null,this.value)">' +
                ['neutral','excited','calm','serious','friendly'].map(function(e){return '<option value="'+e+'"'+(v.style_emotion===e?' selected':'')+'>'+e.charAt(0).toUpperCase()+e.slice(1)+'</option>';}).join('') +
              '</select>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '</div>';
    });
    myVoicesList.innerHTML = html;
  }

  window.hvSetActive = function (voiceId, btn) {
    btn.disabled = true;
    apiPost('/humana-voice/api/set-active', { voice_id: voiceId })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { toast(data.error, 'error'); }
        else { toast('Active voice updated', 'success'); loadMyVoices(); }
      })
      .catch(function () { toast('Failed to set active voice', 'error'); })
      .finally(function () { btn.disabled = false; });
  };

  window.hvPreviewVoice = function (voiceId, btn) {
    btn.disabled = true;
    var prevText = btn.innerHTML;
    btn.textContent = '...';
    apiPost('/humana-voice/api/preview', { voice_id: voiceId, text: 'Hello! This is a preview of your selected Humana Voice.' })
      .then(function (r) {
        if (!r.ok) throw new Error('Preview failed');
        return r.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var audio = new Audio(url);
        audio.play();
        audio.addEventListener('ended', function () { URL.revokeObjectURL(url); });
      })
      .catch(function () { toast('Preview unavailable', 'error'); })
      .finally(function () { btn.disabled = false; btn.innerHTML = prevText; });
  };

  window.hvToggleExpand = function (btn) {
    var row = btn.closest('.hv-voice-row');
    var exp = row && row.querySelector('.hv-voice-expand');
    if (!exp) return;
    exp.classList.toggle('open');
    btn.textContent = exp.classList.contains('open') ? 'Style ▴' : 'Style ▾';
  };

  var styleTimers = {};
  window.hvSaveStyle = function (voiceId, speed, emotion) {
    clearTimeout(styleTimers[voiceId]);
    styleTimers[voiceId] = setTimeout(function () {
      var row = document.querySelector('[data-row-id="' + voiceId + '"]');
      var s = speed !== null ? parseFloat(speed) : parseFloat(row && row.querySelector('input[type=range]') ? row.querySelector('input[type=range]').value : 1.0);
      var e = emotion !== null ? emotion : (row && row.querySelector('select') ? row.querySelector('select').value : 'neutral');
      apiPost('/humana-voice/api/style', { voice_id: voiceId, speed: s, emotion: e })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (!d.error) toast('Style saved', 'success'); })
        .catch(function () {});
    }, 600);
  };

  window.hvDeleteVoice = function (voiceId, voiceName, btn) {
    if (!confirm('Delete "' + voiceName + '"? This cannot be undone.')) return;
    btn.disabled = true;
    fetch('/humana-voice/api/voice/' + voiceId, { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { toast(data.error, 'error'); }
        else { toast('"' + voiceName + '" deleted', ''); loadMyVoices(); }
      })
      .catch(function () { toast('Delete failed', 'error'); })
      .finally(function () { btn.disabled = false; });
  };

  /* ── Helpers ─────────────────────────────────────────── */
  function escHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function switchTab(name) {
    tabs.forEach(function (t) {
      var active = t.dataset.tab === name;
      t.classList.toggle('active', active);
      var panel = document.getElementById('panel-' + t.dataset.tab);
      if (panel) panel.classList.toggle('active', active);
    });
  }

  /* ── Init ────────────────────────────────────────────── */
  var _hvInited = false;
  window.hvInit = function () {
    if (_hvInited) { loadMyVoices(); return; }
    _hvInited = true;
    fetch('/api/fish-audio-key').then(function(r){ return r.json(); }).then(function(d){
      var w = document.getElementById('hvApiWarn');
      if (w) w.style.display = d.configured ? 'none' : '';
    }).catch(function(){});
    loadLibrary(true);
    loadMyVoices();
  };

})();
