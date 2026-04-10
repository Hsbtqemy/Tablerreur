const test = require('node:test');
const assert = require('node:assert/strict');

const {
  analyzeFormatPresetSelection,
  buildIncompatiblePresetLabel,
} = require('../src/spreadsheet_qa/web/static/format_compat_helpers.js');

const compatMap = {
  date: ['year', 'iso_date', 'custom'],
  identifier: ['doi', 'isbn13', 'custom'],
};

const optionValues = ['year', 'iso_date', 'doi', 'isbn13', 'custom'];

test('analyzeFormatPresetSelection keeps a compatible preferred preset selected', () => {
  assert.deepEqual(
    analyzeFormatPresetSelection({
      contentType: 'date',
      preferredValue: 'iso_date',
      compatMap,
      optionValues,
    }),
    {
      allowedValues: ['year', 'iso_date', 'custom'],
      hasPreferred: true,
      isCompatible: true,
      preserveIncompatible: false,
      effectiveValue: 'iso_date',
    }
  );
});

test('analyzeFormatPresetSelection flags a known incompatible preset for preservation', () => {
  assert.deepEqual(
    analyzeFormatPresetSelection({
      contentType: 'date',
      preferredValue: 'doi',
      compatMap,
      optionValues,
    }),
    {
      allowedValues: ['year', 'iso_date', 'custom'],
      hasPreferred: true,
      isCompatible: false,
      preserveIncompatible: true,
      effectiveValue: 'doi',
    }
  );
});

test('analyzeFormatPresetSelection drops unknown presets instead of preserving them', () => {
  assert.deepEqual(
    analyzeFormatPresetSelection({
      contentType: 'date',
      preferredValue: 'legacy_preset',
      compatMap,
      optionValues,
    }),
    {
      allowedValues: ['year', 'iso_date', 'custom'],
      hasPreferred: false,
      isCompatible: false,
      preserveIncompatible: false,
      effectiveValue: '',
    }
  );
});

test('buildIncompatiblePresetLabel annotates the preset with the current type label', () => {
  assert.equal(
    buildIncompatiblePresetLabel('DOI', 'Date'),
    'DOI — incompatible avec « Date »'
  );
});
