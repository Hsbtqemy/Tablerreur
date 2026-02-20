/* Tablerreur Web App — Frontend JavaScript (French UI) */
'use strict';

// ---------------------------------------------------------------------------
// État global de l'application
// ---------------------------------------------------------------------------
const state = {
  jobId: null,
  filename: null,
  rows: 0,
  cols: 0,
  columns: [],
  currentPage: 1,
  currentStep: 'upload',
  // Configure step
  columnConfig: {},     // { colName: { content_type, unique, ... } }
  activeColumn: null,   // name of the currently open config panel
};

// ---------------------------------------------------------------------------
// Navigation entre étapes
// ---------------------------------------------------------------------------
function goToStep(step) {
  // Hide all sections
  document.querySelectorAll('.step-section').forEach(el => el.hidden = true);
  document.querySelectorAll('.step-btn').forEach(el => el.classList.remove('active'));

  // Show target section
  const section = document.getElementById('step-' + step);
  if (section) section.hidden = false;

  // Activate nav button
  const btn = document.querySelector(`[data-step="${step}"]`);
  if (btn) btn.classList.add('active');

  state.currentStep = step;

  // Step-specific init
  if (step === 'configure') loadPreview();
  if (step === 'validate') runValidation();
  if (step === 'results') loadProblems(1);
}

function enableStep(step) {
  const btn = document.querySelector(`[data-step="${step}"]`);
  if (btn) btn.disabled = false;
}

// ---------------------------------------------------------------------------
// ÉTAPE 1 — Téléversement
// ---------------------------------------------------------------------------
const fileInput = document.getElementById('file-input');
const uploadZone = document.getElementById('upload-zone');

fileInput?.addEventListener('change', () => {
  if (fileInput.files.length) showFileSelected(fileInput.files[0].name);
});

// Drag & drop
uploadZone?.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone?.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone?.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    showFileSelected(e.dataTransfer.files[0].name);
  }
});

function showFileSelected(name) {
  document.getElementById('upload-filename').textContent = '📄 ' + name;
  document.getElementById('upload-file-info').hidden = false;
  document.querySelector('.upload-inner').hidden = true;
}

function clearFile() {
  fileInput.value = '';
  document.getElementById('upload-file-info').hidden = true;
  document.querySelector('.upload-inner').hidden = false;
}

async function doUpload() {
  const errEl = document.getElementById('upload-error');
  const progEl = document.getElementById('upload-progress');
  errEl.hidden = true;

  if (!fileInput.files.length) {
    errEl.textContent = 'Veuillez sélectionner un fichier.';
    errEl.hidden = false;
    return;
  }

  progEl.hidden = false;
  progEl.textContent = 'Téléversement en cours…';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('header_row', document.getElementById('header-row').value);
  formData.append('delimiter', document.getElementById('delimiter').value);
  formData.append('encoding', document.getElementById('encoding').value);
  formData.append('template_id', document.getElementById('template-id').value);

  try {
    const resp = await fetch('/api/jobs', { method: 'POST', body: formData });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || 'Échec du téléversement');
    }
    const data = await resp.json();
    state.jobId = data.job_id;
    state.filename = data.filename;
    state.rows = data.rows;
    state.cols = data.cols;
    state.columns = data.columns || [];
    state.columnConfig = {};
    state.activeColumn = null;

    progEl.textContent = `Chargé : ${data.filename} (${data.rows} lignes × ${data.cols} colonnes)`;

    // Populate column filter in fixes step
    const fixColSelect = document.getElementById('fix-columns');
    fixColSelect.innerHTML = '<option value="">Toutes les colonnes</option>';
    state.columns.forEach(col => {
      const opt = document.createElement('option');
      opt.value = col;
      opt.textContent = col;
      fixColSelect.appendChild(opt);
    });

    // Populate column filter in results step
    const filterCol = document.getElementById('filter-column');
    filterCol.innerHTML = '<option value="">Toutes les colonnes</option>';
    state.columns.forEach(col => {
      const opt = document.createElement('option');
      opt.value = col;
      opt.textContent = col;
      filterCol.appendChild(opt);
    });

    enableStep('configure');
    goToStep('configure');
  } catch (err) {
    progEl.hidden = true;
    errEl.textContent = 'Erreur : ' + err.message;
    errEl.hidden = false;
  }
}

