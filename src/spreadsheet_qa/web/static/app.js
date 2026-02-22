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
  validationDone: false,  // true once validation has been run for this job
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
  if (step === 'fixes') updateUndoRedoButtons();
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
  // Le modèle importé manuellement a priorité sur le sélecteur builtin
  formData.append('template_id', _pendingTemplateFile
    ? 'generic_default'
    : document.getElementById('template-id').value);

  try {
    const resp = await fetch('/api/jobs', { method: 'POST', body: formData });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || 'Échec du téléversement');
    }
    const data = await resp.json();
    state.jobId = data.job_id;

    // Appliquer le modèle personnalisé s'il y en a un
    if (_pendingTemplateFile) {
      await _applyPendingTemplate(state.jobId);
    }
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

// Default Oui/Non values
const YESNO_DEFAULT_TRUE  = 'oui, o, vrai, true, yes, y, 1';
const YESNO_DEFAULT_FALSE = 'non, n, faux, false, no, 0';

// Build a case-insensitive regex from Oui/Non text fields
function _buildYesNoRegex() {
  const trueRaw  = document.getElementById('cfg-yesno-true').value.trim();
  const falseRaw = document.getElementById('cfg-yesno-false').value.trim();
  const trueVals  = (trueRaw  || YESNO_DEFAULT_TRUE ).split(',').map(s => s.trim()).filter(Boolean);
  const falseVals = (falseRaw || YESNO_DEFAULT_FALSE).split(',').map(s => s.trim()).filter(Boolean);
  const allVals = [...trueVals, ...falseVals];
  const escaped = allVals.map(v => v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return `(?i)^(${escaped.join('|')})$`;
}

// Show/hide hint, custom regex field, and Oui/Non fields based on selected preset
function _updateFormatPresetUI(presetValue) {
  const hintEl      = document.getElementById('cfg-format-hint');
  const customWrap  = document.getElementById('cfg-custom-regex-wrap');
  const yesnoWrap   = document.getElementById('cfg-yesno-wrap');

  hintEl.hidden     = true;
  customWrap.hidden = true;
  yesnoWrap.hidden  = true;

  if (presetValue === 'custom') {
    customWrap.hidden = false;
  } else if (presetValue === 'yes_no') {
    hintEl.textContent = FORMAT_PRESETS['yes_no'].hint;
    hintEl.hidden = false;
    yesnoWrap.hidden = false;
  } else if (presetValue && FORMAT_PRESETS[presetValue]) {
    hintEl.textContent = FORMAT_PRESETS[presetValue].hint;
    hintEl.hidden = false;
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

// Real-time preview debounce — listen on the whole panel (event delegation)
let _previewRuleTimer = null;
document.getElementById('column-config-panel')?.addEventListener('input',  () => _schedulePreviewRule());
document.getElementById('column-config-panel')?.addEventListener('change', () => _schedulePreviewRule());

// Show/hide rare-value sub-options based on checkbox state
document.getElementById('cfg-detect-rare')?.addEventListener('change', function () {
  document.getElementById('cfg-rare-options').hidden = !this.checked;
});

// Show/hide similar-values sub-options based on checkbox state
document.getElementById('cfg-detect-similar')?.addEventListener('change', function () {
  document.getElementById('cfg-similar-options').hidden = !this.checked;
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
      th.addEventListener('click', () => openColumnConfig(col));
      if (_isColumnConfigured(col)) {
        th.classList.add('column-configured');
        th.title = _buildConfigSummary(state.columnConfig[col]);
      } else {
        th.title = 'Cliquer pour configurer cette colonne';
      }
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

    // Apply cell-level issue highlights if validation has already been run
    if (state.validationDone) _applyCellIssueHighlights();

    // Consume pending cell navigation (triggered from the Results step)
    if (_pendingCellNav) {
      const nav = _pendingCellNav;
      _pendingCellNav = null;
      setTimeout(() => _highlightCell(nav.rowIdx, nav.colName), 50);
    }
  } catch (err) {
    loadingEl.textContent = 'Erreur lors du chargement de l\'aperçu : ' + err.message;
    loadingEl.className = 'msg-error';
  }
}

async function _applyCellIssueHighlights() {
  if (!state.jobId || !state.validationDone) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/preview-issues?rows=30`);
    if (!resp.ok) return;
    const data = await resp.json();
    const issues = data.cell_issues || [];
    if (!issues.length) return;

    // Map column name → td index
    const colIndexMap = {};
    state.columns.forEach((col, i) => { colIndexMap[col] = i; });

    const rows = document.querySelectorAll('#preview-body tr');
    issues.forEach(issue => {
      const tr = rows[issue.row];
      if (!tr) return;
      const colIdx = colIndexMap[issue.col];
      if (colIdx == null) return;
      const td = tr.querySelectorAll('td')[colIdx];
      if (!td) return;
      td.classList.add(`cell-${issue.severity}`);
      td.title = issue.message;
    });
  } catch (_) { /* non-bloquant */ }
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
  // Format preset: restore dropdown + conditional fields
  let preset = cfg.format_preset || '';
  if (!preset && cfg.regex) preset = 'custom';  // legacy: regex set but no preset stored
  document.getElementById('cfg-format-preset').value = preset;
  document.getElementById('cfg-regex').value = preset === 'custom' ? (cfg.regex || '') : '';
  // Oui/Non custom values
  document.getElementById('cfg-yesno-true').value  = cfg.yes_no_true_values  || '';
  document.getElementById('cfg-yesno-false').value = cfg.yes_no_false_values || '';
  _updateFormatPresetUI(preset);

  // Rare-value detection fields
  const detectRare = cfg.detect_rare_values || false;
  document.getElementById('cfg-detect-rare').checked = detectRare;
  document.getElementById('cfg-rare-options').hidden = !detectRare;
  document.getElementById('cfg-rare-threshold').value  = cfg.rare_threshold  != null ? cfg.rare_threshold  : 1;
  document.getElementById('cfg-rare-min-total').value  = cfg.rare_min_total  != null ? cfg.rare_min_total  : 10;

  // Similar-value detection fields
  const detectSimilar = cfg.detect_similar_values || false;
  const cfgDetectSimilarEl = document.getElementById('cfg-detect-similar');
  if (cfgDetectSimilarEl) cfgDetectSimilarEl.checked = detectSimilar;
  const cfgSimilarOptionsEl = document.getElementById('cfg-similar-options');
  if (cfgSimilarOptionsEl) cfgSimilarOptionsEl.hidden = !detectSimilar;
  const cfgSimilarThreshEl = document.getElementById('cfg-similar-threshold');
  if (cfgSimilarThreshEl) cfgSimilarThreshEl.value = cfg.similar_threshold != null ? cfg.similar_threshold : 85;

  // Allowed-values: handle lock flag
  const avArr = cfg.allowed_values;
  const avStr = Array.isArray(avArr) && avArr.length ? avArr.join('\n') : '';
  const locked = cfg.allowed_values_locked || false;
  const avEl = document.getElementById('cfg-allowed-values');
  avEl.readOnly = locked;
  avEl.classList.toggle('av-locked', locked);
  document.getElementById('cfg-av-locked-msg').hidden = !locked;
  if (locked && Array.isArray(avArr) && avArr.length > 20) {
    avEl.value = avArr.slice(0, 20).join('\n');
    const countEl = document.getElementById('cfg-av-count-msg');
    countEl.textContent = `${avArr.length} valeurs autorisées`;
    countEl.hidden = false;
    const btn = document.getElementById('cfg-av-voir-tout');
    btn.hidden = false;
    btn.textContent = 'Voir tout';
    btn.dataset.full = avStr;
  } else {
    avEl.value = avStr;
    document.getElementById('cfg-av-count-msg').hidden = true;
    document.getElementById('cfg-av-voir-tout').hidden = true;
  }

  // Vocabulaire NAKALA : restaurer la sélection et réinitialiser le statut
  document.getElementById('cfg-nakala-vocabulary').value = cfg.nakala_vocabulary || '';
  const nakalaStatusEl = document.getElementById('nakala-vocab-status');
  nakalaStatusEl.hidden = true;
  nakalaStatusEl.textContent = '';
  nakalaStatusEl.className = 'format-hint';

  // Reset saved indicator
  const savedEl = document.getElementById('col-config-saved');
  savedEl.hidden = true;

  // Show panel
  document.getElementById('column-config-panel').hidden = false;
  document.getElementById('column-config-panel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // Trigger initial preview
  _schedulePreviewRule();
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
  const avEl = document.getElementById('cfg-allowed-values');
  const avLocked = avEl.readOnly;
  let avList = null;
  if (!avLocked) {
    // Editable: read from textarea
    const avRaw = avEl.value.trim();
    avList = avRaw ? avRaw.split('\n').map(s => s.trim()).filter(Boolean) : null;
  } else {
    // Locked: preserve existing values from state (don't erase with null)
    const stateCfg = state.activeColumn ? (state.columnConfig[state.activeColumn] || {}) : {};
    avList = stateCfg.allowed_values || null;
  }

  const minLen = document.getElementById('cfg-min-length').value;
  const maxLen = document.getElementById('cfg-max-length').value;

  const preset = document.getElementById('cfg-format-preset').value;
  let regex = null;
  let format_preset = null;
  let yes_no_true_values = null;
  let yes_no_false_values = null;
  if (preset === 'custom') {
    regex = document.getElementById('cfg-regex').value.trim() || null;
    format_preset = 'custom';
  } else if (preset === 'yes_no') {
    yes_no_true_values  = document.getElementById('cfg-yesno-true').value.trim()  || null;
    yes_no_false_values = document.getElementById('cfg-yesno-false').value.trim() || null;
    regex = _buildYesNoRegex();
    format_preset = 'yes_no';
  } else if (preset && FORMAT_PRESETS[preset]) {
    regex = FORMAT_PRESETS[preset].regex;
    format_preset = preset;
  }

  const detectRare = document.getElementById('cfg-detect-rare').checked;

  return {
    required: document.getElementById('cfg-required').checked || false,
    content_type: document.getElementById('cfg-content-type').value || null,
    unique: document.getElementById('cfg-unique').checked,
    multiline_ok: document.getElementById('cfg-multiline').checked,
    format_preset,
    regex,
    yes_no_true_values,
    yes_no_false_values,
    min_length: minLen !== '' ? parseInt(minLen, 10) : null,
    max_length: maxLen !== '' ? parseInt(maxLen, 10) : null,
    forbidden_chars: document.getElementById('cfg-forbidden-chars').value || null,
    expected_case: document.getElementById('cfg-expected-case').value || null,
    allowed_values: avList,
    allowed_values_locked: avLocked,
    nakala_vocabulary: document.getElementById('cfg-nakala-vocabulary').value || null,
    // List fields
    list_separator: document.getElementById('cfg-list-separator').value.trim() || null,
    list_unique: document.getElementById('cfg-list-unique').checked || false,
    list_no_empty: document.getElementById('cfg-list-no-empty').checked !== false,
    list_min_items: document.getElementById('cfg-list-min-items').value !== ''
      ? parseInt(document.getElementById('cfg-list-min-items').value, 10) : null,
    list_max_items: document.getElementById('cfg-list-max-items').value !== ''
      ? parseInt(document.getElementById('cfg-list-max-items').value, 10) : null,
    // Rare-value detection
    detect_rare_values: detectRare,
    rare_threshold: detectRare
      ? (parseInt(document.getElementById('cfg-rare-threshold').value, 10) || 1)
      : null,
    rare_min_total: detectRare
      ? (parseInt(document.getElementById('cfg-rare-min-total').value, 10) || 10)
      : null,
    // Similar-value detection
    detect_similar_values: document.getElementById('cfg-detect-similar')?.checked || false,
    similar_threshold: document.getElementById('cfg-detect-similar')?.checked
      ? (parseInt(document.getElementById('cfg-similar-threshold')?.value, 10) || 85)
      : null,
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

    // Mark configured indicators on all header columns
    _updateColumnBadges();
  } catch (err) {
    alert('Erreur lors de l\'enregistrement : ' + err.message);
  }
}

function _buildConfigSummary(cfg) {
  if (!cfg) return '';
  const parts = [];
  if (cfg.required) parts.push('Obligatoire');
  if (cfg.content_type) {
    const types = { integer: 'Nombre entier', decimal: 'Nombre décimal', date: 'Date', email: 'E-mail', url: 'URL' };
    parts.push('Type : ' + (types[cfg.content_type] || cfg.content_type));
  }
  if (cfg.unique) parts.push('Valeurs uniques');
  if (cfg.format_preset && cfg.format_preset !== 'custom') {
    const labels = { year: 'Année', yes_no: 'Oui/Non', alphanum: 'Alphanumérique',
      letters_only: 'Lettres', positive_int: 'Entier positif', doi: 'DOI',
      orcid: 'ORCID', ark: 'ARK', issn: 'ISSN', w3cdtf: 'Date W3C-DTF',
      iso_date: 'Date ISO', lang_iso639: 'Langue ISO 639' };
    parts.push('Format : ' + (labels[cfg.format_preset] || cfg.format_preset));
  } else if (cfg.format_preset === 'custom' && cfg.regex) {
    parts.push('Regex personnalisée');
  }
  if (Array.isArray(cfg.allowed_values) && cfg.allowed_values.length) {
    parts.push(`${cfg.allowed_values.length} valeur(s) autorisée(s)`);
  }
  if (cfg.min_length != null || cfg.max_length != null) {
    const lo = cfg.min_length != null ? `min ${cfg.min_length}` : '';
    const hi = cfg.max_length != null ? `max ${cfg.max_length}` : '';
    parts.push('Longueur : ' + [lo, hi].filter(Boolean).join(', '));
  }
  if (cfg.forbidden_chars) parts.push(`Chars interdits : ${cfg.forbidden_chars}`);
  if (cfg.expected_case) {
    const cases = { upper: 'MAJUSCULES', lower: 'minuscules', title: 'Titre' };
    parts.push('Casse : ' + (cases[cfg.expected_case] || cfg.expected_case));
  }
  if (cfg.list_separator) parts.push(`Liste (séparateur "${cfg.list_separator}")`);
  if (cfg.detect_rare_values) parts.push('Valeurs rares détectées');
  return parts.join(' · ') || 'Configurée';
}

function _updateColumnBadges() {
  state.columns.forEach(col => _updateConfiguredMarker(col));
}

function _updateConfiguredMarker(colName) {
  const th = document.querySelector(`#preview-header th[data-column="${CSS.escape(colName)}"]`);
  if (!th) return;
  if (_isColumnConfigured(colName)) {
    th.classList.add('column-configured');
    th.title = _buildConfigSummary(state.columnConfig[colName]);
  } else {
    th.classList.remove('column-configured');
    th.title = 'Cliquer pour configurer cette colonne';
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
    cfg.list_separator ||
    cfg.detect_similar_values
  );
}

async function showConfigSummary() {
  // Auto-save any open panel
  if (state.activeColumn) {
    _saveCurrentPanelToState();
    const cfg = state.columnConfig[state.activeColumn];
    try {
      await fetch(`/api/jobs/${state.jobId}/column-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns: { [state.activeColumn]: cfg } }),
      });
    } catch (_) {}
    closeColumnConfig();
  }

  // Build summary table
  const configuredCols = state.columns.filter(col => _isColumnConfigured(col));
  const unconfiguredCount = state.columns.length - configuredCols.length;

  let html = '';
  if (configuredCols.length > 0) {
    html += '<table class="summary-table"><thead><tr><th>Colonne</th><th>Configuration</th></tr></thead><tbody>';
    for (const col of configuredCols) {
      const summary = _buildConfigSummary(state.columnConfig[col]);
      html += `<tr><td class="summary-col-name">${esc(col)}</td><td>${esc(summary)}</td></tr>`;
    }
    html += '</tbody></table>';
  } else {
    html += '<p class="msg-info">Aucune colonne n\'a été configurée spécifiquement.</p>';
  }
  if (unconfiguredCount > 0) {
    html += `<p class="summary-unconfigured">${unconfiguredCount} colonne${unconfiguredCount > 1 ? 's' : ''} sans configuration spécifique.</p>`;
  }

  document.getElementById('config-summary-content').innerHTML = html;
  const summaryEl = document.getElementById('config-summary');
  summaryEl.hidden = false;
  summaryEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideConfigSummary() {
  document.getElementById('config-summary').hidden = true;
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
    await updateUndoRedoButtons();
    enableStep('validate');
    goToStep('validate');
  } catch (err) {
    alert('Erreur : ' + err.message);
  }
}

/** Annuler le dernier correctif. */
async function undoFix() {
  if (!state.jobId) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/undo`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      _showToast('↩ Correctif annulé', 'success');
      await previewFixes();
    } else {
      _showToast(data.message || 'Rien à annuler.', 'warning');
    }
    _syncUndoRedoButtons(data.can_undo, data.can_redo);
  } catch (err) {
    _showToast('Erreur : ' + err.message, 'error');
  }
}

/** Rétablir le dernier correctif annulé. */
async function redoFix() {
  if (!state.jobId) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/redo`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      _showToast('↪ Correctif rétabli', 'success');
      await previewFixes();
    } else {
      _showToast(data.message || 'Rien à rétablir.', 'warning');
    }
    _syncUndoRedoButtons(data.can_undo, data.can_redo);
  } catch (err) {
    _showToast('Erreur : ' + err.message, 'error');
  }
}

/** Interroge GET /history et met à jour les boutons undo/redo. */
async function updateUndoRedoButtons() {
  if (!state.jobId) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/history`);
    if (!resp.ok) return;
    const data = await resp.json();
    _syncUndoRedoButtons(data.can_undo, data.can_redo);
  } catch (_) { /* non-bloquant */ }
}

function _syncUndoRedoButtons(canUndo, canRedo) {
  const btnUndo = document.getElementById('btn-undo');
  const btnRedo = document.getElementById('btn-redo');
  if (btnUndo) btnUndo.disabled = !canUndo;
  if (btnRedo) btnRedo.disabled = !canRedo;
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
    state.validationDone = true;

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
  const statusFilter = document.getElementById('filter-status')?.value || '';

  const url = new URL(`/api/jobs/${state.jobId}/problems`, window.location.origin);
  url.searchParams.set('page', page);
  url.searchParams.set('per_page', '50');
  if (severity) url.searchParams.set('severity', severity);
  if (column) url.searchParams.set('column', column);
  if (statusFilter) url.searchParams.set('status', statusFilter);

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
        const status = p['statut'] || 'OPEN';
        const issueId = p['issue_id'] || '';

        const tr = document.createElement('tr');
        tr.classList.add('problem-row-clickable');
        if (status === 'IGNORED') tr.classList.add('issue-ignored');
        if (status === 'EXCEPTED') tr.classList.add('issue-excepted');
        tr.dataset.row = p['ligne'];
        tr.dataset.col = p['colonne'];
        tr.dataset.issueId = issueId;
        tr.addEventListener('click', (e) => {
          if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
          navigateToCell(parseInt(tr.dataset.row), tr.dataset.col);
        });

        // Checkbox cell
        const tdCheck = document.createElement('td');
        tdCheck.className = 'td-check';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.className = 'problem-checkbox';
        cb.dataset.issueId = issueId;
        cb.addEventListener('change', _updateBulkActionBar);
        tdCheck.appendChild(cb);
        tr.appendChild(tdCheck);

        const tdSev = document.createElement('td');
        tdSev.className = sevClass;
        tdSev.textContent = sevLabel;
        tr.appendChild(tdSev);

        const tdCol = document.createElement('td');
        tdCol.textContent = p['colonne'];
        tr.appendChild(tdCol);

        const tdLig = document.createElement('td');
        tdLig.textContent = p['ligne'];
        tr.appendChild(tdLig);

        const tdMsg = document.createElement('td');
        tdMsg.textContent = p['message'];
        tr.appendChild(tdMsg);

        const tdSug = document.createElement('td');
        tdSug.textContent = p['suggestion'] || '';
        tr.appendChild(tdSug);

        // Actions cell
        const tdAct = document.createElement('td');
        tdAct.className = 'td-actions';
        if (status === 'OPEN') {
          const bIgn = document.createElement('button');
          bIgn.className = 'btn-status btn-ignore';
          bIgn.textContent = 'Ignorer';
          bIgn.title = 'Ignorer ce problème';
          bIgn.onclick = () => setIssueStatus(issueId, 'IGNORED');
          const bExc = document.createElement('button');
          bExc.className = 'btn-status btn-except';
          bExc.textContent = 'Exclure';
          bExc.title = 'Exclure ce problème (exception documentée)';
          bExc.onclick = () => setIssueStatus(issueId, 'EXCEPTED');
          tdAct.appendChild(bIgn);
          tdAct.appendChild(bExc);
        } else {
          const bReo = document.createElement('button');
          bReo.className = 'btn-status btn-reopen';
          bReo.textContent = 'Rouvrir';
          bReo.title = 'Remettre ce problème à l\'état ouvert';
          bReo.onclick = () => setIssueStatus(issueId, 'OPEN');
          tdAct.appendChild(bReo);
        }
        tr.appendChild(tdAct);

        const tdNav = document.createElement('td');
        tdNav.innerHTML = '<span class="problem-nav-icon" title="Localiser dans le tableau">→</span>';
        tr.appendChild(tdNav);

        tbody.appendChild(tr);
      }
    }

    // Reset check-all and bulk bar after reload
    const checkAll = document.getElementById('check-all-problems');
    if (checkAll) checkAll.checked = false;
    _updateBulkActionBar();

    renderPagination(page, data.pages);
  } catch (err) {
    console.error('Erreur lors du chargement des problèmes', err);
  }
}

