const test = require('node:test');
const assert = require('node:assert/strict');

const {
  canTargetPreviewRow,
  buildPreviewLimitMessage,
  makePendingCellNavigation,
} = require('../src/spreadsheet_qa/web/static/curation_helpers.js');

test('canTargetPreviewRow respects the 30-row preview window', () => {
  assert.equal(canTargetPreviewRow(1), true);
  assert.equal(canTargetPreviewRow(30), true);
  assert.equal(canTargetPreviewRow(0), false);
  assert.equal(canTargetPreviewRow(31), false);
});

test('buildPreviewLimitMessage explains edit fallback for rows outside preview', () => {
  const msg = buildPreviewLimitMessage(42, { mode: 'edit' });
  assert.match(msg, /Ligne 42 hors aperçu/);
  assert.match(msg, /export de travail/);
});

test('makePendingCellNavigation stores a 0-based row index and edit flag', () => {
  assert.deepEqual(
    makePendingCellNavigation(5, 'titre', { startEdit: true }),
    { rowIdx: 4, colName: 'titre', startEdit: true }
  );
  assert.deepEqual(
    makePendingCellNavigation(2, 'annee'),
    { rowIdx: 1, colName: 'annee', startEdit: false }
  );
});
