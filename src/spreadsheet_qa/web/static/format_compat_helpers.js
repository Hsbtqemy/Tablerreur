(function initTablerreurFormatCompatHelpers(globalScope) {
  'use strict';

  function analyzeFormatPresetSelection({
    contentType = '',
    preferredValue = '',
    compatMap = {},
    optionValues = [],
  } = {}) {
    const preferred = String(preferredValue || '').trim();
    const allowedValues = Array.isArray(compatMap?.[contentType]) ? compatMap[contentType] : null;
    const allowed = allowedValues ? new Set(allowedValues) : null;
    const known = new Set((optionValues || []).map((value) => String(value || '').trim()).filter(Boolean));
    const hasPreferred = preferred.length > 0 && known.has(preferred);
    const isCompatible = !preferred || !allowed || allowed.has(preferred);
    const preserveIncompatible = hasPreferred && !isCompatible;

    return {
      allowedValues,
      hasPreferred,
      isCompatible,
      preserveIncompatible,
      effectiveValue: preserveIncompatible || isCompatible ? preferred : '',
    };
  }

  function buildIncompatiblePresetLabel(presetLabel, typeLabel) {
    const preset = String(presetLabel || '').trim() || 'Préréglage';
    const type = String(typeLabel || '').trim() || 'la nature actuelle';
    return `${preset} — incompatible avec « ${type} »`;
  }

  const api = {
    analyzeFormatPresetSelection,
    buildIncompatiblePresetLabel,
  };

  globalScope.TablerreurFormatCompatHelpers = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
