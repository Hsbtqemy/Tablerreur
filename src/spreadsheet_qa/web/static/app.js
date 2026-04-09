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
  showSpecialChars: false, // toggle for visible special-char rendering
  // Configure step
  columnConfig: {},     // { colName: { content_type, unique, ... } } — fusion modèle + serveur (GET)
  /** Par colonne : l’utilisateur a enregistré des surcharges (job.column_config non vide) — aligné sur GET user_overrides. */
  columnUserSaved: {},
  /** Par colonne : le type / format a déjà été enregistré manuellement côté serveur. */
  columnUserFormatSaved: {},
  /** Cache de suggestion de format par colonne. */
  columnFormatSuggestions: {},
  /** Par colonne : suggestion masquée localement jusqu’à nouvelle analyse ou mutation des données. */
  columnFormatSuggestionDismissed: {},
  activeColumn: null,   // name of the currently open config panel
  /** True après au moins une sauvegarde serveur des réglages colonne (PUT column-config). Utilisé pour FLUX-03 (changement de modèle). */
  userColumnConfigSaved: false,
  /** True après POST /api/jobs réussi et avant « Continuer vers la configuration » — aperçu 10 lignes sur l’étape Téléverser. */
  uploadPreviewReady: false,
  loadedVocabs: {},       // cache { vocabName: [...values] } to restore selector on panel reopen
  loadedVocabLabels: {},  // cache { vocabName: {uri: labelFR} } for datatypes display
  ruleFailures: [],       // échecs d'exécution de règles (moteur)
  exportWarnings: [],     // avertissements_export (fichiers téléchargeables)
  /** Lignes d’aperçu Configurer (GET /preview) pour l’exemple vertical */
  previewDataRows: null,
  /** Index 0-based de la ligne affichée pour les valeurs d’exemple dans la liste des colonnes */
  sampleRowIndex: 0,
  /** Afficher nom + valeur par colonne dans la liste (préférence UX) */
  showSampleValues: false,
  formatSuggestionSeq: 0,
};
let _currentProblemsTotal = 0;

/** Clés legacy (sessionStorage) — migrées vers ACTIVE_JOB_KEY */
const SESSION_JOB_ID_KEY = 'tablerreur.job_id';
const SESSION_COLUMNS_KEY = 'tablerreur.columns';
/** Persistance du job courant : localStorage (fiable en WebView Tauri ; sessionStorage peut être vide ou bloqué). */
const ACTIVE_JOB_KEY = 'tablerreur.active_job.v1';

function _persistJobSession() {
  if (!state.jobId) return;
  const payload = JSON.stringify({
    jobId: state.jobId,
    columns: state.columns || [],
    filename: state.filename || null,
  });
  try {
    localStorage.setItem(ACTIVE_JOB_KEY, payload);
  } catch (_) { /* quota / mode privé */ }
  try {
    sessionStorage.setItem(SESSION_JOB_ID_KEY, state.jobId);
    sessionStorage.setItem(SESSION_COLUMNS_KEY, JSON.stringify(state.columns || []));
  } catch (_) { /* secondaire */ }
}

/** Réinjecte jobId / colonnes après rechargement de page (mémoire JS vide, session serveur encore valide). */
function _restoreJobSession() {
  if (state.jobId) return;
  try {
    const blob = localStorage.getItem(ACTIVE_JOB_KEY);
    if (blob) {
      let data = null;
      try {
        data = JSON.parse(blob);
      } catch {
        localStorage.removeItem(ACTIVE_JOB_KEY);
      }
      if (data) {
        const jid = data.jobId != null ? String(data.jobId).trim() : '';
        if (jid.length > 0) {
          state.jobId = jid;
          state.columns = Array.isArray(data.columns) ? data.columns.map((c) => String(c)) : [];
          if (typeof data.filename === 'string' && data.filename.length > 0) {
            state.filename = data.filename;
          }
          return;
        }
      }
    }
  } catch (_) { /* ignore */ }
  try {
    const jid = sessionStorage.getItem(SESSION_JOB_ID_KEY);
    if (!jid) return;
    state.jobId = String(jid).trim();
    if (!state.jobId) return;
    const raw = sessionStorage.getItem(SESSION_COLUMNS_KEY);
    if (raw) {
      try {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) state.columns = arr.map((c) => String(c));
      } catch (_) {
        /* Colonnes legacy corrompues — ne pas invalider tout le job ni effacer localStorage. */
      }
    }
    _persistJobSession();
  } catch (_) {
    state.jobId = null;
    _clearJobSessionStorage();
  }
}

function _clearJobSessionStorage() {
  try {
    localStorage.removeItem(ACTIVE_JOB_KEY);
  } catch (_) { /* ignore */ }
  try {
    sessionStorage.removeItem(SESSION_JOB_ID_KEY);
    sessionStorage.removeItem(SESSION_COLUMNS_KEY);
  } catch (_) { /* ignore */ }
}

/** Conteneur liste colonnes (id unique dans la page). */
function _getColumnNavEl() {
  return document.getElementById('column-nav-list');
}

function _setColumnNavNoSessionMessage() {
  const el = _getColumnNavEl();
  if (!el) return;
  el.removeAttribute('aria-busy');
  el.innerHTML = `
    <div class="column-nav-no-session">
      <p class="format-hint msg-warning" role="status">
        Aucun fichier actif : rien n’a été téléversé sur le serveur pour cette page, ou la session a expiré (délai, rechargement, redémarrage).
      </p>
      <p class="column-nav-no-session-actions mt-2">
        <button type="button" class="btn btn-primary btn-sm" onclick="goToStep('upload')">Aller à l’étape Téléverser</button>
      </p>
    </div>`;
}

const UX_PREFS_KEY = 'tablerreur.web.ux_prefs.v1';
const UX_PREFS_DEFAULTS = {
  header_row: 1,
  delimiter: '',
  encoding: '',
  template_key: 'manual::',
  show_special_chars: false,
  show_sample_values: false,
  hide_column_config_onboarding: false,
};

let _uxPrefs = _loadUxPrefs();

function _loadUxPrefs() {
  try {
    const raw = localStorage.getItem(UX_PREFS_KEY);
    if (!raw) return { ...UX_PREFS_DEFAULTS };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return { ...UX_PREFS_DEFAULTS };
    const merged = { ...UX_PREFS_DEFAULTS, ...parsed };
    if (merged.template_key == null || String(merged.template_key).trim() === '') {
      merged.template_key = UX_PREFS_DEFAULTS.template_key;
    }
    return merged;
  } catch (_) {
    return { ...UX_PREFS_DEFAULTS };
  }
}

function _saveUxPrefs() {
  try {
    localStorage.setItem(UX_PREFS_KEY, JSON.stringify(_uxPrefs));
  } catch (_) {
    // Non bloquant: localStorage peut être indisponible selon l'environnement.
  }
}

function _setUxPref(key, value) {
  _uxPrefs[key] = value;
  _saveUxPrefs();
}

function _markUserColumnConfigSaved() {
  state.userColumnConfigSaved = true;
}

function _templateOptionKey(optionEl) {
  if (!optionEl) return 'manual::';
  const v =
    optionEl.value != null && String(optionEl.value).trim() !== ''
      ? String(optionEl.value).trim()
      : 'manual';
  return `${v}::${optionEl.dataset.overlay || ''}`;
}

function _findTemplateOptionByKey(selectEl, key) {
  if (!selectEl) return null;
  return Array.from(selectEl.options).find(opt => _templateOptionKey(opt) === key) || null;
}

function _syncSpecialCharsButtons() {
  document.querySelectorAll('.btn-toggle-special-chars').forEach(btn => {
    btn.classList.toggle('btn-special-chars-active', state.showSpecialChars);
  });
}

function _initUxPrefs() {
  const headerRowEl = document.getElementById('header-row');
  const delimiterEl = document.getElementById('delimiter');
  const encodingEl = document.getElementById('encoding');
  const templateEl = document.getElementById('template-id');

  if (headerRowEl) {
    const row = parseInt(_uxPrefs.header_row, 10);
    if (!Number.isNaN(row) && row >= 1) {
      headerRowEl.value = String(row);
    }
    headerRowEl.addEventListener('change', () => {
      const val = parseInt(headerRowEl.value, 10);
      _setUxPref('header_row', Number.isNaN(val) ? 1 : Math.max(1, val));
    });
  }

  if (delimiterEl) {
    delimiterEl.value = _uxPrefs.delimiter || '';
    delimiterEl.addEventListener('change', () => _setUxPref('delimiter', delimiterEl.value || ''));
  }

  if (encodingEl) {
    encodingEl.value = _uxPrefs.encoding || '';
    encodingEl.addEventListener('change', () => _setUxPref('encoding', encodingEl.value || ''));
  }

  if (templateEl) {
    const manualOpt = _findTemplateOptionByKey(templateEl, 'manual::');
    const savedOpt = _findTemplateOptionByKey(templateEl, _uxPrefs.template_key);
    if (savedOpt) {
      savedOpt.selected = true;
    } else if (manualOpt) {
      manualOpt.selected = true;
      _setUxPref('template_key', 'manual::');
    } else if (templateEl.options.length) {
      templateEl.options[0].selected = true;
      _setUxPref('template_key', _templateOptionKey(templateEl.selectedOptions[0]));
    }
    /** Clé du modèle avant interaction (liste déroulante) — pour annuler ou comparer au `change`. */
    let templateKeyBeforeChange = _templateOptionKey(templateEl.selectedOptions[0]);
    const captureTemplateKey = () => {
      if (templateEl.selectedOptions[0]) {
        templateKeyBeforeChange = _templateOptionKey(templateEl.selectedOptions[0]);
      }
    };
    templateEl.addEventListener('focus', captureTemplateKey);
    templateEl.addEventListener('pointerdown', captureTemplateKey);

    templateEl.addEventListener('change', () => {
      const selectedOpt = templateEl.selectedOptions[0];
      const newKey = _templateOptionKey(selectedOpt);
      const prevKey = templateKeyBeforeChange;
      const hadSavedConfig = state.userColumnConfigSaved;

      const runTemplateChange = async () => {
        _setUxPref('template_key', newKey);
        templateKeyBeforeChange = newKey;
        if (!state.jobId) return;
        try {
          await syncJobTemplateFromUI();
          closeColumnConfig();
          await loadPreview();
          if (hadSavedConfig) {
            _showToast(
              'Modèle de validation appliqué. Vos réglages enregistrés par colonne restent prioritaires là où vous les avez définis.',
              'info',
              6500
            );
          }
        } catch (err) {
          _showToast(err?.message || 'Impossible de mettre à jour le modèle.', 'error', 6000);
          const revert = _findTemplateOptionByKey(templateEl, prevKey);
          if (revert) revert.selected = true;
          templateKeyBeforeChange = _templateOptionKey(templateEl.selectedOptions[0]);
        }
      };

      if (state.jobId && state.userColumnConfigSaved && prevKey !== newKey) {
        const explain =
          'Vous avez déjà enregistré des réglages par colonne. En changeant de modèle, le nouveau modèle se combine à votre configuration : vos réglages explicites par colonne sont conservés, et les règles par défaut du nouveau modèle s’appliquent pour le reste.\n\nSouhaitez-vous continuer ?';
        if (!window.confirm(explain)) {
          const revert = _findTemplateOptionByKey(templateEl, prevKey);
          if (revert) revert.selected = true;
          return;
        }
      }

      void runTemplateChange();
    });
  }

  state.showSpecialChars = !!_uxPrefs.show_special_chars;
  _syncSpecialCharsButtons();

  state.showSampleValues = _uxPrefs.show_sample_values === true;
  const showSampleEl = document.getElementById('show-sample-values');
  if (showSampleEl) {
    showSampleEl.checked = state.showSampleValues;
    showSampleEl.addEventListener('change', () => {
      state.showSampleValues = showSampleEl.checked;
      _setUxPref('show_sample_values', state.showSampleValues);
      _updateSampleLinePickerVisibility();
      _buildColumnNavList(state.columns);
    });
  }
  _updateSampleLinePickerVisibility();

  _syncColConfigOnboardingVisibility();
}

/** Compte les « blocs » de réglages actifs pour l’indicateur liste colonnes (aligné sur _isColumnConfigured). */
function _countColumnSettings(cfg) {
  if (!cfg) return 0;
  let n = 0;
  if (cfg.required) n++;
  if (cfg.content_type) n++;
  if (cfg.unique) n++;
  if (cfg.multiline_ok) n++;
  if (cfg.format_preset || cfg.regex) n++;
  if (cfg.min_length != null || cfg.max_length != null) n++;
  if (cfg.forbidden_chars) n++;
  if (cfg.expected_case) n++;
  if (Array.isArray(cfg.allowed_values) && cfg.allowed_values.length) n++;
  if (cfg.nakala_vocabulary) n++;
  if (cfg.list_separator) n++;
  if (cfg.detect_rare_values) n++;
  if (cfg.detect_similar_values) n++;
  return n;
}

const CONTENT_TYPE_LABELS = {
  text: 'Texte libre',
  number: 'Nombre',
  integer: 'Nombre entier',
  decimal: 'Nombre décimal',
  date: 'Date',
  boolean: 'Booléen',
  identifier: 'Identifiant',
  language: 'Code langue',
  country: 'Code pays',
  address: 'Adresse ou lien',
  email: 'Adresse e-mail',
  url: 'URL',
};

const FORMAT_PRESET_LABELS = {
  year: 'Année (YYYY)',
  yes_no: 'Oui / Non',
  alphanum: 'Alphanumérique',
  letters_only: 'Lettres uniquement',
  integer: 'Nombre entier',
  decimal: 'Nombre décimal',
  positive_int: 'Nombre entier positif',
  doi: 'DOI',
  orcid: 'ORCID',
  ark: 'ARK',
  issn: 'ISSN',
  isbn13: 'ISBN-13',
  isbn10: 'ISBN-10',
  email_preset: 'Adresse e-mail',
  url: 'URL (http, https ou www)',
  w3cdtf: 'Date W3C-DTF',
  iso_date: 'Date ISO stricte',
  date_fr: 'Date française (JJ/MM/AAAA)',
  lang_iso639: 'Langue ISO 639',
  bcp47: 'Langue BCP 47',
  country_iso: 'Pays ISO 3166',
  latitude: 'Latitude',
  longitude: 'Longitude',
  custom: 'Regex personnalisée',
};

/** Libellés courts des préréglages de format (liste colonnes). */
const _FORMAT_PRESET_SHORT = {
  year: 'Année',
  yes_no: 'Oui/Non',
  alphanum: 'Alphanum.',
  letters_only: 'Lettres',
  integer: 'Entier',
  decimal: 'Décimal',
  positive_int: 'Entier +',
  doi: 'DOI',
  orcid: 'ORCID',
  ark: 'ARK',
  issn: 'ISSN',
  isbn13: 'ISBN-13',
  isbn10: 'ISBN-10',
  email_preset: 'E-mail',
  url: 'URL',
  w3cdtf: 'W3C-DTF',
  iso_date: 'ISO',
  date_fr: 'JJ/MM/AAAA',
  lang_iso639: 'ISO 639',
  bcp47: 'BCP 47',
  country_iso: 'Pays',
  latitude: 'Latitude',
  longitude: 'Longitude',
  custom: 'Regex',
};

const CONTENT_TYPE_FORMAT_COMPAT = {
  text: ['alphanum', 'letters_only', 'custom'],
  number: ['integer', 'decimal', 'year', 'positive_int', 'latitude', 'longitude', 'custom'],
  integer: ['integer', 'year', 'positive_int', 'custom'],
  decimal: ['decimal', 'latitude', 'longitude', 'custom'],
  date: ['year', 'w3cdtf', 'iso_date', 'date_fr', 'custom'],
  boolean: ['yes_no', 'custom'],
  identifier: ['doi', 'orcid', 'ark', 'issn', 'isbn13', 'isbn10', 'custom'],
  language: ['lang_iso639', 'bcp47', 'custom'],
  country: ['country_iso', 'custom'],
  address: ['email_preset', 'url', 'custom'],
  email: ['email_preset', 'custom'],
  url: ['url', 'custom'],
};