// ---------------------------------------------------------------------------
// Gestion des statuts d'issues (Ignorer / Exclure / Rouvrir)
// ---------------------------------------------------------------------------

async function setIssueStatus(issueId, newStatus) {
  if (!state.jobId || !issueId) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/issues/${issueId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      throw new Error(d.detail || 'Échec');
    }
    await loadProblems(state.currentPage);
  } catch (err) {
    _showToast('Erreur : ' + err.message, 'error');
  }
}

async function _bulkSetStatus(status) {
  if (!state.jobId) return;
  const checkboxes = document.querySelectorAll('.problem-checkbox:checked');
  const ids = Array.from(checkboxes).map(cb => cb.dataset.issueId).filter(Boolean);
  if (!ids.length) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/issues/bulk-status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ issue_ids: ids, status }),
    });
    if (!resp.ok) throw new Error('Échec');
    const data = await resp.json();
    const label = status === 'IGNORED' ? 'ignoré(s)' : status === 'EXCEPTED' ? 'exclu(s)' : 'rouvert(s)';
    _showToast(`✓ ${data.changed} problème(s) ${label}`, 'success');
    await loadProblems(state.currentPage);
  } catch (err) {
    _showToast('Erreur : ' + err.message, 'error');
  }
}

function bulkIgnoreSelected()  { return _bulkSetStatus('IGNORED'); }
function bulkExceptSelected()  { return _bulkSetStatus('EXCEPTED'); }
function bulkReopenSelected()  { return _bulkSetStatus('OPEN'); }

