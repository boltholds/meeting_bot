const $ = (selector) => document.querySelector(selector);
const apiKey = $('#apiKey');
const meetingUrl = $('#meetingUrl');
const providerBadge = $('#providerBadge');
const form = $('#meetingForm');
const list = $('#sessionList');
const activeStatuses = new Set(['queued', 'joining', 'waiting_room', 'recording']);
const providerNames = {google_meet: 'Google Meet', zoom: 'Zoom', yandex_telemost: 'Телемост'};
const providerMarks = {google_meet: 'GM', zoom: 'ZM', yandex_telemost: 'ЯТ'};

apiKey.value = sessionStorage.getItem('meetingBotApiKey') || '';

function detectProvider(value) {
  const patterns = [
    [/^https:\/\/meet\.google\.com\/[a-z]{3}-[a-z]{4}-[a-z]{3}(?:[/?#].*)?$/i, 'GOOGLE MEET'],
    [/^https:\/\/(?:[\w-]+\.)?zoom\.us\/j\/\d+(?:[/?#].*)?$/i, 'ZOOM'],
    [/^https:\/\/telemost\.yandex\.(?:ru|com)\/j\/\d+(?:[/?#].*)?$/i, 'ТЕЛЕМОСТ'],
  ];
  return patterns.find(([pattern]) => pattern.test(value.trim()))?.[1] || 'AUTO';
}

meetingUrl.addEventListener('input', () => {
  providerBadge.textContent = detectProvider(meetingUrl.value);
});
apiKey.addEventListener('change', () => {
  sessionStorage.setItem('meetingBotApiKey', apiKey.value);
  loadMeetings();
});

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {'Content-Type': 'application/json', 'X-API-Key': apiKey.value, ...(options.headers || {})},
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const submit = form.querySelector('button[type="submit"]');
  $('#formError').textContent = '';
  submit.disabled = true;
  sessionStorage.setItem('meetingBotApiKey', apiKey.value);
  try {
    await request('/v1/meetings', {method: 'POST', body: JSON.stringify({
      url: meetingUrl.value.trim(),
      title: $('#title').value.trim() || null,
      language: $('#language').value,
      min_speakers: Number($('#minSpeakers').value),
      max_speakers: Number($('#maxSpeakers').value),
      analyze: true,
    })});
    meetingUrl.value = '';
    providerBadge.textContent = 'AUTO';
    await loadMeetings();
  } catch (error) { $('#formError').textContent = error.message; }
  finally { submit.disabled = false; }
});

function renderMeeting(meeting) {
  const card = $('#sessionTemplate').content.firstElementChild.cloneNode(true);
  card.dataset.id = meeting.id;
  card.querySelector('.provider-icon').textContent = providerMarks[meeting.provider] || 'MB';
  card.querySelector('h3').textContent = meeting.title || providerNames[meeting.provider] || 'Встреча';
  const status = card.querySelector('.status');
  status.textContent = meeting.status.replace('_', ' ');
  status.classList.add(meeting.status);
  const link = card.querySelector('.meeting-link');
  link.href = meeting.url; link.textContent = meeting.url;
  const created = new Date(meeting.created_at).toLocaleString('ru-RU');
  card.querySelector('.meta').textContent = `${providerNames[meeting.provider]} · ${created} · ${meeting.language.toUpperCase()}`;
  const error = card.querySelector('.error');
  error.textContent = meeting.error || (meeting.transcription_job_id ? `Transcription: ${meeting.transcription_job_id}` : '');
  const stop = card.querySelector('.stop-button');
  stop.hidden = !activeStatuses.has(meeting.status);
  stop.addEventListener('click', async () => {
    stop.disabled = true;
    try { await request(`/v1/meetings/${meeting.id}/stop`, {method: 'POST'}); await loadMeetings(); }
    catch (err) { error.textContent = err.message; stop.disabled = false; }
  });
  return card;
}

async function loadMeetings() {
  if (!apiKey.value) return;
  try {
    const meetings = await request('/v1/meetings');
    list.replaceChildren(...(meetings.length ? meetings.map(renderMeeting) : [Object.assign(document.createElement('div'), {className: 'empty', textContent: 'Сессий пока нет.'})]));
  } catch (error) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = error.message;
    list.replaceChildren(empty);
  }
}

$('#refresh').addEventListener('click', loadMeetings);
loadMeetings();
setInterval(loadMeetings, 3000);