const CONTENT_TYPE_FORMAT_HINTS = {
  text: 'Formats compatibles : alphanumérique, lettres uniquement ou regex personnalisée.',
  number: 'Formats compatibles : entier, décimal, année, entier positif, latitude, longitude ou regex personnalisée.',
  integer: 'Formats compatibles : entier, année, entier positif ou regex personnalisée.',
  decimal: 'Formats compatibles : décimal, latitude, longitude ou regex personnalisée.',
  date: 'Formats compatibles : année, W3C-DTF, ISO stricte, date française ou regex personnalisée.',
  boolean: 'Formats compatibles : Oui / Non ou regex personnalisée.',
  identifier: 'Formats compatibles : DOI, ORCID, ARK, ISSN, ISBN-10, ISBN-13 ou regex personnalisée.',
  language: 'Formats compatibles : ISO 639, BCP 47 ou regex personnalisée.',
  country: 'Formats compatibles : ISO 3166 ou regex personnalisée.',
  address: 'Formats compatibles : adresse e-mail, URL ou regex personnalisée.',
  email: 'Formats compatibles : adresse e-mail ou regex personnalisée.',
  url: 'Formats compatibles : URL ou regex personnalisée.',
};

function _normalizeTypeAndPreset(cfg) {
  const contentType = cfg?.content_type || '';
  let preset = cfg?.format_preset || '';
  if (!preset && cfg?.regex) preset = 'custom';

  switch (contentType) {
    case 'integer':
      return { contentType: 'number', preset: preset || 'integer' };
    case 'decimal':
      return { contentType: 'number', preset: preset || 'decimal' };
    case 'email':
      return { contentType: 'address', preset: preset || 'email_preset' };
    case 'url':
      return { contentType: 'address', preset: preset || 'url' };
    default:
      return { contentType, preset };
  }
}

function _captureFormatPresetOptions() {
  const select = document.getElementById('cfg-format-preset');
  if (!select) return { placeholder: null, groups: [] };
  const children = Array.from(select.children);
  const placeholderEl = children.find((el) => el.tagName === 'OPTION');
  const placeholder = placeholderEl
    ? { value: placeholderEl.value, label: placeholderEl.textContent || '' }
    : null;
  const groups = children
    .filter((el) => el.tagName === 'OPTGROUP')
    .map((groupEl) => ({
      label: groupEl.label,
      options: Array.from(groupEl.querySelectorAll('option')).map((opt) => ({
        value: opt.value,
        label: opt.textContent || '',
      })),
    }));
  return { placeholder, groups };
}

const _FORMAT_PRESET_OPTION_SOURCE = _captureFormatPresetOptions();

function _rebuildFormatPresetOptions(contentType, preferredValue = '') {
  const select = document.getElementById('cfg-format-preset');
  if (!select) return '';

  const allowedValues = CONTENT_TYPE_FORMAT_COMPAT[contentType] || null;
  const allowed = allowedValues ? new Set(allowedValues) : null;
  select.innerHTML = '';

  if (_FORMAT_PRESET_OPTION_SOURCE.placeholder) {
    const opt = document.createElement('option');
    opt.value = _FORMAT_PRESET_OPTION_SOURCE.placeholder.value;
    opt.textContent = _FORMAT_PRESET_OPTION_SOURCE.placeholder.label;
    select.appendChild(opt);
  }

  _FORMAT_PRESET_OPTION_SOURCE.groups.forEach((group) => {
    const options = group.options.filter((opt) => !allowed || allowed.has(opt.value));
    if (!options.length) return;
    const optgroup = document.createElement('optgroup');
    optgroup.label = group.label;
    options.forEach((item) => {
      const opt = document.createElement('option');
      opt.value = item.value;
      opt.textContent = item.label;
      optgroup.appendChild(opt);
    });
    select.appendChild(optgroup);
  });

  const effectiveValue = preferredValue && (!allowed || allowed.has(preferredValue))
    ? preferredValue
    : '';
  select.value = effectiveValue;
  return effectiveValue;
}

function _syncFormatPresetOptions(preferredValue = null) {
  const contentType = document.getElementById('cfg-content-type')?.value || '';
  const select = document.getElementById('cfg-format-preset');
  const fallbackValue = select?.value || '';
  const effectiveValue = _rebuildFormatPresetOptions(
    contentType,
    preferredValue == null ? fallbackValue : preferredValue,
  );
  _updateFormatPresetUI(effectiveValue, contentType);
  return effectiveValue;
}

function _hideFormatSuggestion() {
  const card = document.getElementById('col-format-suggestion');
  const actionsEl = document.getElementById('col-format-suggestion-actions');
  const applyBtn = document.getElementById('btn-apply-format-suggestion');
  const dismissBtn = document.getElementById('btn-dismiss-format-suggestion');
  const refreshBtn = document.getElementById('btn-refresh-format-suggestion');
  const messageEl = document.getElementById('col-format-suggestion-message');
  const metaEl = document.getElementById('col-format-suggestion-meta');
  const noteEl = document.getElementById('col-format-suggestion-note');
  const candidatesEl = document.getElementById('col-format-suggestion-candidates');
  if (!card || !messageEl || !metaEl || !noteEl || !candidatesEl) return;
  card.hidden = true;
  card.className = 'col-format-suggestion';
  messageEl.textContent = '';
  metaEl.hidden = true;
  metaEl.textContent = '';
  noteEl.hidden = true;
  noteEl.textContent = '';
  candidatesEl.hidden = true;
  candidatesEl.innerHTML = '';
  if (actionsEl) actionsEl.hidden = true;
  if (applyBtn) applyBtn.hidden = true;
  if (dismissBtn) dismissBtn.hidden = true;
  if (refreshBtn) {
    refreshBtn.hidden = true;
    refreshBtn.textContent = 'Ré-analyser';
  }
}

function _setFormatSuggestionCard({
  tone = 'info',
  message = '',
  meta = '',
  note = '',
  showApplyButton = false,
  showDismissButton = false,
  showRefreshButton = false,
  refreshLabel = 'Ré-analyser',
} = {}) {
  const card = document.getElementById('col-format-suggestion');
  const actionsEl = document.getElementById('col-format-suggestion-actions');
  const applyBtn = document.getElementById('btn-apply-format-suggestion');
  const dismissBtn = document.getElementById('btn-dismiss-format-suggestion');
  const refreshBtn = document.getElementById('btn-refresh-format-suggestion');
  const messageEl = document.getElementById('col-format-suggestion-message');
  const metaEl = document.getElementById('col-format-suggestion-meta');
  const noteEl = document.getElementById('col-format-suggestion-note');
  if (!card || !messageEl || !metaEl || !noteEl) return;

  card.className = 'col-format-suggestion';
  if (tone && tone !== 'info') card.classList.add(`is-${tone}`);
  messageEl.textContent = message;
  metaEl.textContent = meta || '';
  metaEl.hidden = !meta;
  noteEl.textContent = note || '';
  noteEl.hidden = !note;
  if (actionsEl) {
    actionsEl.hidden = !(showApplyButton || showDismissButton || showRefreshButton);
  }
  if (applyBtn) applyBtn.hidden = !showApplyButton;
  if (dismissBtn) dismissBtn.hidden = !showDismissButton;
  if (refreshBtn) {
    refreshBtn.hidden = !showRefreshButton;
    refreshBtn.textContent = refreshLabel;
  }
  card.hidden = false;
}

function _formatSuggestionLabel(data) {
  if (!data) return '';
  const typeLabel = CONTENT_TYPE_LABELS[data.content_type] || data.content_type || '';
  const presetLabel = data.format_preset
    ? (FORMAT_PRESET_LABELS[data.format_preset] || data.format_preset)
  : '';
  return presetLabel ? `${typeLabel} → ${presetLabel}` : typeLabel;
}

function _getFormatSuggestionCandidates(data) {
  if (Array.isArray(data?.candidates) && data.candidates.length) return data.candidates;
  if (data?.content_type) {
    return [{
      content_type: data.content_type,
      format_preset: data.format_preset || null,
      confidence: data.confidence || 0,
      matched: data.matched || 0,
      total: data.total || 0,
      examples: data.examples || [],
    }];
  }
  return [];
}

function _formatSuggestionConfidence(candidate) {
  const confidence = Number(candidate?.confidence || 0);
  return `${Math.round(confidence * 100)} %`;
}

function _currentPanelMatchesSuggestion(colName, data) {
  if (!colName || !data || state.activeColumn !== colName) return false;
  try {
    const cfg = _readPanelValues();
    return (cfg.content_type || '') === (data.content_type || '')
      && (cfg.format_preset || '') === (data.format_preset || '');
  } catch (_) {
    return false;
  }
}

function _renderFormatSuggestionCandidates(
  colName,
  data,
  { manualFormatSaved = false, skipPrimary = false } = {}
) {
  const candidatesEl = document.getElementById('col-format-suggestion-candidates');
  if (!candidatesEl) return;

  const allCandidates = _getFormatSuggestionCandidates(data);
  const startIndex = skipPrimary ? 1 : 0;
  const entries = allCandidates
    .slice(startIndex)
    .map((candidate, offset) => ({
      candidate,
      index: startIndex + offset,
      matchesCurrent: _currentPanelMatchesSuggestion(colName, candidate),
    }));

  candidatesEl.innerHTML = '';
  if (!entries.length) {
    candidatesEl.hidden = true;
    return;
  }

  const title = document.createElement('p');
  title.className = 'col-format-suggestion-candidates-title';
  title.textContent = data.detected ? 'Autres pistes proches' : 'Pistes proposées';
  candidatesEl.appendChild(title);

  const list = document.createElement('div');
  list.className = 'col-format-suggestion-candidate-list';

  entries.forEach(({ candidate, index, matchesCurrent }) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-secondary btn-sm col-format-suggestion-candidate';
    if (matchesCurrent) btn.classList.add('is-current');
    btn.disabled = manualFormatSaved || matchesCurrent;
    btn.title = [
      _formatSuggestionLabel(candidate),
      `Compatibilité : ${candidate.matched}/${candidate.total}`,
      `Confiance : ${_formatSuggestionConfidence(candidate)}`,
      candidate.examples?.length ? `Exemples : ${candidate.examples.join(', ')}` : '',
    ].filter(Boolean).join('\n');
    btn.addEventListener('click', () => applyFormatSuggestion(index));

    const label = document.createElement('span');
    label.className = 'col-format-suggestion-candidate-label';
    label.textContent = _formatSuggestionLabel(candidate);
    btn.appendChild(label);

    const score = document.createElement('span');
    score.className = 'col-format-suggestion-candidate-score';
    score.textContent = ` · ${candidate.matched}/${candidate.total} · ${_formatSuggestionConfidence(candidate)}`;
    btn.appendChild(score);

    list.appendChild(btn);
  });

  candidatesEl.appendChild(list);
  candidatesEl.hidden = false;
}

function _hideFormatSuggestionCandidates() {
  const candidatesEl = document.getElementById('col-format-suggestion-candidates');
  if (!candidatesEl) return;
  candidatesEl.hidden = true;
  candidatesEl.innerHTML = '';
}

function _renderFormatSuggestion(colName) {
  if (!colName || state.activeColumn !== colName) return;
  const cached = state.columnFormatSuggestions[colName];
  if (!cached) {
    _hideFormatSuggestion();
    return;
  }

  if (cached.status === 'loading') {
    _setFormatSuggestionCard({
      tone: 'loading',
      message: 'Analyse automatique en cours pour cette colonne…',
    });
    _hideFormatSuggestionCandidates();
    return;
  }

  if (cached.status === 'error') {
    _setFormatSuggestionCard({
      tone: 'warning',
      message: 'Suggestion automatique indisponible pour cette colonne.',
      note: cached.error || '',
      showRefreshButton: true,
    });
    _hideFormatSuggestionCandidates();
    return;
  }

  const data = cached.data;
  if (!data) {
    _hideFormatSuggestion();
    return;
  }

  const candidates = _getFormatSuggestionCandidates(data);
  const primaryCandidate = candidates[0] || null;
  const manualFormatSaved = !!state.columnUserFormatSaved?.[colName];
  const dismissed = !!state.columnFormatSuggestionDismissed?.[colName];

  if (dismissed) {
    const metaParts = [];
    if (primaryCandidate) {
      metaParts.push(`Dernière piste : ${_formatSuggestionLabel(primaryCandidate)}`);
      metaParts.push(`Compatibilité : ${primaryCandidate.matched}/${primaryCandidate.total}`);
      metaParts.push(`Confiance : ${_formatSuggestionConfidence(primaryCandidate)}`);
    }
    _setFormatSuggestionCard({
      tone: 'muted',
      message: 'Suggestion automatique ignorée pour cette colonne.',
      meta: metaParts.join(' · '),
      note: 'Utilisez « Ré-analyser » pour recalculer la suggestion à partir des valeurs courantes.',
      showRefreshButton: true,
    });
    _hideFormatSuggestionCandidates();
    return;
  }

  if (!data.detected) {
    const metaParts = [];
    if (primaryCandidate) {
      metaParts.push(`Piste la plus proche : ${_formatSuggestionLabel(primaryCandidate)}`);
      metaParts.push(`Compatibilité : ${primaryCandidate.matched}/${primaryCandidate.total}`);
    } else if (data.examples?.length) {
      metaParts.push(`Exemples lus : ${data.examples.join(', ')}`);
    }
    _setFormatSuggestionCard({
      tone: 'muted',
      message: data.message || 'Aucune suggestion fiable.',
      meta: metaParts.join(' · '),
      note: candidates.length
        ? (
          manualFormatSaved
            ? 'Plusieurs pistes sont visibles ci-dessous, mais votre choix manuel actuel reste prioritaire.'
            : 'Choisissez une piste ci-dessous pour la recopier dans le formulaire.'
        )
        : '',
      showDismissButton: !!(candidates.length || data.message),
      showRefreshButton: true,
    });
    _renderFormatSuggestionCandidates(colName, data, { manualFormatSaved, skipPrimary: false });
    return;
  }

  const alreadyInForm = _currentPanelMatchesSuggestion(colName, primaryCandidate || data);
  const note = manualFormatSaved
    ? 'Une nature ou un format a déjà été enregistré manuellement pour cette colonne. La suggestion reste informative.'
    : alreadyInForm
      ? 'Le formulaire correspond déjà à cette suggestion. Utilisez « Appliquer » en bas du panneau pour l’enregistrer si besoin.'
      : candidates.length > 1
        ? 'D’autres pistes proches sont proposées ci-dessous.'
        : '';

  const metaParts = [`Compatibilité : ${data.matched}/${data.total}`];
  metaParts.push(`Confiance : ${_formatSuggestionConfidence(primaryCandidate || data)}`);
  if (data.examples?.length) metaParts.push(`Exemples : ${data.examples.join(', ')}`);
  _setFormatSuggestionCard({
    message: `Suggestion automatique : ${_formatSuggestionLabel(primaryCandidate || data)}`,
    meta: metaParts.join(' · '),
    note,
    showApplyButton: !manualFormatSaved && !alreadyInForm,
    showDismissButton: true,
    showRefreshButton: true,
  });
  _renderFormatSuggestionCandidates(colName, data, { manualFormatSaved, skipPrimary: true });
}

function _refreshFormatSuggestionUI() {
  if (!state.activeColumn) {
    _hideFormatSuggestion();
    return;
  }
  _renderFormatSuggestion(state.activeColumn);
}

function _invalidateFormatSuggestionCache(colName = null) {
  state.formatSuggestionSeq += 1;
  if (!colName) {
    state.columnFormatSuggestions = {};
    state.columnFormatSuggestionDismissed = {};
    return;
  }
  delete state.columnFormatSuggestions[colName];
  delete state.columnFormatSuggestionDismissed[colName];
}