function toggleAllProblems(checkbox) {
  document.querySelectorAll('.problem-checkbox').forEach(cb => {
    cb.checked = checkbox.checked;
  });
  _updateBulkActionBar();
}

function _updateBulkActionBar() {
  const checked = document.querySelectorAll('.problem-checkbox:checked').length;
  const bar = document.getElementById('bulk-action-bar');
  const countEl = document.getElementById('bulk-selected-count');
  if (bar) bar.hidden = checked === 0;
  if (countEl) countEl.textContent = `${checked} sélectionné${checked > 1 ? 's' : ''}`;
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
// Aperçu temps réel (preview-rule)
// ---------------------------------------------------------------------------
function _schedulePreviewRule() {
  clearTimeout(_previewRuleTimer);
  _previewRuleTimer = setTimeout(_fetchPreviewRule, 300);
}

function _hasActiveConstraints() {
  if (!state.activeColumn) return false;
  const cfg = _readPanelValues();
  return !!(
    cfg.required || cfg.content_type || cfg.unique || cfg.format_preset ||
    cfg.regex || cfg.min_length != null || cfg.max_length != null ||
    cfg.forbidden_chars || cfg.expected_case ||
    (Array.isArray(cfg.allowed_values) && cfg.allowed_values.length) ||
    cfg.detect_rare_values
  );
}

async function _fetchPreviewRule() {
  const previewEl = document.getElementById('rule-preview');
  if (!previewEl || !state.jobId || !state.activeColumn) return;

  if (!_hasActiveConstraints()) {
    previewEl.innerHTML = '<span class="rule-preview-empty">Aucune contrainte configurée.</span>';
    return;
  }

  previewEl.innerHTML = '<span class="rule-preview-loading"><span class="spinner-sm"></span> Calcul…</span>';

  try {
    const cfg = _readPanelValues();
    const resp = await fetch(`/api/jobs/${state.jobId}/preview-rule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ column: state.activeColumn, config: cfg }),
    });
    if (!resp.ok) throw new Error('Aperçu indisponible');
    const data = await resp.json();
    _renderPreviewRule(previewEl, data);
  } catch (_) {
    previewEl.innerHTML = '<span class="rule-preview-empty">Aperçu non disponible.</span>';
  }
}

function _renderPreviewRule(el, data) {
  const okCount   = data.total_ok   ?? 0;
  const failCount = data.total_fail ?? 0;
  const sampleOk  = data.sample_ok  || [];
  const sampleFail = data.sample_fail || [];

  let html = '<div class="rp-row">';

  // OK column
  html += `<div class="rp-col rp-ok">`;
  html += `<div class="rp-count rp-count-ok">✅ ${okCount} valeur${okCount !== 1 ? 's' : ''} valide${okCount !== 1 ? 's' : ''}</div>`;
  if (sampleOk.length) {
    html += '<ul class="rp-list">';
    sampleOk.forEach(v => { html += `<li>${esc(v)}</li>`; });
    html += '</ul>';
  }
  html += '</div>';

  // Fail column
  html += `<div class="rp-col rp-fail">`;
  html += `<div class="rp-count rp-count-fail">❌ ${failCount} valeur${failCount !== 1 ? 's' : ''} en erreur</div>`;
  if (sampleFail.length) {
    html += '<ul class="rp-list">';
    sampleFail.forEach(item => {
      const val = item.value === '' ? '(vide)' : item.value;
      const msg = item.message.length > 60 ? item.message.slice(0, 57) + '…' : item.message;
      html += `<li title="${esc(item.message)}"><code>${esc(val)}</code> → ${esc(msg)}</li>`;
    });
    html += '</ul>';
  }
  html += '</div>';

  html += '</div>';
  el.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Valeurs autorisées — Voir tout / Réduire
// ---------------------------------------------------------------------------
function _toggleAllowedValuesExpand() {
  const avEl = document.getElementById('cfg-allowed-values');
  const btn  = document.getElementById('cfg-av-voir-tout');
  if (btn.textContent === 'Voir tout') {
    avEl.value = btn.dataset.full;
    btn.textContent = 'Réduire';
  } else {
    avEl.value = btn.dataset.full.split('\n').slice(0, 20).join('\n');
    btn.textContent = 'Voir tout';
  }
}

// ---------------------------------------------------------------------------
// Vocabulaire distant NAKALA
// ---------------------------------------------------------------------------
async function loadNakalaVocabulary() {
  const vocabName = document.getElementById('cfg-nakala-vocabulary').value;
  const statusEl  = document.getElementById('nakala-vocab-status');

  if (!vocabName) {
    statusEl.textContent = 'Sélectionnez un vocabulaire dans la liste.';
    statusEl.className = 'format-hint msg-warning';
    statusEl.hidden = false;
    return;
  }

  statusEl.textContent = 'Chargement du vocabulaire…';
  statusEl.className = 'format-hint';
  statusEl.hidden = false;

  try {
    const resp = await fetch(`/api/nakala/vocabulary/${vocabName}`);
    const data = await resp.json();

    if (!resp.ok) {
      statusEl.textContent = data.detail || 'Erreur lors du chargement du vocabulaire.';
      statusEl.className = 'format-hint msg-error';
      return;
    }

    const values = data.values || [];

    // Lock the allowed-values textarea and populate it
    const avEl = document.getElementById('cfg-allowed-values');
    avEl.readOnly = true;
    avEl.classList.add('av-locked');
    document.getElementById('cfg-av-locked-msg').hidden = false;

    const countEl = document.getElementById('cfg-av-count-msg');
    countEl.textContent = `${values.length} valeurs chargées depuis NAKALA`;
    countEl.hidden = false;

    const allStr = values.join('\n');
    if (values.length > 20) {
      avEl.value = values.slice(0, 20).join('\n');
      const btn = document.getElementById('cfg-av-voir-tout');
      btn.hidden = false;
      btn.textContent = 'Voir tout';
      btn.dataset.full = allStr;
    } else {
      avEl.value = allStr;
      document.getElementById('cfg-av-voir-tout').hidden = true;
    }

    // Update local state directly (bypass _readPanelValues for locked values)
    if (state.activeColumn) {
      if (!state.columnConfig[state.activeColumn]) state.columnConfig[state.activeColumn] = {};
      state.columnConfig[state.activeColumn].allowed_values = values;
      state.columnConfig[state.activeColumn].allowed_values_locked = true;
      state.columnConfig[state.activeColumn].nakala_vocabulary = vocabName;
    }

    statusEl.textContent = `${values.length} valeurs chargées depuis NAKALA.`;
    statusEl.className = 'format-hint msg-success';

    // Auto-save to server
    if (state.jobId && state.activeColumn) {
      try {
        await fetch(`/api/jobs/${state.jobId}/column-config`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            columns: {
              [state.activeColumn]: {
                allowed_values: values,
                allowed_values_locked: true,
                nakala_vocabulary: vocabName,
              },
            },
          }),
        });
        _updateColumnBadges();
      } catch (_) { /* non-bloquant */ }
    }
  } catch (err) {
    statusEl.textContent = 'Erreur : ' + err.message;
    statusEl.className = 'format-hint msg-error';
  }
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
  state.currentPage = 1;
  state.columnConfig = {};
  state.activeColumn = null;
  state.validationDone = false;
  _pendingCellNav = null;
  const bulkBar = document.getElementById('bulk-action-bar');
  if (bulkBar) bulkBar.hidden = true;
  const checkAll = document.getElementById('check-all-problems');
  if (checkAll) checkAll.checked = false;

  // Reset file input
  fileInput.value = '';
  clearFile();

  // Reset modèle personnalisé Upload
  _pendingTemplateFile = null;
  const uploadTplInput = document.getElementById('upload-template-input');
  if (uploadTplInput) uploadTplInput.value = '';
  const uploadTplName = document.getElementById('upload-template-name');
  if (uploadTplName) uploadTplName.hidden = true;

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
  document.getElementById('config-summary').hidden = true;
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
  // Oui/Non
  document.getElementById('cfg-yesno-true').value = '';
  document.getElementById('cfg-yesno-false').value = '';
  // Valeurs autorisées (locked)
  const avEl = document.getElementById('cfg-allowed-values');
  avEl.value = '';
  avEl.readOnly = false;
  avEl.classList.remove('av-locked');
  document.getElementById('cfg-av-locked-msg').hidden = true;
  document.getElementById('cfg-av-count-msg').hidden = true;
  document.getElementById('cfg-av-voir-tout').hidden = true;
  // Valeurs rares
  document.getElementById('cfg-detect-rare').checked = false;
  document.getElementById('cfg-rare-options').hidden = true;
  document.getElementById('cfg-rare-threshold').value = 1;
  document.getElementById('cfg-rare-min-total').value = 10;
  // Valeurs similaires
  const rstSimilar = document.getElementById('cfg-detect-similar');
  if (rstSimilar) rstSimilar.checked = false;
  const rstSimilarOpts = document.getElementById('cfg-similar-options');
  if (rstSimilarOpts) rstSimilarOpts.hidden = true;
  const rstSimilarThresh = document.getElementById('cfg-similar-threshold');
  if (rstSimilarThresh) rstSimilarThresh.value = 85;

  // Reset step buttons
  ['configure','fixes','validate','results'].forEach(step => {
    const btn = document.querySelector(`[data-step="${step}"]`);
    if (btn) btn.disabled = true;
  });
  _syncUndoRedoButtons(false, false);

  // Go back to upload
  goToStep('upload');
  document.getElementById('upload-error').hidden = true;
  document.getElementById('upload-progress').hidden = true;
}

// ---------------------------------------------------------------------------
// Navigation cellule (étape Résultats → Configurer)
// ---------------------------------------------------------------------------

/** Navigation en attente quand le tableau n'est pas encore rendu. */
let _pendingCellNav = null;

/**
 * Naviguer vers une cellule (row 1-based, colName) depuis l'étape Résultats.
 * Si row > 30 : toast informatif (au-delà du preview).
 * Sinon : basculer sur Configurer + scroll + flash.
 */
function navigateToCell(row1based, colName) {
  if (row1based > 30) {
    _showToast(
      `Ligne ${row1based} — au-delà de l'aperçu (30 premières lignes affichées)`,
      'warning'
    );
    return;
  }
  const rowIdx = row1based - 1;
  if (state.currentStep === 'configure') {
    _highlightCell(rowIdx, colName);
  } else {
    _pendingCellNav = { rowIdx, colName };
    goToStep('configure');
  }
}

/** Scroll et flash sur le <td> ciblé dans le tableau d'aperçu. */
function _highlightCell(rowIdx, colName) {
  const colIdx = state.columns.indexOf(colName);
  if (colIdx < 0) return;
  const rows = document.querySelectorAll('#preview-body tr');
  const tr = rows[rowIdx];
  if (!tr) return;
  const td = tr.querySelectorAll('td')[colIdx];
  if (!td) return;
  td.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
  td.classList.remove('cell-highlight-flash');
  // Force reflow pour relancer l'animation si déjà active
  void td.offsetWidth;
  td.classList.add('cell-highlight-flash');
  setTimeout(() => td.classList.remove('cell-highlight-flash'), 1500);
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

// ---------------------------------------------------------------------------
// Export / Import de modèle — étape Configurer
// ---------------------------------------------------------------------------

/** Déclenche le téléchargement du template YAML courant. */
async function exportTemplate() {
  if (!state.jobId) {
    _showToast('Aucun fichier chargé.', 'error');
    return;
  }
  const configuredCols = state.columns.filter(col => _isColumnConfigured(col));
  if (configuredCols.length === 0) {
    _showToast('Configurez au moins une colonne avant d\'exporter.', 'warning');
    return;
  }

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/export-template`);
    if (!resp.ok) throw new Error('Échec de l\'export');

    // Extraire le nom de fichier depuis Content-Disposition
    const cd = resp.headers.get('content-disposition') || '';
    const match = cd.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : 'template.yml';

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    _showToast('✓ Configuration exportée : ' + filename, 'success');
  } catch (err) {
    _showToast('✗ Erreur lors de l\'export : ' + err.message, 'error');
  }
}

/** Ouvre le sélecteur de fichier pour l'import de modèle (étape Configurer). */
function triggerImportTemplate() {
  const input = document.getElementById('import-template-input');
  if (input) input.click();
}

// Écoute du changement de fichier pour l'import dans Configurer
document.getElementById('import-template-input')?.addEventListener('change', async function () {
  if (!this.files.length || !state.jobId) return;
  const file = this.files[0];
  this.value = '';  // reset pour pouvoir re-sélectionner le même fichier

  const fd = new FormData();
  fd.append('file', file);

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/import-template`, {
      method: 'POST',
      body: fd,
    });
    const data = await resp.json();

    if (!resp.ok) {
      _showToast('✗ ' + (data.detail || 'Fichier YAML invalide'), 'error');
      return;
    }

    // Notification avec niveau selon présence de colonnes ignorées
    const level = data.skipped && data.skipped.length > 0 ? 'warning' : 'success';
    const prefix = level === 'warning' ? '⚠' : '✓';
    _showToast(prefix + ' ' + data.message, level);

    // Recharger la config et rafraîchir l'aperçu
    await _reloadColumnConfigFromServer();
    _updateColumnBadges();

    // Si un panneau est ouvert, le rafraîchir
    if (state.activeColumn && state.columnConfig[state.activeColumn]) {
      openColumnConfig(state.activeColumn);
    }
  } catch (err) {
    _showToast('✗ Erreur lors de l\'import : ' + err.message, 'error');
  }
});

