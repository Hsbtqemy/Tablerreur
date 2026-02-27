/* Mapala — Logique frontend (mapping de tableurs) */
'use strict';

// ---------------------------------------------------------------------------
// État global Mapala
// ---------------------------------------------------------------------------
const mapalaState = {
  jobId: null,
  templateSheets: [],
  sourceSheets: [],
  templateColumns: [],
  sourceColumns: [],
  currentStep: 'upload',
};

// ---------------------------------------------------------------------------
// Navigation entre étapes Mapala
// ---------------------------------------------------------------------------
function mapalaGoToStep(step) {
  document.querySelectorAll('#app-mapala .step-section').forEach(el => el.hidden = true);
  document.querySelectorAll('#mapala-step-nav .step-btn').forEach(el => el.classList.remove('active'));

  const section = document.getElementById('mapala-step-' + step);
  if (section) section.hidden = false;

  const btn = document.querySelector(`#mapala-step-nav [data-step="${step}"]`);
  if (btn) btn.classList.add('active');

  mapalaState.currentStep = step;
}

function mapalaEnableStep(step) {
  const btn = document.querySelector(`#mapala-step-nav [data-step="${step}"]`);
  if (btn) btn.disabled = false;
}

// ---------------------------------------------------------------------------
// Gestion des fichiers (sélection + drag-and-drop)
// ---------------------------------------------------------------------------
function mapalaFileSelected(role) {
  const input = document.getElementById(`mapala-${role}-file`);
  const info = document.getElementById(`mapala-${role}-info`);
  const nameEl = document.getElementById(`mapala-${role}-name`);
  if (input && input.files.length) {
    const name = input.files[0].name;
    if (info) info.hidden = false;
    if (nameEl) nameEl.textContent = name;
  }
}

function malalaClearFile(role) {
  const input = document.getElementById(`mapala-${role}-file`);
  const info = document.getElementById(`mapala-${role}-info`);
  const sheetRow = document.getElementById(`mapala-${role}-sheet-row`);
  if (input) input.value = '';
  if (info) info.hidden = true;
  if (sheetRow) sheetRow.hidden = true;
}

function mapalaHandleDrop(event, role) {
  event.preventDefault();
  const files = event.dataTransfer?.files;
  if (!files || !files.length) return;
  const input = document.getElementById(`mapala-${role}-file`);
  if (!input) return;
  // Assign dropped file
  const dt = new DataTransfer();
  dt.items.add(files[0]);
  input.files = dt.files;
  mapalaFileSelected(role);
}

// ---------------------------------------------------------------------------
// ÉTAPE 1 : upload
// ---------------------------------------------------------------------------
async function mapalaUpload() {
  const templateInput = document.getElementById('mapala-template-file');
  const sourceInput = document.getElementById('mapala-source-file');
  const errEl = document.getElementById('mapala-upload-error');
  const progressEl = document.getElementById('mapala-upload-progress');

  if (errEl) errEl.hidden = true;

  if (!templateInput?.files?.length) {
    _mapalaShowError(errEl, 'Veuillez sélectionner un fichier template.');
    return;
  }
  if (!sourceInput?.files?.length) {
    _mapalaShowError(errEl, 'Veuillez sélectionner un fichier source.');
    return;
  }

  if (progressEl) progressEl.hidden = false;

  const formData = new FormData();
  formData.append('template_file', templateInput.files[0]);
  formData.append('source_file', sourceInput.files[0]);

  try {
    const resp = await fetch('/api/mapala/upload', { method: 'POST', body: formData });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Erreur upload');

    mapalaState.jobId = data.job_id;
    mapalaState.templateSheets = data.template_sheets || [];
    mapalaState.sourceSheets = data.source_sheets || [];

    _malaFillSheetSelect('mapala-template-sheet', mapalaState.templateSheets, 'mapala-template-sheet-row');
    _malaFillSheetSelect('mapala-source-sheet', mapalaState.sourceSheets, 'mapala-source-sheet-row');

    // Auto-charger l'aperçu
    await mapalaLoadPreview();

  } catch (e) {
    _mapalaShowError(errEl, String(e.message || e));
  } finally {
    if (progressEl) progressEl.hidden = true;
  }
}

function _malaFillSheetSelect(selectId, sheets, rowId) {
  const sel = document.getElementById(selectId);
  const row = document.getElementById(rowId);
  if (!sel) return;
  sel.innerHTML = sheets.map(s => `<option value="${_esc(s)}">${_esc(s)}</option>`).join('');
  if (row) row.hidden = sheets.length <= 1;
}