function dismissFormatSuggestion() {
  const colName = state.activeColumn;
  if (!colName) return;
  state.columnFormatSuggestionDismissed[colName] = true;
  _renderFormatSuggestion(colName);
}

function reanalyzeFormatSuggestion() {
  const colName = state.activeColumn;
  if (!colName) return;
  delete state.columnFormatSuggestionDismissed[colName];
  _invalidateFormatSuggestionCache(colName);
  void _loadFormatSuggestion(colName, true);
}

function _updatePreviewDataCell(rowIndex, colName, newValue, { markEdited = false } = {}) {
  if (!colName || !Number.isInteger(rowIndex) || rowIndex < 0) return;

  const colIdx = state.columns.indexOf(colName);
  if (colIdx >= 0 && Array.isArray(state.previewDataRows) && rowIndex < state.previewDataRows.length) {
    const row = state.previewDataRows[rowIndex];
    if (Array.isArray(row) && colIdx < row.length) {
      row[colIdx] = newValue;
      if (state.showSampleValues && state.sampleRowIndex === rowIndex) {
        _buildColumnNavList(state.columns);
      }
    }
  }

  const selector = `#preview-body td[data-row="${rowIndex}"][data-col="${CSS.escape(colName)}"]`;
  const td = document.querySelector(selector);
  if (!td) return;
  td.dataset.rawText = newValue;
  if (state.showSpecialChars) {
    td.innerHTML = renderVisibleChars(newValue);
  } else {
    td.textContent = newValue;
  }
  if (markEdited) td.classList.add('cell-edited');
}

function _refreshOpenColumnAfterDataMutation(changedColumn = null) {
  if (!state.activeColumn) return;
  if (changedColumn && state.activeColumn !== changedColumn) return;
  _schedulePreviewRule();
  void _loadFormatSuggestion(state.activeColumn, true);
}

async function _loadFormatSuggestion(colName, force = false) {
  if (!state.jobId || !colName) return;
  const cached = state.columnFormatSuggestions[colName];
  if (!force && cached && (cached.status === 'loading' || cached.status === 'ready')) {
    _renderFormatSuggestion(colName);
    return;
  }

  const seq = ++state.formatSuggestionSeq;
  state.columnFormatSuggestions[colName] = { status: 'loading' };
  _renderFormatSuggestion(colName);

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/detect-format`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ column: colName }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.detail || 'Analyse indisponible');
    }
    state.columnFormatSuggestions[colName] = { status: 'ready', data };
  } catch (err) {
    state.columnFormatSuggestions[colName] = {
      status: 'error',
      error: err?.message || 'Analyse indisponible',
    };
  }

  if (seq !== state.formatSuggestionSeq || state.activeColumn !== colName) return;
  _renderFormatSuggestion(colName);
}

function applyFormatSuggestion(candidateIndex = 0) {
  const colName = state.activeColumn;
  if (!colName) return;
  if (state.columnUserFormatSaved?.[colName]) return;
  const data = state.columnFormatSuggestions[colName]?.data;
  const candidates = _getFormatSuggestionCandidates(data);
  const index = Number(candidateIndex);
  const suggestion = candidates[Number.isNaN(index) ? 0 : index] || null;
  if (!suggestion?.content_type) return;

  const contentType = suggestion.content_type || '';
  document.getElementById('cfg-content-type').value = contentType;
  const preset = _rebuildFormatPresetOptions(contentType, suggestion.format_preset || '');
  document.getElementById('cfg-regex').value = '';
  document.getElementById('cfg-yesno-true').value = '';
  document.getElementById('cfg-yesno-false').value = '';
  _updateFormatPresetUI(preset, contentType);
  _saveCurrentPanelToState();
  _updateConfiguredMarker(colName);
  _schedulePreviewRule();
  _renderFormatSuggestion(colName);
  _showToast(
    `Suggestion « ${_formatSuggestionLabel(suggestion)} » copiée dans le formulaire. Utilisez « Appliquer » en bas du panneau pour l’enregistrer.`,
    'success',
    5000
  );
}

/** Résumé d’une ligne : nature / préréglage / liste pour la liste des colonnes. */
function _columnKindShort(cfg) {
  if (!cfg) return '—';
  const { contentType, preset: fp } = _normalizeTypeAndPreset(cfg);
  if (fp && String(fp).trim() !== '') {
    return _FORMAT_PRESET_SHORT[fp] || fp;
  }
  if (cfg.nakala_vocabulary) return 'NAKALA';
  if (cfg.list_separator) return 'Liste multi';
  if (Array.isArray(cfg.allowed_values) && cfg.allowed_values.length) {
    return cfg.allowed_values_locked ? 'Liste (verrouillée)' : 'Liste';
  }
  if (cfg.regex) return 'Regex';
  const ct = contentType;
  if (ct) {
    return CONTENT_TYPE_LABELS[ct] || ct;
  }
  if (cfg.required) return 'Obligatoire';
  if (cfg.unique) return 'Unique';
  if (cfg.detect_rare_values || cfg.detect_similar_values) return 'Détection';
  return '—';
}

/**
 * Statut court sous le nom de colonne : état (personnalisé / modèle / manuel / en cours) + type effectif.
 * @param {string} colName
 */
function _columnNavStatLabel(colName) {
  const cfg = state.columnConfig[colName] || {};
  const kind = _columnKindShort(cfg);
  const userSaved = !!(state.columnUserSaved && state.columnUserSaved[colName]);
  const panel = document.getElementById('column-config-panel');
  const inProgress = state.activeColumn === colName && panel && !panel.hidden;

  if (inProgress) {
    return `En cours · ${kind}`;
  }
  if (userSaved) {
    return `Personnalisé · ${kind}`;
  }
  let sourceLabel = 'Modèle';
  try {
    const t = _templateSelectionFromUI();
    if (t.template_id === 'manual') sourceLabel = 'Manuel';
  } catch (_) { /* ignore */ }
  return `${sourceLabel} · ${kind}`;
}

function expandAllColConfigSections() {
  document.querySelectorAll('#column-config-panel details.col-config-section').forEach(d => {
    d.open = true;
  });
}

function collapseAllColConfigSections() {
  document.querySelectorAll('#column-config-panel details.col-config-section').forEach(d => {
    d.open = false;
  });
}

/** Affiche ou masque l’encadré d’aide selon la préférence persistée (localStorage). */
function _syncColConfigOnboardingVisibility() {
  const el = document.getElementById('col-config-onboarding');
  if (!el) return;
  el.hidden = !!_uxPrefs.hide_column_config_onboarding;
}

function dismissColConfigOnboarding() {
  _setUxPref('hide_column_config_onboarding', true);
  _syncColConfigOnboardingVisibility();
}

async function _extractErrorDetail(resp, fallback = 'Erreur') {
  let detail = fallback;
  const jsonResp = resp.clone();
  try {
    const data = await jsonResp.json();
    const raw = data?.detail ?? data?.message ?? data?.error;
    if (typeof raw === 'string' && raw.trim()) {
      detail = raw.trim();
    } else if (Array.isArray(raw) && raw.length) {
      detail = raw
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const loc = Array.isArray(item.loc) ? item.loc.join('.') : '';
            const msg = item.msg || '';
            return loc && msg ? `${loc}: ${msg}` : (msg || JSON.stringify(item));
          }
          return '';
        })
        .filter(Boolean)
        .join('; ');
    } else if (raw && typeof raw === 'object') {
      detail = JSON.stringify(raw);
    }
  } catch (_) {
    try {
      const txt = await resp.text();
      if (txt && txt.trim()) detail = txt.trim();
    } catch (_) { /* ignore */ }
  }
  return detail || fallback;
}

function _formatUploadError(status, detail) {
  if (status === 413) {
    return [
      'Le fichier est trop volumineux.',
      'Astuce: réduisez sa taille ou augmentez TABLERREUR_MAX_UPLOAD_MB côté serveur.',
    ].join('\n');
  }
  if (status === 415) {
    return [
      'Format non pris en charge.',
      'Utilisez un fichier CSV, XLSX ou XLS.',
    ].join('\n');
  }
  if (status === 422) {
    if (/header_row=.*beyond the file length/i.test(detail)) {
      return [
        'La ligne d’en-tête choisie n’existe pas dans ce fichier.',
        'Astuce: diminuez “Ligne d’en-tête” dans les options d’import.',
      ].join('\n');
    }
    return [
      'Le fichier n’a pas pu être importé avec ces options.',
      'Vérifiez l’encodage, le délimiteur et la ligne d’en-tête.',
      `Détail: ${detail}`,
    ].join('\n');
  }
  return `Échec du téléversement (${status}).\nDétail: ${detail}`;
}

function _formatActionError(actionName, status, detail) {
  if (status === 404 && /session introuvable|expirée/i.test(detail)) {
    return [
      `${actionName} impossible: la session a expiré.`,
      'Rechargez un fichier pour repartir sur une session valide.',
    ].join('\n');
  }
  if (status === 422) {
    return `${actionName} impossible.\nDétail: ${detail}`;
  }
  return `${actionName} impossible (${status}).\nDétail: ${detail}`;
}

function _setInlineError(el, message) {
  if (!el) return;
  el.innerHTML = esc(message).replace(/\n/g, '<br>');
  el.hidden = false;
}

function _setStepCoach(text, actionLabel = '', actionFn = null) {
  const box = document.getElementById('step-coach');
  const textEl = document.getElementById('step-coach-text');
  const actionBtn = document.getElementById('step-coach-action');
  if (!box || !textEl || !actionBtn) return;

  if (!text) {
    box.hidden = true;
    actionBtn.hidden = true;
    actionBtn.onclick = null;
    return;
  }

  textEl.innerHTML = text;
  /* Toujours masquer d’abord : évite de garder « Choisir un fichier » (étape 1) sur les étapes sans action. */
  actionBtn.hidden = true;
  actionBtn.onclick = null;
  if (actionLabel && typeof actionFn === 'function') {
    actionBtn.textContent = actionLabel;
    actionBtn.hidden = false;
    actionBtn.onclick = (e) => {
      e.preventDefault();
      actionFn();
    };
  }
  box.hidden = false;
}

function _updateStepCoach() {
  const tablerreur = document.getElementById('app-tablerreur');
  if (tablerreur?.hidden) {
    _setStepCoach('');
    return;
  }

  switch (state.currentStep) {
    case 'upload':
      _setStepCoach(
        '<strong>Étape 1/5.</strong> Choisissez un fichier, ajustez les options d’import si besoin, puis cliquez sur <strong>Téléverser et afficher l’aperçu</strong>. Ensuite, continuez vers la configuration.',
        'Choisir un fichier',
        () => fileInput?.click()
      );
      break;
    case 'configure':
      _setStepCoach(
        '<strong>Étape 2/5.</strong> Choisissez le <strong>modèle de validation</strong>, puis une colonne dans la liste pour les contraintes. Ouvrez l’<strong>aperçu tableau</strong> en bas de page pour inspecter les données.'
      );
      break;
    case 'fixes':
      _setStepCoach(
        '<strong>Étape 3/5.</strong> Activez les correctifs utiles puis vérifiez l’impact avec un aperçu.',
        'Calculer l’aperçu',
        () => previewFixes()
      );
      break;
    case 'validate':
      if (state.validationDone) {
        _setStepCoach(
          '<strong>Étape 4/5.</strong> Validation terminée. Consultez maintenant la liste des problèmes.',
          'Voir les résultats',
          () => goToStep('results')
        );
      } else {
        _setStepCoach('<strong>Étape 4/5.</strong> Validation en cours, cela peut prendre quelques secondes.');
      }
      break;
    case 'results':
      if (_currentProblemsTotal > 0) {
        _setStepCoach(
          `<strong>Étape 5/5.</strong> ${_currentProblemsTotal} problème(s) affiché(s). Utilisez “Appliquer” ou “✏️” pour corriger rapidement.`,
          'Filtrer: Erreurs',
          () => {
            const sev = document.getElementById('filter-severity');
            if (sev) sev.value = 'ERROR';
            loadProblems(1);
          }
        );
      } else {
        _setStepCoach('<strong>Étape 5/5.</strong> Aucun problème restant. Vous pouvez exporter le fichier nettoyé.');
      }
      break;
    default:
      _setStepCoach('');
      break;
  }
}

// ---------------------------------------------------------------------------
// Navigation entre étapes
// ---------------------------------------------------------------------------
function goToStep(step) {
  // Hide all sections (scope: Tablerreur only, avoid touching Mapala)
  document.querySelectorAll('#app-tablerreur .step-section').forEach(el => el.hidden = true);
  document.querySelectorAll('#step-nav .step-btn').forEach(el => el.classList.remove('active'));

  // Show target section
  const section = document.getElementById('step-' + step);
  if (section) {
    section.hidden = false;
    // Après un long scroll sur Téléverser, l’étape suivante peut rester hors vue (WebView : smooth parfois sans effet).
    if (step !== 'upload') {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const nav = document.getElementById('step-nav');
          if (nav) nav.scrollIntoView({ behavior: 'auto', block: 'start' });
          section.scrollIntoView({ behavior: 'auto', block: 'start' });
        });
      });
    }
  }

  // Activate nav button (scope: Tablerreur step nav only)
  const btn = document.querySelector(`#step-nav [data-step="${step}"]`);
  if (btn) btn.classList.add('active');

  state.currentStep = step;
  document.body.classList.toggle('tablerreur-step-configure', step === 'configure');

  // Step-specific init
  if (step === 'upload') {
    if (state.jobId && state.uploadPreviewReady) {
      _showUploadPreviewChrome();
      void _renderUploadPreview();
    }
  }
  if (step === 'configure') {
    void loadPreview().catch((err) => console.error('loadPreview', err));
    updateUndoRedoButtons();
  }
  if (step === 'fixes') updateUndoRedoButtons();
  if (step === 'validate') runValidation();
  if (step === 'results') {
    loadProblems(1);
    _renderResultsExportWarnings();
  }
  _updateStepCoach();
}

function enableStep(step) {
  const btn = document.querySelector(`#step-nav [data-step="${step}"]`);
  if (btn) btn.disabled = false;
}

/** Désactive l’étape Configurer si aucun job (ex. session expirée, 404 preview). */
function _syncConfigureStepButton() {
  const btn = document.querySelector('#step-nav [data-step="configure"]');
  if (btn) btn.disabled = !state.jobId;
}

// ---------------------------------------------------------------------------
// Navigation par onglet : Tablerreur ↔ Mapala
// ---------------------------------------------------------------------------
function switchApp(appName) {
  const tablerreur = document.getElementById('app-tablerreur');
  const mapala = document.getElementById('app-mapala');
  const tabT = document.getElementById('tab-tablerreur');
  const tabM = document.getElementById('tab-mapala');
  // Header : id prioritaire, fallback par classe (compat WebView / ancien bundle)
  const header = document.getElementById('app-header') || document.querySelector('.app-header');
  if (!tablerreur || !mapala) return;
  if (appName === 'mapala') {
    tablerreur.hidden = true;
    mapala.hidden = false;
    document.body.classList.remove('tablerreur-step-configure');
    tabT.classList.remove('active');
    tabM.classList.add('active');
    if (header) {
      header.classList.remove('app-header--tablerreur');
      header.classList.add('app-header--mapala');
    }
  } else {
    mapala.hidden = true;
    tablerreur.hidden = false;
    document.body.classList.toggle('tablerreur-step-configure', state.currentStep === 'configure');
    tabT.classList.add('active');
    tabM.classList.remove('active');
    if (header) {
      header.classList.remove('app-header--mapala');
      header.classList.add('app-header--tablerreur');
    }
  }
  _updateStepCoach();
}

// ---------------------------------------------------------------------------
// ÉTAPE 1 — Téléversement
// ---------------------------------------------------------------------------
const fileInput = document.getElementById('file-input');
const uploadZone = document.getElementById('upload-zone');
const btnUploadContinue = document.getElementById('btn-upload-continue');
btnUploadContinue?.addEventListener('click', (e) => {
  e.preventDefault();
  e.stopPropagation();
  void uploadContinueToConfigure();
});
_initUxPrefs();
_restoreJobSession();
_syncConfigureStepButton();
_updateStepCoach();

