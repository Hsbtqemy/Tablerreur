(function initTablerreurNakalaVocabHelpers(globalScope) {
  'use strict';

  function formatCountLabel(count) {
    const n = Number.isInteger(count) ? count : 0;
    return `${n} valeur${n > 1 ? 's' : ''}`;
  }

  function resolveNakalaVocabularySelection({
    vocabValues = [],
    selectedValues = null,
  } = {}) {
    const normalizedValues = Array.isArray(vocabValues)
      ? vocabValues.map((value) => String(value || '').trim()).filter(Boolean)
      : [];
    const knownValues = new Set(normalizedValues);
    const normalizedSelectedValues = Array.isArray(selectedValues) && selectedValues.length > 0
      ? selectedValues
          .map((value) => String(value || '').trim())
          .filter((value) => knownValues.has(value))
      : null;
    const effectiveSelectedValues = normalizedSelectedValues && normalizedSelectedValues.length > 0
      ? normalizedSelectedValues
      : null;
    const selectedCount = effectiveSelectedValues ? effectiveSelectedValues.length : normalizedValues.length;
    const countMessage = effectiveSelectedValues && selectedCount !== normalizedValues.length
      ? `${formatCountLabel(selectedCount)} sélectionnée${selectedCount > 1 ? 's' : ''} par l\u2019utilisateur (${formatCountLabel(normalizedValues.length)} autorisées par le modèle NAKALA)`
      : `${formatCountLabel(selectedCount)} autorisée${selectedCount > 1 ? 's' : ''} via le vocabulaire NAKALA`;

    return {
      normalizedValues,
      effectiveSelectedValues,
      selectedCount,
      countMessage,
    };
  }

  const api = {
    resolveNakalaVocabularySelection,
  };

  globalScope.TablerreurNakalaVocabHelpers = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