/** Recharge la column config depuis le serveur et met à jour state.columnConfig. */
async function _reloadColumnConfigFromServer() {
  if (!state.jobId) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/column-config`);
    if (resp.ok) {
      const data = await resp.json();
      // Fusionner : les valeurs serveur ont priorité
      const serverCols = data.columns || {};
      Object.entries(serverCols).forEach(([col, cfg]) => {
        state.columnConfig[col] = Object.assign(state.columnConfig[col] || {}, cfg);
      });
    }
  } catch (_) { /* non-bloquant */ }
}

/** Affiche un toast temporaire (4 s). type: 'success' | 'warning' | 'error' */
let _toastTimer = null;
function _showToast(message, type) {
  const el = document.getElementById('template-toast');
  if (!el) return;

  clearTimeout(_toastTimer);
  el.textContent = message;
  el.className = `template-toast toast-${type}`;
  el.hidden = false;

  _toastTimer = setTimeout(() => {
    el.style.animation = 'none';
    el.hidden = true;
    el.style.animation = '';
  }, 4000);
}

// ---------------------------------------------------------------------------
// Import de vocabulaire — panneau de config colonne (étape Configurer)
// ---------------------------------------------------------------------------

/** Ouvre le sélecteur de fichier pour l'import de vocabulaire. */
function triggerImportVocabulary() {
  const input = document.getElementById('import-vocabulary-input');
  if (input) input.click();
}

document.getElementById('import-vocabulary-input')?.addEventListener('change', async function () {
  if (!this.files.length || !state.jobId || !state.activeColumn) return;
  const file = this.files[0];
  this.value = '';

  const fd = new FormData();
  fd.append('file', file);

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/import-vocabulary`, {
      method: 'POST',
      body: fd,
    });
    const data = await resp.json();

    if (!resp.ok) {
      _showToast('✗ ' + (data.detail || 'Fichier invalide'), 'error');
      return;
    }

    // Populate allowed-values textarea (editable, non-locked)
    const avEl = document.getElementById('cfg-allowed-values');
    avEl.readOnly = false;
    avEl.classList.remove('av-locked');
    document.getElementById('cfg-av-locked-msg').hidden = true;
    avEl.value = data.values.join('\n');

    // Hide "voir tout" since we just set a fresh list
    document.getElementById('cfg-av-count-msg').hidden = true;
    document.getElementById('cfg-av-voir-tout').hidden = true;

    // Update local state
    if (!state.columnConfig[state.activeColumn]) state.columnConfig[state.activeColumn] = {};
    state.columnConfig[state.activeColumn].allowed_values = data.values;
    state.columnConfig[state.activeColumn].allowed_values_locked = false;

    _showToast(`✓ ${data.count} valeurs importées depuis « ${data.name} »`, 'success');
    _schedulePreviewRule();
  } catch (err) {
    _showToast('✗ Erreur lors de l\'import : ' + err.message, 'error');
  }
});