fileInput?.addEventListener('change', () => {
  if (fileInput.files.length) {
    _resetUploadPreviewStepUI();
    showFileSelected(fileInput.files[0].name);
    void _refreshWorkbookSheetOptions(fileInput.files[0]);
  }
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
    _resetUploadPreviewStepUI();
    showFileSelected(e.dataTransfer.files[0].name);
    void _refreshWorkbookSheetOptions(e.dataTransfer.files[0]);
  }
});

/** Nombre de lignes affichées dans l’aperçu après téléversement (étape Téléverser). */
const UPLOAD_PREVIEW_ROWS = 10;

function _hideUploadSheetSelector() {
  const lab = document.getElementById('upload-sheet-label');
  const sel = document.getElementById('sheet-name');
  if (lab) lab.hidden = true;
  if (sel) {
    sel.hidden = true;
    sel.innerHTML = '';
  }
}

/**
 * Pour un classeur Excel, remplit le sélecteur de feuille (requête avant le POST /api/jobs).
 * Affiché dès qu’au moins une feuille est détectée (y compris une seule).
 * @param {File} file
 */
async function _refreshWorkbookSheetOptions(file) {
  if (!file?.name) {
    _hideUploadSheetSelector();
    return;
  }
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  if (!['.xlsx', '.xls', '.xlsm'].includes(ext)) {
    _hideUploadSheetSelector();
    return;
  }
  const lab = document.getElementById('upload-sheet-label');
  const sel = document.getElementById('sheet-name');
  if (!lab || !sel) return;
  const fd = new FormData();
  fd.append('file', file);
  try {
    const resp = await fetch('/api/inspect-workbook-sheets', { method: 'POST', body: fd });
    if (!resp.ok) {
      _hideUploadSheetSelector();
      return;
    }
    const data = await resp.json();
    const sheets = data.sheets || [];
    sel.innerHTML = '';
    if (sheets.length === 0) {
      _hideUploadSheetSelector();
      return;
    }
    sheets.forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      sel.appendChild(opt);
    });
    lab.hidden = false;
    sel.hidden = false;
  } catch {
    _hideUploadSheetSelector();
  }
}

function _showUploadPreviewChrome() {
  const card = document.getElementById('upload-preview-card');
  const btnS = document.getElementById('btn-upload-submit');
  const btnC = document.getElementById('btn-upload-continue');
  if (card) card.hidden = false;
  if (btnS) {
    btnS.hidden = true;
    btnS.disabled = false;
    btnS.removeAttribute('aria-busy');
  }
  if (btnC) {
    btnC.hidden = false;
  }
}

/** Masque l’aperçu Téléverser et réaffiche le bouton principal (nouveau fichier ou réinitialisation). */
function _resetUploadPreviewStepUI() {
  state.uploadPreviewReady = false;
  const card = document.getElementById('upload-preview-card');
  const table = document.getElementById('upload-preview-table');
  const loading = document.getElementById('upload-preview-loading');
  const meta = document.getElementById('upload-preview-meta');
  const headerRow = document.getElementById('upload-preview-header');
  const tbody = document.getElementById('upload-preview-body');
  const btnS = document.getElementById('btn-upload-submit');
  const btnC = document.getElementById('btn-upload-continue');
  if (card) card.hidden = true;
  if (table) table.hidden = true;
  if (headerRow) headerRow.innerHTML = '';
  if (tbody) tbody.innerHTML = '';
  if (loading) {
    loading.hidden = false;
    loading.textContent = 'Chargement de l\'aperçu…';
    loading.className = 'msg-info upload-preview-loading-msg';
  }
  if (meta) {
    meta.hidden = true;
    meta.textContent = '';
  }
  if (btnS) {
    btnS.hidden = false;
    btnS.disabled = false;
    btnS.removeAttribute('aria-busy');
  }
  if (btnC) btnC.hidden = true;
  _hideUploadSheetSelector();
}

/**
 * Charge et affiche l’aperçu court (GET /preview) sur l’étape Téléverser.
 * @returns {Promise<boolean>} true si le tableau a été affiché avec succès
 */
