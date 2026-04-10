(function initTablerreurCurationHelpers(globalScope) {
  'use strict';

  function canTargetPreviewRow(row1based, maxPreviewRows = 30) {
    return Number.isInteger(row1based) && row1based >= 1 && row1based <= maxPreviewRows;
  }

  function buildPreviewLimitMessage(row1based, options = {}) {
    const maxPreviewRows = Number.isInteger(options.maxPreviewRows) ? options.maxPreviewRows : 30;
    const mode = options.mode === 'edit' ? 'edit' : 'navigate';
    const prefix = `Ligne ${row1based} hors aperçu (${maxPreviewRows} premières lignes).`;
    if (mode === 'edit') {
      return `${prefix} La correction ciblée n'est disponible que dans l'aperçu. Utilisez l'export de travail ou corrigez cette ligne dans le fichier source.`;
    }
    return `${prefix} La localisation directe n'est disponible que dans l'aperçu.`;
  }

  function makePendingCellNavigation(row1based, colName, options = {}) {
    return {
      rowIdx: row1based - 1,
      colName: String(colName || ''),
      startEdit: !!options.startEdit,
    };
  }

  const api = {
    canTargetPreviewRow,
    buildPreviewLimitMessage,
    makePendingCellNavigation,
  };

  globalScope.TablerreurCurationHelpers = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