// ---------------------------------------------------------------------------
// ÉTAPE 2 — Configuration des colonnes
// ---------------------------------------------------------------------------

// Map of predefined format presets: key → { regex, hint }
const FORMAT_PRESETS = {
  // Formats généraux
  year:         { regex: '^\\d{4}$',                            hint: 'Accepte : 2024, 1999. Rejette : 24, deux mille.' },
  yes_no:       { regex: '(?i)^(oui|non|o|n|yes|no|vrai|faux|true|false|1|0)$', hint: 'Accepte : oui, non, o, n, vrai, faux, 1, 0 (majuscules ou minuscules).' },
  alphanum:     { regex: '^[A-Za-z0-9]+$',                      hint: 'Accepte : ABC123, test42. Rejette : test@42, hello world.' },
  letters_only: { regex: "^[A-Za-z\\u00C0-\\u00FF\\s\\-']+$",  hint: "Accepte : Jean-Pierre, José, l'Île. Rejette : test123, @nom." },
  positive_int: { regex: '^\\d+$',                              hint: 'Accepte : 0, 42, 1000. Rejette : -1, 3.14.' },
  // Identifiants & liens
  doi:          { regex: '^10\\.\\d{4,9}/[^\\s]+$',            hint: "Accepte : 10.1000/xyz123, 10.5281/zenodo.12345. Rejette : doi:10.1000 (préfixe 'doi:' non inclus), texte libre." },
  orcid:        { regex: '^\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]$', hint: 'Accepte : 0000-0002-1825-0097, 0000-0001-5109-3700. Rejette : sans tirets, trop court.' },
  ark:          { regex: '^ark:/\\d{5}/.+$',                    hint: 'Accepte : ark:/67375/ABC-123. Rejette : ark:67375 (manque le /), texte libre.' },
  issn:         { regex: '^\\d{4}-\\d{3}[\\dX]$',              hint: 'Accepte : 0317-8471, 1234-567X. Rejette : sans tiret, trop court.' },
  // Dates
  w3cdtf:       { regex: '^\\d{4}(-\\d{2}(-\\d{2})?)?$',       hint: 'Accepte : 2024, 2024-01, 2024-01-15. Rejette : 15/01/2024, 24.' },
  iso_date:     { regex: '^\\d{4}-\\d{2}-\\d{2}$',             hint: 'Accepte : 2024-01-15. Rejette : 2024, 15/01/2024, 2024-1-5.' },
  // Codes & référentiels
  lang_iso639:  { regex: '(?i)^[a-z]{2,3}$',                   hint: 'Accepte : fr, en, de, ita, oci. Rejette : français, FR-fr, french.' },
};

// Show/hide hint and custom regex field based on selected preset
function _updateFormatPresetUI(presetValue) {
  const hintEl = document.getElementById('cfg-format-hint');
  const customWrap = document.getElementById('cfg-custom-regex-wrap');

  if (presetValue === 'custom') {
    hintEl.hidden = true;
    customWrap.hidden = false;
  } else if (presetValue && FORMAT_PRESETS[presetValue]) {
    hintEl.textContent = FORMAT_PRESETS[presetValue].hint;
    hintEl.hidden = false;
    customWrap.hidden = true;
  } else {
    hintEl.hidden = true;
    customWrap.hidden = true;
  }
}

// Wire up the preset dropdown change event (runs once at page load)
document.getElementById('cfg-format-preset')?.addEventListener('change', function () {
  _updateFormatPresetUI(this.value);
});

// Enable/disable list option fields based on separator input
document.getElementById('cfg-list-separator')?.addEventListener('input', function () {
  _updateListOptionsState(this.value.trim());
});

function _updateListOptionsState(sepValue) {
  const optionsEl = document.getElementById('cfg-list-options');
  if (!optionsEl) return;
  const disabled = !sepValue;
  optionsEl.querySelectorAll('input').forEach(el => {
    el.disabled = disabled;
  });
  optionsEl.classList.toggle('list-options-disabled', disabled);
}