async function _renderUploadPreview() {
  const loading = document.getElementById('upload-preview-loading');
  const table = document.getElementById('upload-preview-table');
  /** Une ligne d’en-tête : une cellule th par colonne (comme #preview-header à l’étape Configurer). */
  const headerRow = document.getElementById('upload-preview-header');
  const tbody = document.getElementById('upload-preview-body');
  const meta = document.getElementById('upload-preview-meta');
  if (!state.jobId || !loading || !table || !headerRow || !tbody) return false;

  loading.hidden = false;
  loading.className = 'msg-info upload-preview-loading-msg';
  loading.textContent = 'Chargement de l\'aperçu…';
  table.hidden = true;
  if (meta) meta.hidden = true;
  headerRow.innerHTML = '';
  tbody.innerHTML = '';

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/preview?rows=${UPLOAD_PREVIEW_ROWS}`);
    if (!resp.ok) throw new Error('Impossible de charger l\'aperçu');
    const data = await resp.json();
    const cols = data.columns || [];
    const rowData = data.rows || [];
    const total = data.total_rows != null ? data.total_rows : rowData.length;

    if (cols.length === 0) {
      const th0 = document.createElement('th');
      th0.textContent = '—';
      headerRow.appendChild(th0);
      loading.hidden = true;
      table.hidden = false;
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.className = 'upload-preview-empty';
      td.textContent = 'Aucune colonne détectée après import. Vérifiez le fichier et la ligne d’en-tête.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      if (meta) {
        meta.hidden = false;
        meta.textContent = '0 colonne.';
      }
      return true;
    }

    cols.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c;
      headerRow.appendChild(th);
    });

    rowData.forEach(row => {
      const tr = document.createElement('tr');
      for (let i = 0; i < cols.length; i++) {
        const td = document.createElement('td');
        const raw = row[i];
        td.textContent = raw == null || raw === '' ? '' : String(raw);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    });

    loading.hidden = true;
    table.hidden = false;
    if (meta) {
      meta.hidden = false;
      if (total > UPLOAD_PREVIEW_ROWS) {
        meta.textContent = `Aperçu : ${UPLOAD_PREVIEW_ROWS} ligne(s) de données sur ${total} au total.`;
      } else {
        meta.textContent = total === 0
          ? 'Aucune ligne de données.'
          : total === 1
            ? '1 ligne de données dans le fichier.'
            : `${total} lignes de données dans le fichier.`;
      }
    }
    return true;
  } catch (err) {
    loading.hidden = false;
    loading.className = 'msg-error upload-preview-loading-msg';
    loading.textContent = err?.message || 'Erreur lors du chargement de l\'aperçu.';
    return false;
  }
}

/**
 * Passe à l’étape Configurer. Si le fichier n’a pas encore été téléversé (POST /api/jobs),
 * déclenche le téléversement puis la navigation.
 */
async function uploadContinueToConfigure() {
  switchApp('tablerreur');
  if (!state.jobId) {
    _restoreJobSession();
  }
  const hasFile = !!(fileInput && fileInput.files && fileInput.files.length);
  const needUpload = hasFile && !state.uploadPreviewReady;

  if (needUpload) {
    const ok = await doUpload({ skipUploadStepPreview: true });
    if (!ok) return;
  }

  if (state.jobId) {
    _persistJobSession();
  }
  if (!state.jobId) {
    _showToast(
      'Session introuvable. Sélectionnez un fichier, ou utilisez « Téléverser et afficher l’aperçu ».',
      'error'
    );
    return;
  }
  _syncConfigureStepButton();
  goToStep('configure');
}

function showFileSelected(name) {
  document.getElementById('upload-filename').textContent = '📄 ' + name;
  document.getElementById('upload-file-info').hidden = false;
  const inner = document.querySelector('#upload-zone .upload-inner');
  if (inner) inner.hidden = true;
  const btnC = document.getElementById('btn-upload-continue');
  if (btnC) btnC.hidden = false;
}

function clearFile() {
  fileInput.value = '';
  document.getElementById('upload-file-info').hidden = true;
  const inner = document.querySelector('#upload-zone .upload-inner');
  if (inner) inner.hidden = false;
  _resetUploadPreviewStepUI();
}

/** Lit le modèle (#template-id) : même source pour POST /api/jobs et PATCH (changement en cours de route). */
function _templateSelectionFromUI() {
  const sel = document.getElementById('template-id');
  if (!sel) {
    return { template_id: 'manual', overlay_id: null, overlayForm: '' };
  }
  const opt = sel.selectedOptions[0];
  const template_id =
    opt?.value != null && String(opt.value).trim() !== ''
      ? String(opt.value).trim()
      : 'manual';
  const overlayRaw = String(opt?.dataset?.overlay ?? '').trim();
  const isManual = template_id === 'manual';
  return {
    template_id,
    overlay_id: isManual || !overlayRaw ? null : overlayRaw,
    overlayForm: isManual ? '' : overlayRaw,
  };
}

/** Applique sur le job le modèle sélectionné (changement après création — ex. sidecar sans route PATCH obsolète). */
async function syncJobTemplateFromUI() {
  if (!state.jobId) return;
  const sel = document.getElementById('template-id');
  if (!sel) return;
  const { template_id, overlay_id } = _templateSelectionFromUI();
  const resp = await fetch(`/api/jobs/${state.jobId}/template`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_id, overlay_id }),
  });
  if (!resp.ok) {
    const detail = await _extractErrorDetail(resp, 'Mise à jour du modèle');
    if (resp.status === 404) {
      throw new Error(
        'Impossible de changer le modèle : version du serveur trop ancienne. Re-téléversez le fichier avec le modèle souhaité (il est appliqué à l’étape Téléverser), ou mettez à jour l’application.'
      );
    }
    throw new Error(detail);
  }
}

/**
 * @param {{ skipUploadStepPreview?: boolean }} [options] — si vrai, pas d’aperçu tableau sur l’étape Téléverser (ex. enchaînement via « Continuer »).
 * @returns {Promise<boolean>} true si le POST /api/jobs a réussi
 */
async function doUpload(options = {}) {
  const skipUploadStepPreview = !!options.skipUploadStepPreview;
  const errEl = document.getElementById('upload-error');
  const progEl = document.getElementById('upload-progress');
  const btnSubmit = document.getElementById('btn-upload-submit');
  const btnContinue = document.getElementById('btn-upload-continue');
  errEl.hidden = true;
  errEl.textContent = '';

  if (!fileInput.files.length) {
    _setInlineError(errEl, 'Veuillez sélectionner un fichier.');
    return false;
  }

  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.setAttribute('aria-busy', 'true');
  }
  if (btnContinue) {
    btnContinue.disabled = true;
    btnContinue.setAttribute('aria-busy', 'true');
  }

  progEl.hidden = false;
  progEl.textContent = 'Téléversement en cours…';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('header_row', document.getElementById('header-row').value);
  formData.append('delimiter', document.getElementById('delimiter').value);
  formData.append('encoding', document.getElementById('encoding').value);
  // Modèle : lu depuis #template-id (préférences / étape Configurer) — envoyé au POST pour compat. sidecars sans PATCH.
  _setUxPref('header_row', parseInt(document.getElementById('header-row').value, 10) || 1);
  _setUxPref('delimiter', document.getElementById('delimiter').value || '');
  _setUxPref('encoding', document.getElementById('encoding').value || '');
  const tmpl = _templateSelectionFromUI();
  formData.append('template_id', tmpl.template_id);
  formData.append('overlay_id', tmpl.overlayForm);
  const sheetLab = document.getElementById('upload-sheet-label');
  const sheetSel = document.getElementById('sheet-name');
  if (sheetLab && !sheetLab.hidden && sheetSel && !sheetSel.hidden && sheetSel.options.length) {
    formData.append('sheet_name', sheetSel.value);
  }

  try {
    const resp = await fetch('/api/jobs', { method: 'POST', body: formData });
    if (!resp.ok) {
      const detail = await _extractErrorDetail(resp, 'Échec du téléversement');
      throw new Error(_formatUploadError(resp.status, detail));
    }
    const data = await resp.json();
    const jid = data.job_id != null ? String(data.job_id).trim() : '';
    if (!jid) {
      throw new Error('Réponse serveur invalide : identifiant de session manquant.');
    }
    state.jobId = jid;

    state.filename = data.filename;
    state.rows = data.rows;
    state.cols = data.cols;
    state.columns = data.columns || [];
    _persistJobSession();
    state.columnConfig = {};
    state.columnUserSaved = {};
    state.columnUserFormatSaved = {};
    state.columnFormatSuggestions = {};
    state.columnFormatSuggestionDismissed = {};
    state.formatSuggestionSeq = 0;
    state.userColumnConfigSaved = false;
    state.activeColumn = null;
    state.validationDone = false;
    state.ruleFailures = [];
    state.exportWarnings = [];
    _currentProblemsTotal = 0;
    _hideCellsEditedBanner();
    _hideFormatSuggestion();
    const vrf = document.getElementById('validate-rule-failures');
    if (vrf) { vrf.hidden = true; vrf.innerHTML = ''; }
    const rew = document.getElementById('results-export-warnings');
    if (rew) { rew.hidden = true; rew.innerHTML = ''; }

    if (!skipUploadStepPreview) {
      progEl.textContent = `Chargé : ${data.filename} (${data.rows} lignes × ${data.cols} colonnes)`;
    } else {
      progEl.hidden = true;
    }

    // Populate column filter in fixes step
    const fixColSelect = document.getElementById('fix-columns');
    if (fixColSelect) {
      fixColSelect.innerHTML = '<option value="">Toutes les colonnes</option>';
      state.columns.forEach(col => {
        const opt = document.createElement('option');
        opt.value = col;
        opt.textContent = col;
        fixColSelect.appendChild(opt);
      });
    }

    // Populate column filter in results step
    const filterCol = document.getElementById('filter-column');
    if (filterCol) {
      filterCol.innerHTML = '<option value="">Toutes les colonnes</option>';
      state.columns.forEach(col => {
        const opt = document.createElement('option');
        opt.value = col;
        opt.textContent = col;
        filterCol.appendChild(opt);
      });
    }

    state.uploadPreviewReady = true;
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.removeAttribute('aria-busy');
    }
    if (btnContinue) {
      btnContinue.disabled = false;
      btnContinue.removeAttribute('aria-busy');
    }
    _syncConfigureStepButton();
    if (!skipUploadStepPreview) {
      _showUploadPreviewChrome();
      await _renderUploadPreview();
      document.getElementById('upload-action-row')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      document.getElementById('btn-upload-continue')?.focus();
    } else {
      _showUploadPreviewChrome();
    }
    return true;
  } catch (err) {
    progEl.hidden = true;
    _setInlineError(errEl, err?.message || 'Erreur lors du téléversement.');
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.removeAttribute('aria-busy');
    }
    if (btnContinue) {
      btnContinue.disabled = false;
      btnContinue.removeAttribute('aria-busy');
    }
    return false;
  }
}

// ---------------------------------------------------------------------------
// ÉTAPE 2 — Configuration des colonnes
// ---------------------------------------------------------------------------

// Map of predefined format presets: key → { regex, hint }
const FORMAT_PRESETS = {
  // Formats généraux
  year:         { regex: '^\\d{4}$',                            hint: 'Accepte : 2024, 1999. Rejette : 24, deux mille.' },
  yes_no:       { regex: '(?i)^(oui|non|o|n|yes|no|vrai|faux|true|false|1|0|actif|inactif|active|inactive|enabled|disabled)$', hint: 'Accepte : oui/non, vrai/faux, 1/0, actif/inactif, enabled/disabled (majuscules ou minuscules).' },
  alphanum:     { regex: '^[A-Za-z0-9]+$',                      hint: 'Accepte : ABC123, test42. Rejette : test@42, hello world.' },
  letters_only: { regex: "^[A-Za-z\\u00C0-\\u00FF\\s\\-']+$",  hint: "Accepte : Jean-Pierre, José, l'Île. Rejette : test123, @nom." },
  positive_int: { regex: '^\\d+$',                              hint: 'Accepte : 0, 42, 1000. Rejette : -1, 3.14.' },
  // Identifiants & liens
  doi:          { regex: '^10\\.\\d{4,9}/[^\\s]+$',            hint: "Accepte : 10.1000/xyz123, 10.5281/zenodo.12345. Rejette : doi:10.1000 (préfixe 'doi:' non inclus), texte libre." },
  orcid:        { regex: '^\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]$', hint: 'Accepte : 0000-0002-1825-0097, 0000-0001-5109-3700. Rejette : sans tirets, trop court.' },
  ark:          { regex: '^ark:/\\d{5}/.+$',                    hint: 'Accepte : ark:/67375/ABC-123. Rejette : ark:67375 (manque le /), texte libre.' },
  issn:         { regex: '^\\d{4}-\\d{3}[\\dX]$',              hint: 'Accepte : 0317-8471, 1234-567X. Rejette : sans tiret, trop court.' },
  isbn13:       { regex: '^97[89][\\d\\- ]{10,14}$',            hint: 'Accepte : 9781234567890, 978-1-23-456789-0. Rejette : 123456789, trop court.' },
  isbn10:       { regex: '^[\\dX\\- ]{10,13}$',                hint: 'Accepte : 0123456789, 012345678X, 0-12-345678-9. Rejette : trop court, lettres.' },
  email_preset: { regex: '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$',     hint: 'Accepte : user@example.com, a.b@c.fr. Rejette : user@, @domain, texte libre.' },
  url:          { regex: '^(https?://\\S+|www\\.[^\\s/]+\\.\\S+)$', hint: 'Accepte : https://example.org, http://site.fr, www.example.com. Rejette : exemple, ftp://site.' },
  // Dates
  w3cdtf:       { regex: '^\\d{4}(-\\d{2}(-\\d{2})?)?$',       hint: 'Accepte : 2024, 2024-01, 2024-01-15. Rejette : 15/01/2024, 24.' },
  iso_date:     { regex: '^\\d{4}-\\d{2}-\\d{2}$',             hint: 'Accepte : 2024-01-15. Rejette : 2024, 15/01/2024, 2024-1-5.' },
  date_fr:      { regex: '^\\d{2}/\\d{2}/\\d{4}$',             hint: 'Accepte : 15/01/2024, 01/12/1999. Rejette : 2024-01-15 (format ISO), 1/1/2024 (sans zéros).' },
  // Codes & référentiels
  lang_iso639:  { regex: '(?i)^[a-z]{2,3}$',                   hint: 'Accepte : fr, en, de, ita, oci. Rejette : français, FR-fr, french.' },
  bcp47:        { regex: '^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$', hint: 'Accepte : fr, fr-FR, en-GB, oc, pt-BR. Rejette : français, FRA (trop long sans subtag).' },
  country_iso:  { regex: '^[A-Z]{2}$',                         hint: 'Accepte : FR, DE, US, IT. Rejette : fra (3 lettres), France (nom complet), fr (minuscules).' },
  // Nombres & mesures
  integer:      { regex: '^-?\\d+$',                           hint: 'Accepte : 42, -7, 0. Rejette : 3.14, 2,5, texte.' },
  decimal:      { regex: '^-?\\d+(?:[\\.,]\\d+)?$',            hint: 'Accepte : 42, 3.14, 2,5, -0.75. Rejette : 12.3.4, texte.' },
  latitude:     { regex: '^-?([0-8]?\\d(\\.\\d+)?|90(\\.0+)?)$',                        hint: 'Accepte : 48.8566, -33.8688, 0, 90, -90. Rejette : 91, -91, texte.' },
  longitude:    { regex: '^-?(1[0-7]\\d(\\.\\d+)?|180(\\.0+)?|[0-9]{1,2}(\\.\\d+)?)$',  hint: 'Accepte : 2.3522, -122.4194, 0, 180, -180. Rejette : 181, -181, texte.' },
};

// Default Oui/Non values
const YESNO_DEFAULT_TRUE  = 'oui, o, vrai, true, yes, y, 1, actif, active, enabled';
const YESNO_DEFAULT_FALSE = 'non, n, faux, false, no, 0, inactif, inactive, disabled';

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
function _updateFormatPresetUI(presetValue, contentType = null) {
  const hintEl      = document.getElementById('cfg-format-hint');
  const customWrap  = document.getElementById('cfg-custom-regex-wrap');
  const yesnoWrap   = document.getElementById('cfg-yesno-wrap');
  const currentType = contentType ?? (document.getElementById('cfg-content-type')?.value || '');

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
  } else if (currentType && CONTENT_TYPE_FORMAT_HINTS[currentType]) {
    hintEl.textContent = CONTENT_TYPE_FORMAT_HINTS[currentType];
    hintEl.hidden = false;
  }
}

// Wire up the preset dropdown change event (runs once at page load)
document.getElementById('cfg-format-preset')?.addEventListener('change', function () {
  _updateFormatPresetUI(this.value);
});

document.getElementById('cfg-content-type')?.addEventListener('change', function () {
  const previousPreset = document.getElementById('cfg-format-preset')?.value || '';
  const effectivePreset = _rebuildFormatPresetOptions(this.value, previousPreset);
  _updateFormatPresetUI(effectivePreset, this.value);
});

// Enable/disable list option fields based on separator input
document.getElementById('cfg-list-separator')?.addEventListener('input', function () {
  _updateListOptionsState(this.value.trim());
});

// Real-time preview debounce — listen on the whole panel (event delegation)
let _previewRuleTimer = null;
document.getElementById('column-config-panel')?.addEventListener('input',  () => {
  _schedulePreviewRule();
  _refreshFormatSuggestionUI();
});
document.getElementById('column-config-panel')?.addEventListener('change', () => {
  _schedulePreviewRule();
  _refreshFormatSuggestionUI();
});

document.getElementById('btn-close-column-config')?.addEventListener(
  'click',
  (e) => {
    e.preventDefault();
    e.stopPropagation();
    closeColumnConfig();
  },
  true
);

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

const _previewTableContainerEl = document.getElementById('preview-table-container');
const _previewScrollTopEl = document.getElementById('preview-scroll-top');
const _previewScrollTopInnerEl = document.getElementById('preview-scroll-top-inner');
let _previewScrollSyncLock = false;

function _refreshPreviewTopScrollbar() {
  if (!_previewTableContainerEl || !_previewScrollTopEl || !_previewScrollTopInnerEl) return;
  const tableEl = document.getElementById('preview-table');
  if (!tableEl || tableEl.hidden) {
    _previewScrollTopEl.hidden = true;
    return;
  }

  const scrollWidth = _previewTableContainerEl.scrollWidth;
  const clientWidth = _previewTableContainerEl.clientWidth;
  const hasOverflow = scrollWidth > (clientWidth + 1);

  _previewScrollTopInnerEl.style.width = `${scrollWidth}px`;
  _previewScrollTopEl.hidden = !hasOverflow;
  if (hasOverflow) {
    _previewScrollTopEl.scrollLeft = _previewTableContainerEl.scrollLeft;
  }
}

if (_previewScrollTopEl && _previewTableContainerEl) {
  _previewScrollTopEl.addEventListener('scroll', () => {
    if (_previewScrollSyncLock) return;
    _previewScrollSyncLock = true;
    _previewTableContainerEl.scrollLeft = _previewScrollTopEl.scrollLeft;
    _previewScrollSyncLock = false;
  });
  _previewTableContainerEl.addEventListener('scroll', () => {
    if (_previewScrollSyncLock) return;
    _previewScrollSyncLock = true;
    _previewScrollTopEl.scrollLeft = _previewTableContainerEl.scrollLeft;
    _previewScrollSyncLock = false;
  });
  window.addEventListener('resize', _refreshPreviewTopScrollbar);
}

function _populateSampleRowSelect(rowCount) {
  const sel = document.getElementById('sample-row-select');
  if (!sel) return;
  sel.innerHTML = '';
  if (rowCount < 1) {
    sel.disabled = true;
    return;
  }
  sel.disabled = false;
  for (let i = 0; i < rowCount; i++) {
    const opt = document.createElement('option');
    opt.value = String(i);
    opt.textContent = `Ligne ${i + 1} (données)`;
    sel.appendChild(opt);
  }
  const idx = Math.min(state.sampleRowIndex ?? 0, rowCount - 1);
  state.sampleRowIndex = Math.max(0, idx);
  sel.value = String(state.sampleRowIndex);
}

/** Affiche le sélecteur de ligne et l’aide uniquement lorsque les valeurs d’exemple sont visibles et qu’il y a des lignes. */
function _updateSampleLinePickerVisibility() {
  const wrap = document.getElementById('sample-row-line-picker');
  const hint = document.querySelector('.column-nav-sample-hint');
  const hasRows = state.previewDataRows && state.previewDataRows.length > 0;
  const show = state.showSampleValues && hasRows;
  if (wrap) wrap.hidden = !show;
  if (hint) hint.hidden = !show;
}

document.getElementById('sample-row-select')?.addEventListener('change', e => {
  state.sampleRowIndex = parseInt(e.target.value, 10) || 0;
  _buildColumnNavList(state.columns);
});

/** Met en surbrillance l’entrée correspondante dans la liste verticale des colonnes. */
function _syncColumnNavSelection(colName) {
  document.querySelectorAll('#column-nav-list .column-nav-item').forEach(btn => {
    const match = Boolean(colName && btn.dataset.column === colName);
    btn.classList.toggle('column-nav-selected', match);
    if (match) btn.scrollIntoView({ block: 'nearest' });
  });
}

function _buildColumnNavList(columns) {
  const nav = _getColumnNavEl();
  if (!nav) return;
  nav.innerHTML = '';
  const cols = Array.isArray(columns)
    ? columns.map((c) => String(c))
    : [];
  const showValues =
    state.showSampleValues &&
    state.previewDataRows &&
    state.previewDataRows.length > 0;
  const row = showValues ? state.previewDataRows[state.sampleRowIndex] : null;

  try {
  cols.forEach((col, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'column-nav-item';
    btn.dataset.column = col;
    const cfg = state.columnConfig[col];
    const nameSpan = document.createElement('span');
    nameSpan.className = 'column-nav-name';
    nameSpan.textContent = col;
    const statSpan = document.createElement('span');
    statSpan.className = 'column-nav-stat';
    statSpan.textContent = _columnNavStatLabel(col);
    btn.appendChild(nameSpan);
    btn.appendChild(statSpan);
    btn.addEventListener('click', () => openColumnConfig(col));
    if (_isColumnConfigured(col)) {
      btn.classList.add('column-nav-configured');
    }
    btn.title = _columnNavStatTitle(col);

    if (showValues && row) {
      const wrap = document.createElement('div');
      wrap.className = 'column-nav-row';
      const valEl = document.createElement('span');
      valEl.className = 'column-nav-value';
      const raw = row[i] ?? '';
      valEl.dataset.rawText = String(raw);
      if (state.showSpecialChars) {
        valEl.innerHTML = renderVisibleChars(raw);
      } else {
        valEl.textContent = raw;
      }
      wrap.appendChild(btn);
      wrap.appendChild(valEl);
      nav.appendChild(wrap);
    } else {
      nav.appendChild(btn);
    }
  });

  if (cols.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'column-nav-empty format-hint';
    empty.textContent = 'Aucune colonne dans le fichier importé.';
    nav.appendChild(empty);
  }

  if (state.activeColumn && cols.includes(state.activeColumn)) {
    _syncColumnNavSelection(state.activeColumn);
  }
  nav.setAttribute('aria-busy', 'false');
  } catch (err) {
    console.error('column-nav-list', err);
    nav.innerHTML =
      '<p class="msg-error" role="alert">Impossible d’afficher la liste des colonnes. Rechargez la page ou réessayez.</p>';
    nav.setAttribute('aria-busy', 'false');
  }
}

async function loadPreview() {
  _restoreJobSession();
  _syncConfigureStepButton();
  if (!state.jobId) {
    _setColumnNavNoSessionMessage();
    return;
  }

  const loadingEl = document.getElementById('preview-loading');
  const tableEl = document.getElementById('preview-table');
  const headerRow = document.getElementById('preview-header');
  const body = document.getElementById('preview-body');
  if (!loadingEl || !tableEl || !headerRow || !body) {
    console.error('loadPreview: éléments #preview-loading / #preview-table introuvables');
    const colNavMissing = _getColumnNavEl();
    if (colNavMissing) {
      colNavMissing.removeAttribute('aria-busy');
      colNavMissing.innerHTML =
        '<p class="msg-error" role="alert">Interface d’aperçu incomplète. Rechargez la page.</p>';
    }
    return;
  }

  loadingEl.className = 'msg-info';
  loadingEl.textContent = 'Chargement de l\'aperçu…';
  loadingEl.hidden = false;
  tableEl.hidden = true;
  if (_previewScrollTopEl) _previewScrollTopEl.hidden = true;
  headerRow.innerHTML = '';
  body.innerHTML = '';
  const colNavEl = _getColumnNavEl();
  if (colNavEl) {
    colNavEl.setAttribute('aria-busy', 'true');
    colNavEl.innerHTML =
      '<p class="column-nav-loading format-hint">Chargement des colonnes…</p>';
  }
  state.previewDataRows = null;
  const sampleSel = document.getElementById('sample-row-select');
  if (sampleSel) {
    sampleSel.innerHTML = '';
    sampleSel.disabled = true;
  }
  _updateSampleLinePickerVisibility();

  try {
    const [previewResp, configResp] = await Promise.all([
      fetch(`/api/jobs/${state.jobId}/preview?rows=30`),
      fetch(`/api/jobs/${state.jobId}/column-config`),
    ]);

    if (!previewResp.ok) {
      if (previewResp.status === 404) {
        state.jobId = null;
        _clearJobSessionStorage();
        _syncConfigureStepButton();
      }
      throw new Error('Impossible de charger l\'aperçu');
    }
    const preview = await previewResp.json();

    if (configResp.ok) {
      const configData = await configResp.json();
      state.columnConfig = configData.columns || {};
      state.columnUserSaved = configData.user_overrides || {};
      state.columnUserFormatSaved = configData.user_format_overrides || {};
    }

    let rawCols = Array.isArray(preview.columns) ? preview.columns : [];
    if (rawCols.length === 0 && Array.isArray(state.columns) && state.columns.length > 0) {
      rawCols = state.columns;
    }
    state.columns = rawCols.map((c) => String(c));
    state.previewDataRows = Array.isArray(preview.rows) ? preview.rows : [];
    _populateSampleRowSelect(state.previewDataRows.length);
    _updateSampleLinePickerVisibility();

    // Build header row
    state.columns.forEach((col) => {
      const th = document.createElement('th');
      th.textContent = col;
      th.dataset.column = col;
      th.addEventListener('click', () => openColumnConfig(col));
      if (_isColumnConfigured(col)) {
        th.classList.add('column-configured');
        th.title = _columnNavStatTitle(col);
      } else {
        th.title = _columnNavStatTitle(col);
      }
      headerRow.appendChild(th);
    });

    _buildColumnNavList(state.columns);

    _persistJobSession();

    // Build body rows
    state.previewDataRows.forEach((row, rowIdx) => {
      const tr = document.createElement('tr');
      const cells = Array.isArray(row) ? row : [];
      cells.forEach((cell, i) => {
        const td = document.createElement('td');
        const rawVal = cell ?? '';
        td.dataset.rawText = rawVal;
        td.dataset.colIdx = i;
        td.dataset.row = rowIdx;
        td.dataset.col = state.columns[i] || '';
        if (state.showSpecialChars) {
          td.innerHTML = renderVisibleChars(rawVal);
        } else {
          td.textContent = rawVal;
        }
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });

    loadingEl.hidden = true;
    tableEl.hidden = false;
    _refreshPreviewTopScrollbar();

    if (state.activeColumn && state.columns.includes(state.activeColumn)) {
      const col = state.activeColumn;
      const colIdx = state.columns.indexOf(col);
      document.querySelectorAll('#preview-header th').forEach(th => {
        th.classList.toggle('column-selected', th.dataset.column === col);
      });
      document.querySelectorAll('#preview-body tr').forEach(tr => {
        tr.querySelectorAll('td').forEach((td, i) => {
          td.classList.toggle('column-selected', i === colIdx);
        });
      });
      _schedulePreviewRule();
      void _loadFormatSuggestion(state.activeColumn, true);
    }

    // Apply cell-level issue highlights if validation has already been run
    if (state.validationDone) _applyCellIssueHighlights();

    // Consume pending cell navigation (triggered from the Results step)
    if (_pendingCellNav) {
      const nav = _pendingCellNav;
      _pendingCellNav = null;
      setTimeout(() => {
        const sel = document.getElementById('sample-row-select');
        if (sel && !sel.disabled && nav.rowIdx >= 0 && nav.rowIdx < sel.options.length) {
          state.sampleRowIndex = nav.rowIdx;
          sel.value = String(nav.rowIdx);
          _buildColumnNavList(state.columns);
        }
        _highlightCell(nav.rowIdx, nav.colName);
      }, 50);
    }
  } catch (err) {
    loadingEl.textContent = 'Erreur lors du chargement de l\'aperçu : ' + err.message;
    loadingEl.className = 'msg-error';
    if (_previewScrollTopEl) _previewScrollTopEl.hidden = true;
    const colNavErr = _getColumnNavEl();
    if (colNavErr) {
      colNavErr.setAttribute('aria-busy', 'false');
      colNavErr.innerHTML = `<p class="msg-error" role="alert">Impossible de charger les colonnes. ${esc(err.message)}</p>`;
    }
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
      td.title = renderVisibleCharsText(issue.message);
    });
  } catch (_) { /* non-bloquant */ }
}

function openColumnConfig(colName) {
  const prevOpen = state.activeColumn;
  // Auto-save previous column silently (local state only)
  if (state.activeColumn && state.activeColumn !== colName) {
    _saveCurrentPanelToState();
  }

  state.activeColumn = colName;

  // Update header highlights
  document.querySelectorAll('#preview-header th').forEach(th => {
    th.classList.toggle('column-selected', th.dataset.column === colName);
  });
  _syncColumnNavSelection(colName);
  // Highlight column cells
  const colIdx = state.columns.indexOf(colName);
  document.querySelectorAll('#preview-body tr').forEach(tr => {
    tr.querySelectorAll('td').forEach((td, i) => {
      td.classList.toggle('column-selected', i === colIdx);
    });
  });

  // Populate panel
  const cfg = state.columnConfig[colName] || {};
  const normalized = _normalizeTypeAndPreset(cfg);
  document.getElementById('col-config-name').textContent = colName;
  document.getElementById('cfg-required').checked = cfg.required || false;
  const contentType = normalized.contentType;
  document.getElementById('cfg-content-type').value = contentType;
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
  let preset = normalized.preset;
  preset = _rebuildFormatPresetOptions(contentType, preset);
  document.getElementById('cfg-regex').value = preset === 'custom' ? (cfg.regex || '') : '';
  // Oui/Non custom values
  document.getElementById('cfg-yesno-true').value  = cfg.yes_no_true_values  || '';
  document.getElementById('cfg-yesno-false').value = cfg.yes_no_false_values || '';
  _updateFormatPresetUI(preset, contentType);

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

  // Restaurer le sélecteur de sous-ensemble si le vocabulaire est en cache
  const vocabSelectorEl = document.getElementById('cfg-vocab-selector');
  const cachedVocab = cfg.nakala_vocabulary ? state.loadedVocabs[cfg.nakala_vocabulary] : null;
  const cachedLabels = cfg.nakala_vocabulary ? (state.loadedVocabLabels[cfg.nakala_vocabulary] || {}) : {};
  if (cachedVocab && cachedVocab.length > 0) {
    const savedSelection = Array.isArray(cfg.allowed_values) && cfg.allowed_values.length > 0
      ? cfg.allowed_values : null;
    _buildVocabSelector(cachedVocab, savedSelection, cachedLabels);
  } else {
    vocabSelectorEl.hidden = true;
    document.getElementById('vocab-selector-list').innerHTML = '';
  }

  // Reset saved indicator
  const savedEl = document.getElementById('col-config-saved');
  savedEl.hidden = true;

  _syncColConfigOnboardingVisibility();
  _renderFormatSuggestion(colName);

  // Show panel
  document.getElementById('column-config-panel').hidden = false;
  document.querySelector('.configure-config-column')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // Trigger initial preview
  _schedulePreviewRule();
  void _loadFormatSuggestion(colName);

  if (prevOpen && prevOpen !== colName) _updateConfiguredMarker(prevOpen);
  _updateConfiguredMarker(colName);
}

function closeColumnConfig() {
  const closing = state.activeColumn;
  if (state.activeColumn) _saveCurrentPanelToState();
  state.activeColumn = null;

  document.querySelectorAll('#preview-header th').forEach(th => th.classList.remove('column-selected'));
  document.querySelectorAll('#preview-body td').forEach(td => td.classList.remove('column-selected'));
  _syncColumnNavSelection(null);
  document.getElementById('column-config-panel').hidden = true;
  _hideFormatSuggestion();
  if (closing) _updateConfiguredMarker(closing);
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
  let contentType = document.getElementById('cfg-content-type').value || null;
  if (contentType === 'number' && preset === 'integer') {
    contentType = 'number';
  } else if (contentType === 'number' && preset === 'decimal') {
    contentType = 'number';
  } else if (contentType === 'address' && (preset === 'email_preset' || preset === 'url')) {
    contentType = 'address';
  }

  return {
    required: document.getElementById('cfg-required').checked || false,
    content_type: contentType,
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

    _markUserColumnConfigSaved();
    state.columnUserSaved[state.activeColumn] = true;

    // Visual feedback
    const savedEl = document.getElementById('col-config-saved');
    savedEl.hidden = false;
    setTimeout(() => { savedEl.hidden = true; }, 2000);

    await _reloadColumnConfigFromServer();
    // Mark configured indicators on all header columns
    _updateColumnBadges();
    _refreshFormatSuggestionUI();
  } catch (err) {
    alert('Erreur lors de l\'enregistrement : ' + err.message);
  }
}

function _buildConfigSummary(cfg) {
  if (!cfg) return '';
  const normalized = _normalizeTypeAndPreset(cfg);
  const parts = [];
  if (cfg.required) parts.push('Obligatoire');
  if (normalized.contentType) {
    parts.push('Nature : ' + (CONTENT_TYPE_LABELS[normalized.contentType] || normalized.contentType));
  }
  if (cfg.unique) parts.push('Valeurs uniques');
  if (normalized.preset && normalized.preset !== 'custom') {
    parts.push('Format : ' + (FORMAT_PRESET_LABELS[normalized.preset] || normalized.preset));
  } else if (normalized.preset === 'custom' && cfg.regex) {
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
  if (cfg.detect_similar_values) parts.push('Valeurs similaires détectées');
  if (cfg.nakala_vocabulary) parts.push('Vocabulaire NAKALA');
  return parts.join(' · ') || 'Configurée';
}

/** Tooltip liste colonnes : état + résumé détaillé (fusion modèle). */
function _columnNavStatTitle(colName) {
  const cfg = state.columnConfig[colName] || {};
  const userSaved = !!(state.columnUserSaved && state.columnUserSaved[colName]);
  const summary = _buildConfigSummary(cfg);
  const head = userSaved
    ? 'Colonne personnalisée (réglages enregistrés sur le serveur).'
    : 'Pas encore de surcharges enregistrées — affichage selon le modèle ou le mode manuel.';
  return summary ? `${head}\n${summary}` : head;
}

function _updateColumnBadges() {
  state.columns.forEach(col => _updateConfiguredMarker(col));
}

function _updateConfiguredMarker(colName) {
  const th = document.querySelector(`#preview-header th[data-column="${CSS.escape(colName)}"]`);
  if (th) {
    if (_isColumnConfigured(colName)) {
      th.classList.add('column-configured');
      th.title = _columnNavStatTitle(colName);
    } else {
      th.classList.remove('column-configured');
      th.title = _columnNavStatTitle(colName);
    }
  }
  const navBtn = document.querySelector(
    `#column-nav-list .column-nav-item[data-column="${CSS.escape(colName)}"]`
  );
  if (navBtn) {
    const cfg = state.columnConfig[colName];
    navBtn.classList.toggle('column-nav-configured', _isColumnConfigured(colName));
    navBtn.title = _columnNavStatTitle(colName);
    const stat = navBtn.querySelector('.column-nav-stat');
    if (stat) stat.textContent = _columnNavStatLabel(colName);
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
    cfg.nakala_vocabulary ||
    cfg.detect_rare_values ||
    cfg.detect_similar_values
  );
}

