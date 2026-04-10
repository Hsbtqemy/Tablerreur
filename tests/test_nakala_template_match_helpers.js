const test = require('node:test');
const assert = require('node:assert/strict');

const {
  getNakalaFieldLabel,
  normalizeTemplateColumnName,
  suggestTemplateFieldMappings,
} = require('../src/spreadsheet_qa/web/static/nakala_template_match_helpers.js');

test('normalizeTemplateColumnName strips accents and separators', () => {
  assert.equal(normalizeTemplateColumnName('Lang_Title'), 'lang title');
  assert.equal(normalizeTemplateColumnName('Éditeur principal'), 'editeur principal');
});

test('suggestTemplateFieldMappings proposes explicit NAKALA matches from common aliases', () => {
  const { suggestions } = suggestTemplateFieldMappings({
    availableColumns: ['title', 'language', 'creator_name', 'notes'],
    templateColumns: {
      'nakala:title': {},
      'nakala:creator': {},
      'dcterms:language': {},
    },
    requiredColumns: ['nakala:title', 'nakala:creator'],
    recommendedColumns: ['dcterms:language'],
  });

  assert.deepEqual(
    suggestions.map((entry) => [entry.sourceColumn, entry.targetField, entry.requirement]),
    [
      ['creator_name', 'nakala:creator', 'required'],
      ['title', 'nakala:title', 'required'],
      ['language', 'dcterms:language', 'recommended'],
    ]
  );
});

test('suggestTemplateFieldMappings prefers multilingual groups for title_fr and description_en', () => {
  const { suggestions } = suggestTemplateFieldMappings({
    availableColumns: ['title_fr', 'description_en'],
    templateColumns: {
      'nakala:title': {},
      'dcterms:description': {},
    },
    templateColumnGroups: {
      'nakala:title_*': {},
      'dcterms:description_*': {},
    },
    requiredColumns: ['nakala:title'],
    recommendedColumns: ['dcterms:description'],
  });

  assert.deepEqual(
    suggestions.map((entry) => [entry.sourceColumn, entry.targetField, entry.targetSource]),
    [
      ['description_en', 'dcterms:description_*', 'column_group'],
      ['title_fr', 'nakala:title_*', 'column_group'],
    ]
  );
});

test('suggestTemplateFieldMappings recognizes keyword and identifier motifs', () => {
  const { suggestions } = suggestTemplateFieldMappings({
    availableColumns: ['keywords_en_1', 'doi_2'],
    templateColumnGroups: {
      'keywords_*': {},
      'dcterms:identifier*': {},
    },
  });

  assert.deepEqual(
    suggestions.map((entry) => [entry.sourceColumn, entry.targetField]),
    [
      ['keywords_en_1', 'keywords_*'],
      ['doi_2', 'dcterms:identifier*'],
    ]
  );
});

test('suggestTemplateFieldMappings skips targets already present in the dataset', () => {
  const { suggestions } = suggestTemplateFieldMappings({
    availableColumns: ['nakala:title', 'title', 'language'],
    templateColumns: {
      'nakala:title': {},
      'dcterms:language': {},
    },
    requiredColumns: ['nakala:title'],
    recommendedColumns: ['dcterms:language'],
  });

  assert.deepEqual(
    suggestions.map((entry) => [entry.sourceColumn, entry.targetField]),
    [['language', 'dcterms:language']]
  );
});

test('suggestTemplateFieldMappings keeps manual columns informative but deprioritized', () => {
  const { suggestions } = suggestTemplateFieldMappings({
    availableColumns: ['title', 'main_title'],
    templateColumns: {
      'nakala:title': {},
    },
    requiredColumns: ['nakala:title'],
    userSavedColumns: {
      title: true,
    },
  });

  assert.equal(suggestions.length, 1);
  assert.equal(suggestions[0].sourceColumn, 'main_title');
  assert.equal(suggestions[0].userSaved, false);
});

test('getNakalaFieldLabel falls back to the field name when unknown', () => {
  assert.equal(getNakalaFieldLabel('nakala:title'), 'Titre NAKALA');
  assert.equal(getNakalaFieldLabel('nakala:title_*'), 'Titre multilingue');
  assert.equal(getNakalaFieldLabel('custom:field'), 'custom:field');
});