async function loadPreview() {
  if (!state.jobId) return;

  const loadingEl = document.getElementById('preview-loading');
  const tableEl = document.getElementById('preview-table');
  const headerRow = document.getElementById('preview-header');
  const body = document.getElementById('preview-body');

  loadingEl.hidden = false;
  tableEl.hidden = true;
  headerRow.innerHTML = '';
  body.innerHTML = '';

  try {
    const [previewResp, configResp] = await Promise.all([
      fetch(`/api/jobs/${state.jobId}/preview?rows=30`),
      fetch(`/api/jobs/${state.jobId}/column-config`),
    ]);

    if (!previewResp.ok) throw new Error('Impossible de charger l\'aperçu');
    const preview = await previewResp.json();

    if (configResp.ok) {
      const configData = await configResp.json();
      state.columnConfig = configData.columns || {};
    }

    // Build header row
    preview.columns.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col;
      th.dataset.column = col;
      th.title = 'Cliquer pour configurer cette colonne';
      th.addEventListener('click', () => openColumnConfig(col));
      if (_isColumnConfigured(col)) th.classList.add('column-configured');
      headerRow.appendChild(th);
    });

    // Build body rows
    preview.rows.forEach(row => {
      const tr = document.createElement('tr');
      row.forEach((cell, i) => {
        const td = document.createElement('td');
        td.textContent = cell;
        td.dataset.colIdx = i;
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });

    loadingEl.hidden = true;
    tableEl.hidden = false;
  } catch (err) {
    loadingEl.textContent = 'Erreur lors du chargement de l\'aperçu : ' + err.message;
    loadingEl.className = 'msg-error';
  }
}

function openColumnConfig(colName) {
  // Auto-save previous column silently (local state only)
  if (state.activeColumn && state.activeColumn !== colName) {
    _saveCurrentPanelToState();
  }

  state.activeColumn = colName;

  // Update header highlights
  document.querySelectorAll('#preview-header th').forEach(th => {
    th.classList.toggle('column-selected', th.dataset.column === colName);
  });
  // Highlight column cells
  const colIdx = state.columns.indexOf(colName);
  document.querySelectorAll('#preview-body tr').forEach(tr => {
    tr.querySelectorAll('td').forEach((td, i) => {
      td.classList.toggle('column-selected', i === colIdx);
    });
  });

  // Populate panel
  const cfg = state.columnConfig[colName] || {};
  document.getElementById('col-config-name').textContent = colName;
  document.getElementById('cfg-required').checked = cfg.required || false;
  document.getElementById('cfg-content-type').value = cfg.content_type || '';
  document.getElementById('cfg-unique').checked = cfg.unique || false;
  document.getElementById('cfg-multiline').checked = cfg.multiline_ok || false;
  document.getElementById('cfg-min-length').value = cfg.min_length != null ? cfg.min_length : '';
  document.getElementById('cfg-max-length').value = cfg.max_length != null ? cfg.max_length : '';
  document.getElementById('cfg-forbidden-chars').value = cfg.forbidden_chars || '';
  document.getElementById('cfg-expected-case').value = cfg.expected_case || '';
  // List fields
  const listSep = cfg.list_separator || '';
  document.getElementById('cfg-list-separator').value = listSep;
  document.getElementById('cfg-list-unique').checked = cfg.list_unique || false;
  document.getElementById('cfg-list-no-empty').checked = cfg.list_no_empty !== false;  // default true
  document.getElementById('cfg-list-min-items').value = cfg.list_min_items != null ? cfg.list_min_items : '';
  document.getElementById('cfg-list-max-items').value = cfg.list_max_items != null ? cfg.list_max_items : '';
  _updateListOptionsState(listSep);
  // allowed_values: list → one per line
  const av = cfg.allowed_values;
  document.getElementById('cfg-allowed-values').value =
    Array.isArray(av) && av.length ? av.join('\n') : '';

  // Format preset: restore dropdown + conditional fields
  let preset = cfg.format_preset || '';
  if (!preset && cfg.regex) preset = 'custom';  // legacy: regex set but no preset stored
  document.getElementById('cfg-format-preset').value = preset;
  document.getElementById('cfg-regex').value = preset === 'custom' ? (cfg.regex || '') : '';
  _updateFormatPresetUI(preset);

  // Reset saved indicator
  const savedEl = document.getElementById('col-config-saved');
  savedEl.hidden = true;

  // Show panel
  document.getElementById('column-config-panel').hidden = false;
  document.getElementById('column-config-panel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeColumnConfig() {
  if (state.activeColumn) _saveCurrentPanelToState();
  state.activeColumn = null;

  document.querySelectorAll('#preview-header th').forEach(th => th.classList.remove('column-selected'));
  document.querySelectorAll('#preview-body td').forEach(td => td.classList.remove('column-selected'));
  document.getElementById('column-config-panel').hidden = true;
}

function _saveCurrentPanelToState() {
  if (!state.activeColumn) return;
  const cfg = _readPanelValues();
  state.columnConfig[state.activeColumn] = cfg;
}

function _readPanelValues() {
  const avRaw = document.getElementById('cfg-allowed-values').value.trim();
  const avList = avRaw ? avRaw.split('\n').map(s => s.trim()).filter(Boolean) : null;
  const minLen = document.getElementById('cfg-min-length').value;
  const maxLen = document.getElementById('cfg-max-length').value;

  const preset = document.getElementById('cfg-format-preset').value;
  let regex = null;
  let format_preset = null;
  if (preset === 'custom') {
    regex = document.getElementById('cfg-regex').value.trim() || null;
    format_preset = 'custom';
  } else if (preset && FORMAT_PRESETS[preset]) {
    regex = FORMAT_PRESETS[preset].regex;
    format_preset = preset;
  }

  return {
    required: document.getElementById('cfg-required').checked || false,
    content_type: document.getElementById('cfg-content-type').value || null,
    unique: document.getElementById('cfg-unique').checked,
    multiline_ok: document.getElementById('cfg-multiline').checked,
    format_preset,
    regex,
    min_length: minLen !== '' ? parseInt(minLen, 10) : null,
    max_length: maxLen !== '' ? parseInt(maxLen, 10) : null,
    forbidden_chars: document.getElementById('cfg-forbidden-chars').value || null,
    expected_case: document.getElementById('cfg-expected-case').value || null,
    allowed_values: avList,
    // List fields
    list_separator: document.getElementById('cfg-list-separator').value.trim() || null,
    list_unique: document.getElementById('cfg-list-unique').checked || false,
    list_no_empty: document.getElementById('cfg-list-no-empty').checked !== false,
    list_min_items: document.getElementById('cfg-list-min-items').value !== ''
      ? parseInt(document.getElementById('cfg-list-min-items').value, 10) : null,
    list_max_items: document.getElementById('cfg-list-max-items').value !== ''
      ? parseInt(document.getElementById('cfg-list-max-items').value, 10) : null,
  };
}

async function applyColumnConfig() {
  if (!state.jobId || !state.activeColumn) return;

  const cfg = _readPanelValues();
  state.columnConfig[state.activeColumn] = cfg;

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/column-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ columns: { [state.activeColumn]: cfg } }),
    });
    if (!resp.ok) throw new Error('Échec de l\'enregistrement');

    // Visual feedback
    const savedEl = document.getElementById('col-config-saved');
    savedEl.hidden = false;
    setTimeout(() => { savedEl.hidden = true; }, 2000);

    // Mark configured indicator on header
    _updateConfiguredMarker(state.activeColumn);
  } catch (err) {
    alert('Erreur lors de l\'enregistrement : ' + err.message);
  }
}

