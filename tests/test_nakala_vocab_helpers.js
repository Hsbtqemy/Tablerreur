const test = require('node:test');
const assert = require('node:assert/strict');

const {
  resolveNakalaVocabularySelection,
} = require('../src/spreadsheet_qa/web/static/nakala_vocab_helpers.js');

test('resolveNakalaVocabularySelection keeps the full vocabulary when no subset is defined', () => {
  assert.deepEqual(
    resolveNakalaVocabularySelection({
      vocabValues: ['fra', 'eng', 'deu'],
      selectedValues: null,
    }),
    {
      normalizedValues: ['fra', 'eng', 'deu'],
      effectiveSelectedValues: null,
      selectedCount: 3,
      countMessage: '3 valeurs autorisées via le vocabulaire NAKALA',
    }
  );
});

test('resolveNakalaVocabularySelection preserves only known user-selected values', () => {
  assert.deepEqual(
    resolveNakalaVocabularySelection({
      vocabValues: ['CC-BY-4.0', 'CC0-1.0', 'Etalab-2.0'],
      selectedValues: ['CC-BY-4.0', 'unknown'],
    }),
    {
      normalizedValues: ['CC-BY-4.0', 'CC0-1.0', 'Etalab-2.0'],
      effectiveSelectedValues: ['CC-BY-4.0'],
      selectedCount: 1,
      countMessage: '1 valeur sélectionnée par l\u2019utilisateur (3 valeurs autorisées par le modèle NAKALA)',
    }
  );
});

test('resolveNakalaVocabularySelection falls back to the full vocabulary when subset becomes empty', () => {
  assert.deepEqual(
    resolveNakalaVocabularySelection({
      vocabValues: ['http://purl.org/coar/resource_type/c_c513'],
      selectedValues: ['legacy-missing-value'],
    }),
    {
      normalizedValues: ['http://purl.org/coar/resource_type/c_c513'],
      effectiveSelectedValues: null,
      selectedCount: 1,
      countMessage: '1 valeur autorisée via le vocabulaire NAKALA',
    }
  );
});