// ---------------------------------------------------------------------------
// Import de modèle — étape Upload (avant création du job)
// ---------------------------------------------------------------------------

/** Fichier de modèle personnalisé sélectionné à l'étape Upload (null si aucun). */
let _pendingTemplateFile = null;

/** Ouvre le sélecteur de fichier modèle à l'étape Upload. */
function triggerUploadTemplateInput() {
  document.getElementById('upload-template-input')?.click();
}

// Écoute du changement de fichier pour le modèle à l'étape Upload
document.getElementById('upload-template-input')?.addEventListener('change', function () {
  if (!this.files.length) return;
  _pendingTemplateFile = this.files[0];
  const nameEl = document.getElementById('upload-template-name');
  if (nameEl) {
    nameEl.textContent = '📄 ' + _pendingTemplateFile.name;
    nameEl.hidden = false;
  }
});

/** Applique le modèle en attente sur un job fraîchement créé. */
async function _applyPendingTemplate(jobId) {
  if (!_pendingTemplateFile) return;
  const fd = new FormData();
  fd.append('file', _pendingTemplateFile);
  try {
    await fetch(`/api/jobs/${jobId}/import-template`, { method: 'POST', body: fd });
  } catch (_) { /* non-bloquant — l'import est best-effort au démarrage */ }
}