function _updateConfiguredMarker(colName) {
  const th = document.querySelector(`#preview-header th[data-column="${CSS.escape(colName)}"]`);
  if (!th) return;
  if (_isColumnConfigured(colName)) {
    th.classList.add('column-configured');
  } else {
    th.classList.remove('column-configured');
  }
}

function _isColumnConfigured(colName) {
  const cfg = state.columnConfig[colName];
  if (!cfg) return false;
  return !!(
    cfg.required ||
    cfg.content_type ||
    cfg.unique ||
    cfg.multiline_ok ||
    cfg.format_preset ||
    cfg.regex ||
    cfg.min_length != null ||
    cfg.max_length != null ||
    cfg.forbidden_chars ||
    cfg.expected_case ||
    (Array.isArray(cfg.allowed_values) && cfg.allowed_values.length) ||
    cfg.list_separator
  );
}

async function configureDone() {
  // Auto-save any open panel to server before leaving
  if (state.activeColumn) {
    _saveCurrentPanelToState();
    const cfg = state.columnConfig[state.activeColumn];
    try {
      await fetch(`/api/jobs/${state.jobId}/column-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns: { [state.activeColumn]: cfg } }),
      });
    } catch (_) { /* non-blocking */ }
  }
  closeColumnConfig();
  enableStep('fixes');
  goToStep('fixes');
}

// ---------------------------------------------------------------------------
// ÉTAPE 3 — Correctifs
// ---------------------------------------------------------------------------
async function previewFixes() {
  if (!state.jobId) return;
  const previewEl = document.getElementById('fixes-preview');
  previewEl.innerHTML = '<em>Calcul en cours…</em>';

  const formData = buildFixesFormData();
  formData.append('limit', '20');

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/fixes/preview`, {
      method: 'POST', body: formData,
    });
    const data = await resp.json();

    if (data.total === 0) {
      previewEl.innerHTML = '<p class="msg-info">Aucune modification détectée avec ces réglages.</p>';
      return;
    }

    let html = `<p class="msg-info">${data.total} cellule(s) concernée(s) (aperçu des 20 premières) :</p>`;
    html += '<table class="problems-table"><thead><tr><th>Colonne</th><th>Ligne</th><th>Avant</th><th>Après</th></tr></thead><tbody>';
    for (const item of (data['aperçu'] || [])) {
      html += `<tr><td>${esc(item['colonne'])}</td><td>${item['ligne']}</td><td><code>${esc(item['avant'])}</code></td><td><code>${esc(item['après'])}</code></td></tr>`;
    }
    html += '</tbody></table>';
    previewEl.innerHTML = html;
  } catch (err) {
    previewEl.innerHTML = '<p class="msg-error">Erreur lors du calcul de l\'aperçu.</p>';
  }
}

function buildFixesFormData() {
  const fd = new FormData();
  fd.append('trim', document.getElementById('fix-trim').checked);
  fd.append('collapse_spaces', document.getElementById('fix-collapse').checked);
  fd.append('replace_nbsp', document.getElementById('fix-nbsp').checked);
  fd.append('strip_invisible', document.getElementById('fix-invisible').checked);
  fd.append('normalize_unicode', document.getElementById('fix-unicode').checked);
  fd.append('normalize_newlines', document.getElementById('fix-newlines').checked);
  fd.append('columns', document.getElementById('fix-columns').value);
  return fd;
}

async function applyFixes() {
  if (!state.jobId) return;
  const formData = buildFixesFormData();
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/fixes`, { method: 'POST', body: formData });
    if (!resp.ok) throw new Error('Échec de l\'application des correctifs');
    enableStep('validate');
    goToStep('validate');
  } catch (err) {
    alert('Erreur : ' + err.message);
  }
}

function skipFixes() {
  enableStep('validate');
  goToStep('validate');
}

// ---------------------------------------------------------------------------
// ÉTAPE 4 — Validation
// ---------------------------------------------------------------------------
async function runValidation() {
  if (!state.jobId) return;

  const progEl = document.getElementById('validate-progress');
  const sumEl = document.getElementById('validate-summary');
  progEl.hidden = false;
  sumEl.hidden = true;

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/validate`, { method: 'POST' });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || 'Erreur de validation');
    }
    const data = await resp.json();
    const résumé = data['résumé'] || {};

    document.getElementById('sum-errors').textContent = résumé['erreurs'] ?? 0;
    document.getElementById('sum-warnings').textContent = résumé['avertissements'] ?? 0;
    document.getElementById('sum-suspicions').textContent = résumé['suspicions'] ?? 0;
    document.getElementById('sum-total').textContent = résumé['total'] ?? 0;

    progEl.hidden = true;
    sumEl.hidden = false;

    enableStep('results');
  } catch (err) {
    progEl.innerHTML = `<p class="msg-error">Erreur : ${esc(err.message)}</p>`;
  }
}