// ---------------------------------------------------------------------------
// ÉTAPE 2 : aperçu + génération du mapping
// ---------------------------------------------------------------------------
async function mapalaLoadPreview() {
  if (!mapalaState.jobId) return;

  const templateSheet = document.getElementById('mapala-template-sheet')?.value || null;
  const sourceSheet = document.getElementById('mapala-source-sheet')?.value || null;
  const errEl = document.getElementById('mapala-upload-error');

  try {
    const resp = await fetch('/api/mapala/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: mapalaState.jobId,
        template_sheet: templateSheet,
        source_sheet: sourceSheet,
        rows: 30,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Erreur aperçu');

    mapalaState.templateColumns = data.template_columns || [];
    mapalaState.sourceColumns = data.source_columns || [];

    _mapalaRenderPreviewTable('mapala-template-thead', 'mapala-template-tbody', data.template_columns, data.template_preview);
    _mapalaRenderPreviewTable('mapala-source-thead', 'mapala-source-tbody', data.source_columns, data.source_preview);

    _mapalaGenerateMappingRows(data.template_columns, data.source_columns);

    mapalaEnableStep('mapping');
    mapalaGoToStep('mapping');

  } catch (e) {
    _mapalaShowError(errEl, String(e.message || e));
  }
}

function _mapalaRenderPreviewTable(theadId, tbodyId, columns, rows) {
  const thead = document.getElementById(theadId);
  const tbody = document.getElementById(tbodyId);
  if (!thead || !tbody) return;

  thead.innerHTML = columns.map(c => `<th>${_esc(c)}</th>`).join('');
  tbody.innerHTML = rows.map(row =>
    `<tr>${row.map(cell => `<td>${_esc(cell)}</td>`).join('')}</tr>`
  ).join('');
}

function _mapalaGenerateMappingRows(templateCols, sourceCols) {
  const container = document.getElementById('mapala-mapping-config');
  if (!container) return;

  const sourceOptions = ['<option value="">— Non mappé —</option>']
    .concat(sourceCols.map(c => `<option value="${_esc(c)}">${_esc(c)}</option>`))
    .join('');

  container.innerHTML = templateCols.map((col, idx) => {
    // Auto-match : cherche une colonne source au nom identique ou proche
    const autoMatch = sourceCols.find(s => s.toLowerCase() === col.toLowerCase()) || '';
    return `
    <div class="mapala-mapping-row" data-template-col="${_esc(col)}" id="mapala-row-${idx}">
      <span class="mapala-col-name" title="${_esc(col)}">${_esc(col)}</span>
      <span class="mapala-arrow">←</span>
      <div class="mapala-source-area" id="mapala-source-area-${idx}">
        <select class="input-sm mapala-source-select" id="mapala-sel-${idx}"
                onchange="mapalaOnSourceChange(${idx})">
          ${sourceCols.map(c =>
            `<option value="${_esc(c)}"${c === autoMatch ? ' selected' : ''}>${_esc(c)}</option>`
          ).join('')}
          <option value=""${!autoMatch ? ' selected' : ''}>— Non mappé —</option>
        </select>
        <button class="mapala-btn-concat" onclick="mapalaAddConcat(${idx})" title="Concaténer plusieurs colonnes">+</button>
      </div>
      <span class="mapala-mode-fixed-label">ou</span>
      <input type="text" class="input-sm mapala-fixed-input" id="mapala-fixed-${idx}"
             placeholder="Valeur fixe" title="Valeur fixe (laissez vide si inutilisé)" />
    </div>`;
  }).join('');
}

function mapalaOnSourceChange(idx) {
  // Si on choisit une source, efface la valeur fixe
  const sel = document.getElementById(`mapala-sel-${idx}`);
  const fixed = document.getElementById(`mapala-fixed-${idx}`);
  if (sel && sel.value && fixed) fixed.value = '';
}

// Mode concaténation : ajouter un second select source
function mapalaAddConcat(idx) {
  const area = document.getElementById(`mapala-source-area-${idx}`);
  if (!area) return;

  const sourceCols = mapalaState.sourceColumns;
  const sourceOptions = sourceCols.map(c => `<option value="${_esc(c)}">${_esc(c)}</option>`).join('');

  // Remplace le contenu par le mode concat
  area.innerHTML = `
    <div class="mapala-concat-container" id="mapala-concat-${idx}">
      <div class="mapala-concat-row" id="mapala-concat-sources-${idx}">
        <select class="input-sm mapala-source-select mapala-concat-sel" data-concat-idx="0">
          <option value="">— Non mappé —</option>
          ${sourceOptions}
        </select>
        <button class="mapala-btn-concat" onclick="mapalaAddConcatSource(${idx})" title="Ajouter une colonne">+</button>
        <button class="mapala-btn-remove-concat" onclick="mapalaRemoveConcat(${idx})" title="Revenir au mode simple">✕</button>
      </div>
      <div class="mapala-separator-row">
        <label>Séparateur :</label>
        <input type="text" class="input-sm mapala-separator-input" id="mapala-sep-${idx}" value=" " />
      </div>
    </div>`;
}

function mapalaAddConcatSource(idx) {
  const sourcesContainer = document.getElementById(`mapala-concat-sources-${idx}`);
  if (!sourcesContainer) return;
  const sourceCols = mapalaState.sourceColumns;
  const sourceOptions = sourceCols.map(c => `<option value="${_esc(c)}">${_esc(c)}</option>`).join('');
  const newSel = document.createElement('select');
  newSel.className = 'input-sm mapala-source-select mapala-concat-sel';
  newSel.setAttribute('data-concat-idx', sourcesContainer.querySelectorAll('.mapala-concat-sel').length);
  newSel.innerHTML = `<option value="">— Non mappé —</option>${sourceOptions}`;
  // Insérer avant le bouton +
  const btnAdd = sourcesContainer.querySelector('.mapala-btn-concat');
  sourcesContainer.insertBefore(newSel, btnAdd);
}

function mapalaRemoveConcat(idx) {
  // Revenir au mode simple
  const area = document.getElementById(`mapala-source-area-${idx}`);
  if (!area) return;
  const sourceCols = mapalaState.sourceColumns;
  const sourceOptions = sourceCols.map(c => `<option value="${_esc(c)}">${_esc(c)}</option>`).join('');
  area.innerHTML = `
    <select class="input-sm mapala-source-select" id="mapala-sel-${idx}"
            onchange="mapalaOnSourceChange(${idx})">
      <option value="">— Non mappé —</option>
      ${sourceOptions}
    </select>
    <button class="mapala-btn-concat" onclick="mapalaAddConcat(${idx})" title="Concaténer plusieurs colonnes">+</button>`;
}

// ---------------------------------------------------------------------------
// ÉTAPE 3 : build
// ---------------------------------------------------------------------------
async function mapalaBuild() {
  if (!mapalaState.jobId) return;

  const errEl = document.getElementById('mapala-build-error');
  const progressEl = document.getElementById('mapala-build-progress');
  if (errEl) errEl.hidden = true;
  if (progressEl) progressEl.hidden = false;

  const templateSheet = document.getElementById('mapala-template-sheet')?.value || null;
  const sourceSheet = document.getElementById('mapala-source-sheet')?.value || null;
  const outputFormat = document.getElementById('mapala-output-format')?.value || 'xlsx';

  const mappings = _mapalaCollectMappings();

  try {
    const resp = await fetch('/api/mapala/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: mapalaState.jobId,
        template_sheet: templateSheet,
        source_sheet: sourceSheet,
        mappings,
        output_format: outputFormat,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Erreur construction');

    document.getElementById('mapala-rows-count').textContent = data.rows_mapped ?? 0;
    document.getElementById('mapala-cols-count').textContent = data.columns_mapped ?? 0;

    await _mapalaLoadResultPreview();

    mapalaEnableStep('result');
    mapalaGoToStep('result');

  } catch (e) {
    _mapalaShowError(errEl, String(e.message || e));
  } finally {
    if (progressEl) progressEl.hidden = true;
  }
}

function _mapalaCollectMappings() {
  const container = document.getElementById('mapala-mapping-config');
  if (!container) return [];

  const rows = container.querySelectorAll('.mapala-mapping-row');
  const mappings = [];

  rows.forEach((row, idx) => {
    const templateCol = row.getAttribute('data-template-col') || '';
    if (!templateCol) return;

    // Valeur fixe (prioritaire si remplie)
    const fixedInput = document.getElementById(`mapala-fixed-${idx}`);
    const fixedVal = fixedInput?.value?.trim() || '';
    if (fixedVal) {
      mappings.push({ template_col: templateCol, value: fixedVal });
      return;
    }

    // Mode concat ?
    const concatContainer = document.getElementById(`mapala-concat-${idx}`);
    if (concatContainer) {
      const sels = concatContainer.querySelectorAll('.mapala-concat-sel');
      const source_cols = Array.from(sels).map(s => s.value).filter(Boolean);
      if (!source_cols.length) return;
      const sepInput = document.getElementById(`mapala-sep-${idx}`);
      const separator = sepInput?.value ?? ' ';
      mappings.push({ template_col: templateCol, source_cols, separator });
      return;
    }

    // Mode simple
    const sel = document.getElementById(`mapala-sel-${idx}`);
    const sourceCol = sel?.value || '';
    if (!sourceCol) return;
    mappings.push({ template_col: templateCol, source_col: sourceCol });
  });

  return mappings;
}

async function _mapalaLoadResultPreview() {
  if (!mapalaState.jobId) return;

  // Charge un aperçu du résultat en re-appelant preview sur le job
  // Pour ne pas surcharger, on utilise les données déjà connues (templateColumns)
  // et on télécharge l'aperçu via un preview rapide
  try {
    const templateSheet = document.getElementById('mapala-template-sheet')?.value || null;
    const sourceSheet = document.getElementById('mapala-source-sheet')?.value || null;
    const resp = await fetch('/api/mapala/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: mapalaState.jobId,
        template_sheet: templateSheet,
        source_sheet: sourceSheet,
        rows: 10,
      }),
    });
    if (!resp.ok) return;
    const data = await resp.json();

    // Reconstitue un aperçu résultat simulé depuis les mappings
    const mappings = _mapalaCollectMappings();
    const previewRows = (data.source_preview || []).slice(0, 10).map(sourceRow => {
      const srcByCol = {};
      (data.source_columns || []).forEach((c, i) => { srcByCol[c] = sourceRow[i] || ''; });

      return mapalaState.templateColumns.map(tCol => {
        const m = mappings.find(x => x.template_col === tCol);
        if (!m) return '';
        if ('value' in m) return m.value;
        if (m.source_cols) {
          const sep = m.separator ?? ' ';
          return m.source_cols.map(sc => srcByCol[sc] || '').filter(Boolean).join(sep);
        }
        if (m.source_col) return srcByCol[m.source_col] || '';
        return '';
      });
    });

    _mapalaRenderPreviewTable('mapala-result-thead', 'mapala-result-tbody', mapalaState.templateColumns, previewRows);
  } catch (_) {
    // Aperçu non critique — on ignore les erreurs
  }
}