async function showConfigSummary() {
  // Auto-save any open panel
  if (state.activeColumn) {
    _saveCurrentPanelToState();
    const cfg = state.columnConfig[state.activeColumn];
    const colSaved = state.activeColumn;
    try {
      const resp = await fetch(`/api/jobs/${state.jobId}/column-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns: { [state.activeColumn]: cfg } }),
      });
      if (resp.ok) {
        _markUserColumnConfigSaved();
        state.columnUserSaved[colSaved] = true;
        await _reloadColumnConfigFromServer();
      }
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
    const colSaved = state.activeColumn;
    try {
      const resp = await fetch(`/api/jobs/${state.jobId}/column-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns: { [state.activeColumn]: cfg } }),
      });
      if (resp.ok) {
        _markUserColumnConfigSaved();
        state.columnUserSaved[colSaved] = true;
        await _reloadColumnConfigFromServer();
      }
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
    if (!resp.ok) {
      const detail = await _extractErrorDetail(resp, 'Échec de l\'application des correctifs');
      throw new Error(_formatActionError('Application des correctifs', resp.status, detail));
    }
    await updateUndoRedoButtons();
    enableStep('validate');
    goToStep('validate');
  } catch (err) {
    _showToast(`Erreur : ${err.message}`, 'error', 7000);
  }
}

/** Annuler le dernier correctif. */
async function undoFix() {
  if (!state.jobId) return;
  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/undo`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      _showToast('↩ Modification annulée', 'success');
      _invalidateFormatSuggestionCache();
      if (state.currentStep === 'configure') {
        await loadPreview();
      } else {
        await previewFixes();
      }
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
      _showToast('↪ Modification rétablie', 'success');
      _invalidateFormatSuggestionCache();
      if (state.currentStep === 'configure') {
        await loadPreview();
      } else {
        await previewFixes();
      }
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
  // Also sync the configure-step undo/redo buttons
  const btnUndoConf = document.getElementById('btn-undo-configure');
  const btnRedoConf = document.getElementById('btn-redo-configure');
  if (btnUndoConf) btnUndoConf.disabled = !canUndo;
  if (btnRedoConf) btnRedoConf.disabled = !canRedo;
}

function skipFixes() {
  enableStep('validate');
  goToStep('validate');
}

// ---------------------------------------------------------------------------
// ÉTAPE 4 — Validation
// ---------------------------------------------------------------------------
function _applyRuleFailAndExportWarnings(data) {
  state.ruleFailures = data['échecs_règles'] || [];
  state.exportWarnings = data['avertissements_export'] || [];
  _renderValidationRuleFailures();
  _renderResultsExportWarnings();
}

function _renderValidationRuleFailures() {
  const el = document.getElementById('validate-rule-failures');
  if (!el) return;
  const rf = state.ruleFailures || [];
  if (!rf.length) {
    el.hidden = true;
    el.innerHTML = '';
    return;
  }
  el.hidden = false;
  const lines = rf.map((r) => {
    const id = r['règle'] ?? '';
    const col = r.colonne;
    const msg = r.message || '';
    return `<li><strong>${esc(id)}</strong>${col ? ` — ${esc(col)}` : ''} : ${esc(msg)}</li>`;
  });
  el.innerHTML = `<p><strong>Attention :</strong> certaines règles n'ont pas pu s'exécuter :</p><ul>${lines.join('')}</ul>`;
}

function _renderResultsExportWarnings() {
  const el = document.getElementById('results-export-warnings');
  if (!el) return;
  const ew = state.exportWarnings || [];
  if (!ew.length) {
    el.hidden = true;
    el.innerHTML = '';
    return;
  }
  el.hidden = false;
  const lines = ew.map((t) => `<li>${esc(t)}</li>`).join('');
  el.innerHTML = `<p><strong>Attention — exports :</strong></p><ul>${lines.join('')}</ul>`;
}

async function runValidation() {
  if (!state.jobId) return;

  const progEl = document.getElementById('validate-progress');
  const sumEl = document.getElementById('validate-summary');
  progEl.hidden = false;
  sumEl.hidden = true;

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/validate`, { method: 'POST' });
    if (!resp.ok) {
      const detail = await _extractErrorDetail(resp, 'Erreur de validation');
      throw new Error(_formatActionError('Validation', resp.status, detail));
    }
    const data = await resp.json();
    const résumé = data['résumé'] || {};
    _applyRuleFailAndExportWarnings(data);

    document.getElementById('sum-errors').textContent = résumé['erreurs'] ?? 0;
    document.getElementById('sum-warnings').textContent = résumé['avertissements'] ?? 0;
    document.getElementById('sum-suspicions').textContent = résumé['suspicions'] ?? 0;
    document.getElementById('sum-total').textContent = résumé['total'] ?? 0;

    progEl.hidden = true;
    sumEl.hidden = false;
    state.validationDone = true;

    enableStep('results');
    _updateStepCoach();
  } catch (err) {
    const msg = err?.message || 'Erreur de validation';
    progEl.innerHTML = `<p class="msg-error">Erreur : ${esc(msg).replace(/\n/g, '<br>')}</p>`;
    _showToast(`Erreur de validation.\n${msg}`, 'error', 7000);
    _updateStepCoach();
  }
}