// ---------------------------------------------------------------------------
// ÉTAPE 5 — Résultats
// ---------------------------------------------------------------------------
let _currentProblemsTotal = 0;

async function loadProblems(page) {
  if (!state.jobId) return;
  state.currentPage = page;

  const severity = document.getElementById('filter-severity').value;
  const column = document.getElementById('filter-column').value;

  const url = new URL(`/api/jobs/${state.jobId}/problems`, window.location.origin);
  url.searchParams.set('page', page);
  url.searchParams.set('per_page', '50');
  if (severity) url.searchParams.set('severity', severity);
  if (column) url.searchParams.set('column', column);

  try {
    const resp = await fetch(url.toString());
    const data = await resp.json();
    _currentProblemsTotal = data.total;

    const tbody = document.getElementById('problems-body');
    const noIssues = document.getElementById('no-issues');
    const table = document.getElementById('problems-table');

    tbody.innerHTML = '';

    if (data.total === 0) {
      table.hidden = true;
      noIssues.hidden = false;
    } else {
      table.hidden = false;
      noIssues.hidden = true;
      for (const p of (data['problèmes'] || [])) {
        const sev = p['sévérité'];
        const sevClass = sev === 'ERROR' ? 'sev-error' : sev === 'WARNING' ? 'sev-warning' : 'sev-suspicion';
        const sevLabel = sev === 'ERROR' ? 'Erreur' : sev === 'WARNING' ? 'Avertissement' : 'Suspicion';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="${sevClass}">${sevLabel}</td>
          <td>${esc(p['colonne'])}</td>
          <td>${p['ligne']}</td>
          <td>${esc(p['message'])}</td>
          <td>${esc(p['suggestion'] || '')}</td>
        `;
        tbody.appendChild(tr);
      }
    }

    renderPagination(page, data.pages);
  } catch (err) {
    console.error('Erreur lors du chargement des problèmes', err);
  }
}

function renderPagination(current, total) {
  const el = document.getElementById('pagination');
  if (total <= 1) { el.innerHTML = ''; return; }

  let html = `<button onclick="loadProblems(${current - 1})" ${current <= 1 ? 'disabled' : ''}>← Précédent</button>`;
  for (let p = 1; p <= total; p++) {
    if (p === current) {
      html += `<button class="active" disabled>${p}</button>`;
    } else if (p === 1 || p === total || Math.abs(p - current) <= 2) {
      html += `<button onclick="loadProblems(${p})">${p}</button>`;
    } else if (Math.abs(p - current) === 3) {
      html += `<span>…</span>`;
    }
  }
  html += `<button onclick="loadProblems(${current + 1})" ${current >= total ? 'disabled' : ''}>Suivant →</button>`;
  html += `<span class="pagination-info">Page ${current} sur ${total}</span>`;
  el.innerHTML = html;
}

function downloadFile(filename) {
  if (!state.jobId) return false;
  window.location.href = `/api/jobs/${state.jobId}/download/${filename}`;
  return false;
}

// ---------------------------------------------------------------------------
// Réinitialisation
// ---------------------------------------------------------------------------
function resetApp() {
  state.jobId = null;
  state.filename = null;
  state.rows = 0;
  state.cols = 0;
  state.columns = [];
  state.columnConfig = {};
  state.activeColumn = null;

  // Reset file input
  fileInput.value = '';
  clearFile();

  // Reset fix checkboxes
  ['fix-trim','fix-collapse','fix-nbsp','fix-invisible','fix-unicode','fix-newlines'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.checked = false;
  });

  document.getElementById('fixes-preview').innerHTML = '';

  // Reset configure step
  document.getElementById('preview-loading').textContent = 'Chargement de l\'aperçu…';
  document.getElementById('preview-loading').className = 'msg-info';
  document.getElementById('preview-loading').hidden = false;
  document.getElementById('preview-table').hidden = true;
  document.getElementById('preview-header').innerHTML = '';
  document.getElementById('preview-body').innerHTML = '';
  document.getElementById('column-config-panel').hidden = true;
  document.getElementById('cfg-required').checked = false;
  document.getElementById('cfg-format-preset').value = '';
  document.getElementById('cfg-regex').value = '';
  document.getElementById('cfg-format-hint').hidden = true;
  document.getElementById('cfg-custom-regex-wrap').hidden = true;
  document.getElementById('cfg-forbidden-chars').value = '';
  document.getElementById('cfg-expected-case').value = '';
  document.getElementById('cfg-list-separator').value = '';
  document.getElementById('cfg-list-unique').checked = false;
  document.getElementById('cfg-list-no-empty').checked = true;
  document.getElementById('cfg-list-min-items').value = '';
  document.getElementById('cfg-list-max-items').value = '';
  _updateListOptionsState('');

  // Reset step buttons
  ['configure','fixes','validate','results'].forEach(step => {
    const btn = document.querySelector(`[data-step="${step}"]`);
    if (btn) btn.disabled = true;
  });

  // Go back to upload
  goToStep('upload');
  document.getElementById('upload-error').hidden = true;
  document.getElementById('upload-progress').hidden = true;
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