// ---------------------------------------------------------------------------
// Téléchargement
// ---------------------------------------------------------------------------
function mapalaDownload() {
  if (!mapalaState.jobId) return;
  window.location.href = `/api/mapala/jobs/${mapalaState.jobId}/download`;
}

// ---------------------------------------------------------------------------
// Valider avec Tablerreur
// ---------------------------------------------------------------------------
async function mapalaValidate() {
  if (!mapalaState.jobId) return;

  const errEl = document.getElementById('mapala-result-error');
  if (errEl) errEl.hidden = true;

  try {
    const resp = await fetch(`/api/mapala/jobs/${mapalaState.jobId}/validate`, { method: 'POST' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Erreur validation');

    const tablerreurJobId = data.tablerreur_job_id;
    if (!tablerreurJobId) throw new Error('Identifiant Tablerreur manquant');

    // Passer à l'onglet Tablerreur avec le job créé
    switchApp('tablerreur');

    // Charger le job dans Tablerreur (passe directement à l'étape Configurer)
    state.jobId = tablerreurJobId;
    state.currentStep = 'upload';

    // Demande le statut du job pour récupérer les métadonnées
    const jobResp = await fetch(`/api/jobs/${tablerreurJobId}`);
    if (jobResp.ok) {
      const jobData = await jobResp.json();
      state.filename = jobData.filename || 'mapala_resultat.xlsx';
      state.rows = jobData.rows || 0;
      state.cols = jobData.cols || 0;
      state.columns = jobData.columns || [];

      // Active les étapes Tablerreur
      ['configure', 'fixes', 'validate', 'results'].forEach(s => enableStep(s));
      goToStep('configure');
    }

  } catch (e) {
    _mapalaShowError(errEl, String(e.message || e));
  }
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------
function _mapalaShowError(el, msg) {
  if (!el) { console.error('[Mapala]', msg); return; }
  el.textContent = msg;
  el.hidden = false;
}

/** Échappe les caractères HTML (réutilise esc() de app.js si disponible). */
function _esc(str) {
  if (typeof esc === 'function') return esc(String(str ?? ''));
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