// ---------------------------------------------------------------------------
// ÉTAPE 5 — Résultats
// ---------------------------------------------------------------------------
async function _applySuggestionToCell(rowNum, colName, suggestion) {
  if (!state.jobId || !colName) return false;
  if (!suggestion) return false;
  if (rowNum > 30) {
    _showToast(
      `Ligne ${rowNum} hors aperçu (30 lignes max). Utilisez la correction manuelle.`,
      'warning',
      6000
    );
    return false;
  }

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/edit-cell`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ row: rowNum - 1, column: colName, value: suggestion }),
    });
    if (!resp.ok) {
      const detail = await _extractErrorDetail(resp, 'Échec de la modification');
      throw new Error(_formatActionError('Application de la suggestion', resp.status, detail));
    }

    _updatePreviewDataCell(rowNum - 1, colName, suggestion, { markEdited: true });
    _invalidateFormatSuggestionCache(colName);
    _refreshOpenColumnAfterDataMutation(colName);
    _manualEditsCount++;
    _showCellsEditedBanner();
    await updateUndoRedoButtons();
    _showToastWithRevalidateLink('Suggestion appliquée. Pensez à re-valider.');
    return true;
  } catch (err) {
    _showToast(`Erreur : ${err.message}`, 'error', 7000);
    return false;
  }
}

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
    if (!resp.ok) {
      const detail = await _extractErrorDetail(resp, 'Échec du chargement');
      throw new Error(_formatActionError('Chargement des problèmes', resp.status, detail));
    }
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
        const rowNum = parseInt(p['ligne']);
        const suggestion = p['suggestion'] || '';

        const tr = document.createElement('tr');
        tr.classList.add('problem-row-clickable');
        if (status === 'IGNORED') tr.classList.add('issue-ignored');
        if (status === 'EXCEPTED') tr.classList.add('issue-excepted');
        tr.dataset.row = rowNum;
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
        tdLig.textContent = rowNum;
        tr.appendChild(tdLig);

        const tdVal = document.createElement('td');
        tdVal.className = 'td-cell-value';
        const rawVal = p['valeur'] || '';
        tdVal.dataset.rawText = rawVal;
        if (state.showSpecialChars) {
          tdVal.innerHTML = renderVisibleChars(rawVal);
        } else {
          tdVal.textContent = rawVal;
        }
        tr.appendChild(tdVal);

        const tdMsg = document.createElement('td');
        tdMsg.textContent = p['message'];
        tr.appendChild(tdMsg);

        const tdSug = document.createElement('td');
        tdSug.textContent = suggestion;
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
          if (suggestion && rowNum <= 30) {
            const bApply = document.createElement('button');
            bApply.className = 'btn-status btn-apply-suggestion';
            bApply.textContent = 'Appliquer';
            bApply.title = 'Appliquer directement la suggestion sur la cellule';
            bApply.onclick = () => _applySuggestionToCell(rowNum, p['colonne'], suggestion);
            tdAct.appendChild(bApply);
          }
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
        tdNav.style.whiteSpace = 'nowrap';
        const navSpan = document.createElement('span');
        navSpan.className = 'problem-nav-icon';
        navSpan.title = 'Localiser dans le tableau';
        navSpan.textContent = '→';
        navSpan.style.cursor = 'pointer';
        navSpan.addEventListener('click', (e) => {
          e.stopPropagation();
          navigateToCell(parseInt(tr.dataset.row), tr.dataset.col);
        });
        tdNav.appendChild(navSpan);

        // Bouton "Corriger"
        const bFix = document.createElement('button');
        bFix.className = 'btn-status';
        bFix.style.marginLeft = '4px';
        bFix.textContent = '✏️';
        bFix.title = 'Corriger cette cellule';
        bFix.addEventListener('click', async (e) => {
          e.stopPropagation();
          const colName = tr.dataset.col;

          if (rowNum > 30) {
            _showToast(
              `Ligne ${rowNum} hors aperçu (30 lignes max). Corrigez via export ou par lot.`,
              'warning',
              6000
            );
            return;
          }

          if (suggestion) {
            // Afficher un dialogue inline
            const existing = tdNav.querySelector('.fix-inline-dialog');
            if (existing) { existing.remove(); return; }
            const dialog = document.createElement('div');
            dialog.className = 'fix-inline-dialog';
            dialog.style.cssText = 'position:absolute;z-index:100;background:var(--color-surface);border:1px solid var(--color-border);border-radius:6px;padding:0.5rem 0.75rem;box-shadow:0 4px 16px rgba(0,0,0,.15);font-size:0.85rem;min-width:200px;right:0;top:1.5rem;';
            dialog.innerHTML = `<div style="margin-bottom:0.4rem;">Appliquer <strong>${esc(suggestion)}</strong> ?</div>`;
            const btnApply = document.createElement('button');
            btnApply.className = 'btn btn-primary btn-sm';
            btnApply.style.fontSize = '0.8rem';
            btnApply.style.padding = '3px 10px';
            btnApply.textContent = 'Appliquer';
            btnApply.onclick = async () => {
              dialog.remove();
              await _applySuggestionToCell(rowNum, colName, suggestion);
            };
            const btnEdit = document.createElement('button');
            btnEdit.className = 'btn btn-secondary btn-sm';
            btnEdit.style.fontSize = '0.8rem';
            btnEdit.style.padding = '3px 10px';
            btnEdit.style.marginLeft = '4px';
            btnEdit.textContent = 'Modifier';
            btnEdit.onclick = () => {
              dialog.remove();
              navigateToCell(rowNum, colName);
              setTimeout(() => {
                const colIdx = state.columns.indexOf(colName);
                if (colIdx < 0) return;
                const rows = document.querySelectorAll('#preview-body tr');
                const tdTarget = rows[rowNum - 1]?.querySelectorAll('td')[colIdx];
                if (tdTarget) startCellEdit(tdTarget);
              }, 300);
            };
            dialog.appendChild(btnApply);
            dialog.appendChild(btnEdit);
            // Fermer en cliquant ailleurs
            setTimeout(() => document.addEventListener('click', function _close(ev) {
              if (!dialog.contains(ev.target)) { dialog.remove(); document.removeEventListener('click', _close); }
            }), 50);
            tdNav.style.position = 'relative';
            tdNav.appendChild(dialog);
          } else {
            // Pas de suggestion — naviguer + éditer directement
            navigateToCell(rowNum, colName);
            setTimeout(() => {
              const colIdx = state.columns.indexOf(colName);
              if (colIdx < 0) return;
              const rows = document.querySelectorAll('#preview-body tr');
              const tdTarget = rows[rowNum - 1]?.querySelectorAll('td')[colIdx];
              if (tdTarget) startCellEdit(tdTarget);
            }, 300);
          }
        });
        tdNav.appendChild(bFix);
        tr.appendChild(tdNav);

        tbody.appendChild(tr);
      }
    }

    // Reset check-all and bulk bar after reload
    const checkAll = document.getElementById('check-all-problems');
    if (checkAll) checkAll.checked = false;
    _updateBulkActionBar();

    renderPagination(page, data.pages);
    _updateStepCoach();
  } catch (err) {
    console.error('Erreur lors du chargement des problèmes', err);
    _showToast(`Impossible de charger les problèmes.\n${err?.message || ''}`.trim(), 'error', 7000);
    _updateStepCoach();
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

function _filenameFromContentDisposition(headerValue) {
  if (!headerValue) return null;
  // RFC 5987 form: filename*=UTF-8''...
  const extMatch = headerValue.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (extMatch && extMatch[1]) {
    try {
      return decodeURIComponent(extMatch[1].trim());
    } catch (_) { /* fallback below */ }
  }
  // Basic form: filename="..."
  const basicMatch = headerValue.match(/filename\s*=\s*"([^"]+)"/i);
  if (basicMatch && basicMatch[1]) return basicMatch[1].trim();
  return null;
}

async function downloadFile(filename) {
  if (!state.jobId) {
    _showToast('Aucune session active pour l\'export.', 'warning');
    return false;
  }
  if (!state.validationDone) {
    _showToast('Lancez la validation avant d\'exporter les fichiers.', 'warning');
    return false;
  }

  const url = `/api/jobs/${state.jobId}/download/${filename}`;
  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      let detail = '';
      try {
        const data = await resp.json();
        detail = data.detail || '';
      } catch (_) { /* ignore non-JSON errors */ }
      throw new Error(detail || `Téléchargement impossible (${resp.status})`);
    }

    const blob = await resp.blob();
    const serverFilename = _filenameFromContentDisposition(resp.headers.get('content-disposition'));
    const downloadName = serverFilename || filename;

    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = downloadName;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  } catch (err) {
    _showToast('✗ Erreur lors du téléchargement : ' + err.message, 'error');
  }
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
    cfg.required || cfg.content_type || cfg.unique || cfg.multiline_ok || cfg.format_preset ||
    cfg.regex || cfg.min_length != null || cfg.max_length != null ||
    cfg.forbidden_chars || cfg.expected_case ||
    (Array.isArray(cfg.allowed_values) && cfg.allowed_values.length) ||
    cfg.list_separator || cfg.detect_rare_values || cfg.detect_similar_values
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
  document.getElementById('cfg-vocab-selector').hidden = true;

  try {
    const resp = await fetch(`/api/nakala/vocabulary/${vocabName}`);
    const data = await resp.json();

    if (!resp.ok) {
      statusEl.textContent = data.detail || 'Erreur lors du chargement du vocabulaire.';
      statusEl.className = 'format-hint msg-error';
      return;
    }

    const values = data.values || [];
    const labels = data.labels || {};

    // Cache for panel-reopen restore
    state.loadedVocabs[vocabName] = values;
    state.loadedVocabLabels[vocabName] = labels;

    // Lock the allowed-values textarea and populate it (all values by default)
    const avEl = document.getElementById('cfg-allowed-values');
    avEl.readOnly = true;
    avEl.classList.add('av-locked');
    document.getElementById('cfg-av-locked-msg').hidden = false;

    const countEl = document.getElementById('cfg-av-count-msg');
    countEl.textContent = `${values.length} valeurs chargées depuis NAKALA`;
    countEl.hidden = false;
    document.getElementById('cfg-av-voir-tout').hidden = true;

    // Build selector — all selected by default (first load)
    _buildVocabSelector(values, null, labels);

    statusEl.textContent = `${values.length} valeurs chargées. Affinez la sélection ci-dessous.`;
    statusEl.className = 'format-hint msg-success';
    statusEl.hidden = false;

  } catch (err) {
    statusEl.textContent = 'Erreur : ' + err.message;
    statusEl.className = 'format-hint msg-error';
  }
}

// ---------------------------------------------------------------------------
// Sélecteur de sous-ensemble vocabulaire
// ---------------------------------------------------------------------------

/** Build (or rebuild) the vocabulary selector.
 *  @param {string[]} allValues  – full vocabulary list
 *  @param {string[]|null} selectedValues – subset to pre-check (null = all)
 *  @param {Object} [labels={}] – optional {uri: labelFR} for datatypes display
 */
function _buildVocabSelector(allValues, selectedValues, labels) {
  labels = labels || {};
  const selectorEl = document.getElementById('cfg-vocab-selector');
  const listEl     = document.getElementById('vocab-selector-list');
  const countEl    = document.getElementById('vocab-selector-count');
  const searchEl   = document.getElementById('vocab-search');

  const selectedSet = selectedValues ? new Set(selectedValues) : null;

  // For large vocabularies, show only first 100 + note
  const LIMIT = 100;
  const displayValues = allValues.length > LIMIT ? allValues.slice(0, LIMIT) : allValues;
  const truncated = allValues.length > LIMIT;

  countEl.textContent = `${allValues.length} valeur${allValues.length > 1 ? 's' : ''} chargée${allValues.length > 1 ? 's' : ''}`;
  searchEl.value = '';

  listEl.innerHTML = '';
  displayValues.forEach(val => {
    const labelEl = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = val;
    cb.checked = selectedSet === null || selectedSet.has(val);
    cb.addEventListener('change', _onVocabCheckChange);
    labelEl.appendChild(cb);
    // Si un libellé FR est disponible, afficher "Libellé (URI)" ; sinon juste la valeur
    const labelText = labels[val] ? `${labels[val]} (${val})` : val;
    labelEl.appendChild(document.createTextNode(' ' + labelText));
    // Stocker le texte de recherche combiné sur l'élément pour le filtre
    labelEl.dataset.searchText = labelText.toLowerCase();
    listEl.appendChild(labelEl);
  });

  if (truncated) {
    const note = document.createElement('p');
    note.className = 'vocab-truncate-note';
    note.textContent = `Affichage limité aux ${LIMIT} premières valeurs. Utilisez la recherche pour trouver d'autres valeurs.`;
    listEl.appendChild(note);
  }

  selectorEl.hidden = false;
  _updateVocabCounters(allValues.length);
  _syncVocabToState();
}

function _filterVocabSearch() {
  const query = document.getElementById('vocab-search').value.toLowerCase();
  document.querySelectorAll('#vocab-selector-list label').forEach(label => {
    // Recherche sur searchText (libellé + URI combinés) stocké en data-attribute
    const searchText = label.dataset.searchText || label.querySelector('input[type=checkbox]')?.value?.toLowerCase() || '';
    label.hidden = query !== '' && !searchText.includes(query);
  });
}

function _vocabSelectAll() {
  document.querySelectorAll('#vocab-selector-list label').forEach(label => {
    if (!label.hidden) {
      const cb = label.querySelector('input[type=checkbox]');
      if (cb) cb.checked = true;
    }
  });
  _onVocabCheckChange();
}

function _vocabSelectNone() {
  document.querySelectorAll('#vocab-selector-list label').forEach(label => {
    if (!label.hidden) {
      const cb = label.querySelector('input[type=checkbox]');
      if (cb) cb.checked = false;
    }
  });
  _onVocabCheckChange();
}

function _onVocabCheckChange() {
  const vocabName = document.getElementById('cfg-nakala-vocabulary').value;
  const allCached = vocabName ? (state.loadedVocabs[vocabName] || []) : [];
  _updateVocabCounters(allCached.length);
  _syncVocabToState();
}

function _updateVocabCounters(totalCount) {
  const checked = document.querySelectorAll('#vocab-selector-list input[type=checkbox]:checked');
  document.getElementById('vocab-selected-count').textContent =
    `${checked.length} / ${totalCount} sélectionnée${checked.length > 1 ? 's' : ''}`;
}