// ---------------------------------------------------------------------------
// Thème sombre / clair
// ---------------------------------------------------------------------------

function _getThemeCookie() {
  return document.cookie.split('; ')
    .find(row => row.startsWith('theme='))
    ?.split('=')[1] || null;
}

function _setThemeCookie(theme) {
  document.cookie = `theme=${theme}; max-age=${365 * 24 * 3600}; path=/; samesite=strict`;
}

function _applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.dataset.theme || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  _applyTheme(next);
  _setThemeCookie(next);
}

// Applique le thème au chargement (cookie > préférence système)
(function _initTheme() {
  const saved = _getThemeCookie();
  if (saved) {
    _applyTheme(saved);
  } else if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    _applyTheme('dark');
  }
})();

// ---------------------------------------------------------------------------
// Raccourcis clavier undo/redo (Ctrl+Z / Ctrl+Shift+Z ou Cmd+Z / Cmd+Shift+Z)
// Actifs uniquement à l'étape Correctifs, hors champs de saisie.
// ---------------------------------------------------------------------------
document.addEventListener('keydown', (e) => {
  if (state.currentStep !== 'fixes') return;
  const tag = document.activeElement?.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  const mod = e.ctrlKey || e.metaKey;
  if (!mod) return;

  if (e.key === 'z' && !e.shiftKey) {
    e.preventDefault();
    undoFix();
  } else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') {
    e.preventDefault();
    redoFix();
  }
});
