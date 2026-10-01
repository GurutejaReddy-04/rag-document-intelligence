/**
 * RAG Document Intelligence (v1) frontend logic.
 * Communicates with the FastAPI backend at API_BASE.
 */
const API_BASE = 'http://localhost:8000';

/* DOM references */
const fileInput           = document.getElementById('fileInput');
const collNameInput       = document.getElementById('collNameInput');
const forceCheckbox       = document.getElementById('forceCheckbox');
const uploadBtn           = document.getElementById('uploadBtn');
const uploadFeedback      = document.getElementById('uploadFeedback');

const collectionSelect    = document.getElementById('collectionSelect');
const deleteBtn           = document.getElementById('deleteBtn');
const resetBtn            = document.getElementById('resetBtn');
const resetConfirm        = document.getElementById('resetConfirm');
const confirmResetBtn     = document.getElementById('confirmResetBtn');
const cancelResetBtn      = document.getElementById('cancelResetBtn');
const manageFeedback      = document.getElementById('manageFeedback');

const queryCollectionSelect = document.getElementById('queryCollectionSelect');
const questionInput        = document.getElementById('questionInput');
const askBtn               = document.getElementById('askBtn');
const queryFeedback        = document.getElementById('queryFeedback');
const resultsContainer     = document.getElementById('resultsContainer');
const answerDisplay        = document.getElementById('answerDisplay');
const sourcesDisplay       = document.getElementById('sourcesDisplay');

/* Utility: show feedback message with class */
function showFeedback(element, message, type = '') {
  element.innerHTML = message ? `<div class="${type}">${message}</div>` : '';
}

/* Fetch and populate both collection dropdowns */
async function loadCollections() {
  try {
    const response = await fetch(`${API_BASE}/collections`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const names = data.collections || [];
    [collectionSelect, queryCollectionSelect].forEach(select => {
      select.innerHTML = '<option value="">-- select --</option>';
      names.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
      });
    });
  } catch (error) {
    showFeedback(manageFeedback, `Failed to load collections: ${error.message}`, 'error');
  }
}

/* Upload handler */
uploadBtn.addEventListener('click', async () => {
  const file = fileInput.files[0];
  const collection = collNameInput.value.trim();
  if (!file) return showFeedback(uploadFeedback, 'Choose a PDF file.', 'warning');
  if (!collection) return showFeedback(uploadFeedback, 'Enter a collection name.', 'warning');

  const form = new FormData();
  form.append('file', file);
  form.append('collection_name', collection);
  form.append('force', forceCheckbox.checked);

  uploadBtn.disabled = true;
  showFeedback(uploadFeedback, 'Uploading and indexing...', '');
  try {
    const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showFeedback(uploadFeedback, data.message, 'success');
    fileInput.value = '';
    collNameInput.value = '';
    forceCheckbox.checked = false;
    loadCollections();  // refresh lists
  } catch (err) {
    showFeedback(uploadFeedback, `Upload failed: ${err.message}`, 'error');
  } finally {
    uploadBtn.disabled = false;
  }
});

/* Delete single collection */
deleteBtn.addEventListener('click', async () => {
  const name = collectionSelect.value;
  if (!name) return showFeedback(manageFeedback, 'Select a collection.', 'warning');
  try {
    const res = await fetch(`${API_BASE}/collections/${encodeURIComponent(name)}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showFeedback(manageFeedback, data.message, 'success');
    loadCollections();
  } catch (err) {
    showFeedback(manageFeedback, `Delete failed: ${err.message}`, 'error');
  }
});

/* Reset all collections (with confirmation) */
resetBtn.addEventListener('click', () => { resetConfirm.style.display = 'block'; });
cancelResetBtn.addEventListener('click', () => { resetConfirm.style.display = 'none'; });
confirmResetBtn.addEventListener('click', async () => {
  try {
    const res = await fetch(`${API_BASE}/reset?wipe_uploads=false`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showFeedback(manageFeedback, data.message, 'success');
    resetConfirm.style.display = 'none';
    loadCollections();
  } catch (err) {
    showFeedback(manageFeedback, `Reset failed: ${err.message}`, 'error');
  }
});

/* Query handler */
askBtn.addEventListener('click', async () => {
  const question = questionInput.value.trim();
  const collection = queryCollectionSelect.value;
  if (!question) return showFeedback(queryFeedback, 'Enter a question.', 'warning');
  if (!collection) return showFeedback(queryFeedback, 'Select a collection.', 'warning');

  askBtn.disabled = true;
  showFeedback(queryFeedback, 'Searching...', '');
  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, collection_name: collection }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showFeedback(queryFeedback, '', '');
    resultsContainer.style.display = 'block';
    answerDisplay.textContent = data.answer;
    // Cosine distance (0-2) -> similarity percentage
    sourcesDisplay.innerHTML = '';
    (data.sources || []).forEach(s => {
      const card = document.createElement('div');
      card.className = 'source-card';

      const nameSpan = document.createElement('span');
      nameSpan.className = 'source-name';
      nameSpan.textContent = s.source;

      const pageText = document.createTextNode(` — Page ${s.page} `);

      const relevanceSpan = document.createElement('span');
      const similarity = Math.max(0, 1 - s.score / 2) * 100;
      relevanceSpan.textContent = `relevance: ${similarity.toFixed(0)}%`;

      card.appendChild(nameSpan);
      card.appendChild(pageText);
      card.appendChild(relevanceSpan);
      sourcesDisplay.appendChild(card);
    });
  } catch (err) {
    showFeedback(queryFeedback, `Query failed: ${err.message}`, 'error');
  } finally {
    askBtn.disabled = false;
  }
});

/* Load collections on page load */
loadCollections();