/** Write current checkbox selection back to state and update the locked textarea. */
function _syncVocabToState() {
  const checkedValues = Array.from(
    document.querySelectorAll('#vocab-selector-list input[type=checkbox]:checked')
  ).map(cb => cb.value);

  const vocabName = document.getElementById('cfg-nakala-vocabulary').value;
  const avEl = document.getElementById('cfg-allowed-values');
  avEl.value = checkedValues.slice(0, 20).join('\n') + (checkedValues.length > 20 ? '\n…' : '');

  if (state.activeColumn) {
    if (!state.columnConfig[state.activeColumn]) state.columnConfig[state.activeColumn] = {};
    state.columnConfig[state.activeColumn].allowed_values = checkedValues;
    state.columnConfig[state.activeColumn].allowed_values_locked = true;
    state.columnConfig[state.activeColumn].nakala_vocabulary = vocabName;
  }

  // Auto-save to server (non-blocking)
  if (state.jobId && state.activeColumn) {
    fetch(`/api/jobs/${state.jobId}/column-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        columns: {
          [state.activeColumn]: {
            allowed_values: checkedValues,
            allowed_values_locked: true,
            nakala_vocabulary: vocabName,
          },
        },
      }),
    })
      .then(resp => {
        if (resp.ok) {
          _markUserColumnConfigSaved();
          state.columnUserSaved[state.activeColumn] = true;
        }
        return _updateColumnBadges();
      })
      .catch(() => {});
  }
}

// ---------------------------------------------------------------------------
// Réinitialisation
// ---------------------------------------------------------------------------
function resetApp() {
  _hideCellsEditedBanner();
  state.jobId = null;
  _clearJobSessionStorage();
  state.filename = null;
  state.rows = 0;
  state.cols = 0;
  state.columns = [];
  state.currentPage = 1;
  state.columnConfig = {};
  state.columnUserSaved = {};
  state.columnUserFormatSaved = {};
  state.columnFormatSuggestions = {};
  state.formatSuggestionSeq = 0;
  state.userColumnConfigSaved = false;
  state.uploadPreviewReady = false;
  state.activeColumn = null;
  state.validationDone = false;
  _currentProblemsTotal = 0;
  _pendingCellNav = null;
  const bulkBar = document.getElementById('bulk-action-bar');
  if (bulkBar) bulkBar.hidden = true;
  const checkAll = document.getElementById('check-all-problems');
  if (checkAll) checkAll.checked = false;

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
  if (_previewScrollTopEl) _previewScrollTopEl.hidden = true;
  if (_previewScrollTopInnerEl) _previewScrollTopInnerEl.style.width = '0px';
  document.getElementById('preview-header').innerHTML = '';
  document.getElementById('preview-body').innerHTML = '';
  const colNav = _getColumnNavEl();
  if (colNav) {
    colNav.innerHTML = '';
    colNav.removeAttribute('aria-busy');
  }
  const sampleSel = document.getElementById('sample-row-select');
  if (sampleSel) {
    sampleSel.innerHTML = '';
    sampleSel.disabled = true;
  }
  state.previewDataRows = null;
  state.sampleRowIndex = 0;
  _updateSampleLinePickerVisibility();
  document.getElementById('column-config-panel').hidden = true;
  _hideFormatSuggestion();
  document.getElementById('config-summary').hidden = true;
  document.getElementById('cfg-required').checked = false;
  document.getElementById('cfg-content-type').value = '';
  _syncFormatPresetOptions('');
  document.getElementById('cfg-regex').value = '';
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

  // Reset step buttons (scope: Tablerreur step nav only)
  ['configure','fixes','validate','results'].forEach(step => {
    const btn = document.querySelector(`#step-nav [data-step="${step}"]`);
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
    const sel = document.getElementById('sample-row-select');
    if (sel && !sel.disabled && rowIdx >= 0 && rowIdx < sel.options.length) {
      state.sampleRowIndex = rowIdx;
      sel.value = String(rowIdx);
      _buildColumnNavList(state.columns);
    }
    _highlightCell(rowIdx, colName);
  } else {
    _pendingCellNav = { rowIdx, colName };
    goToStep('configure');
  }
}

/** Scroll et flash sur le <td> ciblé dans le tableau d'aperçu. */
function _highlightCell(rowIdx, colName) {
  const det = document.getElementById('configure-full-preview-details');
  if (det) det.open = true;
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
// Rendu des caractères spéciaux invisibles — toggle "¶ Caractères spéciaux"
// ---------------------------------------------------------------------------

/**
 * Converts invisible/ambiguous characters in `text` to visible HTML spans.
 * Must be called with raw cell text (before any HTML escaping).
 */
function renderVisibleChars(text) {
  if (text == null) return '';
  // Escape HTML first so that < > & in data are safe
  let html = esc(String(text));

  // Zero-width and BOM characters (most invisible — render first)
  html = html.replace(/\u200B/g, '<span class="char-zwsp">[ZWS]</span>');
  html = html.replace(/\u200D/g, '<span class="char-zwsp">[ZWJ]</span>');
  html = html.replace(/\u200C/g, '<span class="char-zwsp">[ZWNJ]</span>');
  html = html.replace(/\uFEFF/g, '<span class="char-bom">[BOM]</span>');
  html = html.replace(/\u00AD/g, '<span class="char-shy">[SHY]</span>');

  // NBSP (non-breaking space)
  html = html.replace(/\u00A0/g, '<span class="char-nbsp">⍽</span>');

  // Tabs
  html = html.replace(/\t/g, '<span class="char-tab">→</span>');

  // Line endings (CR before LF to avoid double-marking \r\n)
  html = html.replace(/\r/g, '<span class="char-newline">[CR]</span>');
  html = html.replace(/\n/g, '<span class="char-newline">↵</span>');

  // Leading spaces
  html = html.replace(/^( +)/, m => '<span class="char-space">' + '·'.repeat(m.length) + '</span>');

  // Trailing spaces
  html = html.replace(/( +)$/, m => '<span class="char-space">' + '·'.repeat(m.length) + '</span>');

  // Multiple consecutive spaces in the middle
  html = html.replace(/ {2,}/g, m => '<span class="char-space-multi">' + '·'.repeat(m.length) + '</span>');

  return html;
}

/**
 * Plain-text version of renderVisibleChars — for use in tooltip title attributes.
 */
function renderVisibleCharsText(text) {
  if (text == null) return '';
  let t = String(text);
  t = t.replace(/\u200B/g, '[ZWS]');
  t = t.replace(/\u200D/g, '[ZWJ]');
  t = t.replace(/\u200C/g, '[ZWNJ]');
  t = t.replace(/\uFEFF/g, '[BOM]');
  t = t.replace(/\u00AD/g, '[SHY]');
  t = t.replace(/\u00A0/g, '⍽');
  t = t.replace(/\t/g, '→');
  t = t.replace(/\r/g, '[CR]');
  t = t.replace(/\n/g, '↵');
  t = t.replace(/^( +)/, m => '·'.repeat(m.length));
  t = t.replace(/( +)$/, m => '·'.repeat(m.length));
  t = t.replace(/ {2,}/g, m => '·'.repeat(m.length));
  return t;
}

/** Toggle the special-chars display mode; syncs both toggle buttons. */
function toggleSpecialChars() {
  state.showSpecialChars = !state.showSpecialChars;
  _syncSpecialCharsButtons();
  _setUxPref('show_special_chars', state.showSpecialChars);
  _applySpecialCharsToPreview();
  if (state.previewDataRows && state.previewDataRows.length && state.showSampleValues) {
    _buildColumnNavList(state.columns);
  }
  // Re-render problems table if currently visible (to update the Valeur column)
  if (state.currentStep === 'results') loadProblems(state.currentPage);
}

/** Re-renders all preview table cells according to the current showSpecialChars state. */
function _applySpecialCharsToPreview() {
  document.querySelectorAll('#preview-body td').forEach(td => {
    const raw = td.dataset.rawText;
    if (raw === undefined) return;
    if (state.showSpecialChars) {
      td.innerHTML = renderVisibleChars(raw);
    } else {
      td.textContent = raw;
    }
  });
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

    _markUserColumnConfigSaved();

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
      if (data.user_overrides) {
        state.columnUserSaved = { ...state.columnUserSaved, ...data.user_overrides };
      }
      if (data.user_format_overrides) {
        state.columnUserFormatSaved = {
          ...state.columnUserFormatSaved,
          ...data.user_format_overrides,
        };
      }
    }
  } catch (_) { /* non-bloquant */ }
}

/** Affiche un toast temporaire (4 s). type: 'success' | 'warning' | 'error' */
let _toastTimer = null;
/** Handler document pour fermer le toast au clic extérieur (référence pour removeEventListener). */
let _toastOutsideHandler = null;

function _dismissToast() {
  if (_toastTimer != null) {
    clearTimeout(_toastTimer);
    _toastTimer = null;
  }
  if (_toastOutsideHandler) {
    document.removeEventListener('pointerdown', _toastOutsideHandler, true);
    _toastOutsideHandler = null;
  }
  const el = document.getElementById('template-toast');
  if (el) {
    el.style.animation = 'none';
    el.hidden = true;
    el.style.animation = '';
  }
}

/** Après affichage du toast : le prochain clic en dehors le ferme (le clic d’ouverture est ignoré via setTimeout 0). */
function _bindToastOutsideClose() {
  if (_toastOutsideHandler) {
    document.removeEventListener('pointerdown', _toastOutsideHandler, true);
    _toastOutsideHandler = null;
  }
  setTimeout(() => {
    const el = document.getElementById('template-toast');
    if (!el || el.hidden) return;
    _toastOutsideHandler = (e) => {
      if (el.contains(e.target)) return;
      _dismissToast();
    };
    document.addEventListener('pointerdown', _toastOutsideHandler, true);
  }, 0);
}

function _showToast(message, type, durationMs = 4000) {
  const el = document.getElementById('template-toast');
  if (!el) return;

  _dismissToast();
  el.textContent = message;
  el.className = `template-toast toast-${type}`;
  el.hidden = false;

  _toastTimer = setTimeout(_dismissToast, durationMs);
  _bindToastOutsideClose();
}

/**
 * Toast avec lien "Re-valider" cliquable pour inciter à re-valider après édition.
 */
function _showToastWithRevalidateLink(message) {
  const el = document.getElementById('template-toast');
  if (!el) return;
  _dismissToast();
  el.innerHTML = `${esc(message)} <button onclick="revalidate()" style="background:none;border:none;color:inherit;font-weight:700;text-decoration:underline;cursor:pointer;font-size:inherit;">Re-valider →</button>`;
  el.className = 'template-toast toast-success';
  el.hidden = false;
  _toastTimer = setTimeout(_dismissToast, 6000);
  _bindToastOutsideClose();
}

/** Affiche l'aide des principaux raccourcis clavier (bouton ? ou touche ? hors champ de saisie). */
function showShortcutsHelp() {
  const mapala = document.getElementById('app-mapala');
  if (mapala && !mapala.hidden) {
    _showToast(
      [
        'Raccourcis — Mapala',
        'Les raccourcis détaillés dépendent de l’étape Mapala ouverte.',
        'Retour à Tablerreur : cliquez l’onglet « Tablerreur » ou Alt+1 (si l’étape est disponible).',
      ].join('\n'),
      'info',
      8000
    );
    return;
  }
  _showToast(
    [
      'Raccourcis — Tablerreur',
      'Ctrl/Cmd + O : ouvrir un fichier',
      'Ctrl/Cmd + Entrée : action principale de l’étape (ex. téléverser, résumé config)',
      'Alt + 1 à 5 : aller à une étape déjà débloquée',
      'Ctrl/Cmd + Z : annuler une correction (Configurer / Correctifs)',
      'Ctrl/Cmd + Maj + Z : rétablir',
      '? ou Maj + / : afficher cette aide (hors champ de texte)',
    ].join('\n'),
    'info',
    10000
  );
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
// Curation — édition in-place des cellules du tableau d'aperçu
// ---------------------------------------------------------------------------

/** Nombre de cellules modifiées manuellement depuis la dernière validation. */
let _manualEditsCount = 0;

/**
 * Active le mode édition sur une cellule <td> du tableau d'aperçu.
 * Appelé par dblclick.
 */
function startCellEdit(td) {
  if (td.classList.contains('editing')) return;
  const row = parseInt(td.dataset.row);
  const col = td.dataset.col;
  if (!col || isNaN(row)) return;

  const currentValue = td.dataset.rawText ?? td.textContent;

  td.classList.add('editing');
  const input = document.createElement('input');
  input.type = 'text';
  input.value = currentValue;
  input.className = 'cell-edit-input';

  td.textContent = '';
  td.appendChild(input);
  input.focus();
  input.select();

  async function save() {
    const newValue = input.value;
    td.classList.remove('editing');
    td.textContent = newValue;
    td.dataset.rawText = newValue;

    if (state.showSpecialChars) {
      td.innerHTML = renderVisibleChars(newValue);
    }

    if (newValue !== currentValue && state.jobId) {
      try {
        const resp = await fetch(`/api/jobs/${state.jobId}/edit-cell`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ row, column: col, value: newValue }),
        });
        if (resp.ok) {
          td.classList.add('cell-edited');
          _updatePreviewDataCell(row, col, newValue, { markEdited: true });
          _invalidateFormatSuggestionCache(col);
          _refreshOpenColumnAfterDataMutation(col);
          _manualEditsCount++;
          _showCellsEditedBanner();
          await updateUndoRedoButtons();
        }
      } catch (_) { /* non-bloquant */ }
    }
  }

  function cancel() {
    td.classList.remove('editing');
    td.textContent = currentValue;
    td.dataset.rawText = currentValue;
    if (state.showSpecialChars) {
      td.innerHTML = renderVisibleChars(currentValue);
    }
  }

  input.addEventListener('blur', save);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
    if (e.key === 'Escape') { input.removeEventListener('blur', save); cancel(); }
  });
}

/** Affiche le bandeau "Des cellules ont été modifiées". */
function _showCellsEditedBanner() {
  const banner = document.getElementById('cells-edited-banner');
  if (banner) banner.hidden = false;
}

/** Masque le bandeau de modification. */
function _hideCellsEditedBanner() {
  const banner = document.getElementById('cells-edited-banner');
  if (banner) banner.hidden = true;
  _manualEditsCount = 0;
}

/** Activer le double-clic sur les cellules du tableau d'aperçu. */
document.getElementById('preview-body')?.addEventListener('dblclick', (e) => {
  const td = e.target.closest('td');
  if (td && td.closest('#preview-body')) {
    startCellEdit(td);
  }
});

// ---------------------------------------------------------------------------
// Re-validation après éditions manuelles
// ---------------------------------------------------------------------------

/**
 * Re-lance la validation sur le DataFrame actuel.
 * Met à jour la liste des problèmes si on est à l'étape Résultats.
 */
async function revalidate() {
  if (!state.jobId) return;
  const oldTotal = _currentProblemsTotal;
  const btn = document.getElementById('btn-revalidate');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Validation…'; }

  try {
    const resp = await fetch(`/api/jobs/${state.jobId}/revalidate`, { method: 'POST' });
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || 'Erreur de re-validation');
    }
    const data = await resp.json();
    const résumé = data['résumé'] || {};
    const newTotal = résumé['total'] ?? 0;
    _applyRuleFailAndExportWarnings(data);

    state.validationDone = true;
    _hideCellsEditedBanner();

    // Update summary counters if present
    const sumErrors = document.getElementById('sum-errors');
    if (sumErrors) sumErrors.textContent = résumé['erreurs'] ?? 0;
    const sumWarnings = document.getElementById('sum-warnings');
    if (sumWarnings) sumWarnings.textContent = résumé['avertissements'] ?? 0;
    const sumSuspicions = document.getElementById('sum-suspicions');
    if (sumSuspicions) sumSuspicions.textContent = résumé['suspicions'] ?? 0;
    const sumTotal = document.getElementById('sum-total');
    if (sumTotal) sumTotal.textContent = newTotal;

    const msg = newTotal === 0
      ? '✓ Re-validation terminée : aucun problème restant'
      : `✓ Re-validation terminée : ${newTotal} problème${newTotal > 1 ? 's' : ''} restant${newTotal > 1 ? 's' : ''} (était ${oldTotal})`;
    _showToast(msg, newTotal < oldTotal ? 'success' : 'warning');

    // Refresh problems table if at results step
    if (state.currentStep === 'results') {
      loadProblems(1);
    }
    // Refresh cell highlights if at configure step
    if (state.currentStep === 'configure') {
      _applyCellIssueHighlights();
    }
  } catch (err) {
    _showToast('Erreur : ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔄 Re-valider'; }
  }
}

// ---------------------------------------------------------------------------
// Raccourcis clavier globaux
// ---------------------------------------------------------------------------
function _isEditableTarget(target) {
  if (!target) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
}

function _isTablerreurVisible() {
  const root = document.getElementById('app-tablerreur');
  return !!root && !root.hidden;
}

function _goToStepFromShortcut(stepNumber) {
  const steps = ['upload', 'configure', 'fixes', 'validate', 'results'];
  const step = steps[stepNumber - 1];
  if (!step) return;
  const btn = document.querySelector(`#step-nav [data-step="${step}"]`);
  if (btn && !btn.disabled) {
    goToStep(step);
  }
}

function _runPrimaryActionShortcut() {
  switch (state.currentStep) {
    case 'upload':
      void uploadContinueToConfigure();
      break;
    case 'configure': {
      const summary = document.getElementById('config-summary');
      if (summary && !summary.hidden) {
        configureDone();
      } else {
        showConfigSummary();
      }
      break;
    }
    case 'fixes':
      applyFixes();
      break;
    case 'validate': {
      const btnResults = document.querySelector('#step-nav [data-step="results"]');
      if (btnResults && !btnResults.disabled) {
        goToStep('results');
      }
      break;
    }
    case 'results':
      revalidate();
      break;
    default:
      break;
  }
}

document.addEventListener('keydown', (e) => {
  if (!_isTablerreurVisible()) return;

  const key = e.key || '';
  const lower = key.toLowerCase();
  const editable = _isEditableTarget(e.target);
  const mod = e.ctrlKey || e.metaKey;

  // "?" -> aide raccourcis (hors champ de saisie)
  if (!editable && (key === '?' || (key === '/' && e.shiftKey))) {
    e.preventDefault();
    showShortcutsHelp();
    return;
  }

  // Alt + 1..5 -> navigation rapide entre étapes déjà disponibles
  if (!editable && e.altKey && !mod && /^[1-5]$/.test(key)) {
    e.preventDefault();
    _goToStepFromShortcut(parseInt(key, 10));
    return;
  }

  // Ctrl/Cmd + O -> ouvrir un fichier
  if (mod && !e.altKey && lower === 'o') {
    e.preventDefault();
    fileInput?.click();
    return;
  }

  // Ctrl/Cmd + Enter -> action principale de l'étape (hors saisie)
  if (!editable && mod && !e.altKey && key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    _runPrimaryActionShortcut();
    return;
  }

  if (editable || !mod) return;
  if (state.currentStep !== 'fixes' && state.currentStep !== 'configure') return;

  // Undo/redo en Configurer / Correctifs
  if (lower === 'z' && !e.shiftKey) {
    e.preventDefault();
    undoFix();
  } else if ((lower === 'z' && e.shiftKey) || lower === 'y') {
    e.preventDefault();
    redoFix();
  }
});
