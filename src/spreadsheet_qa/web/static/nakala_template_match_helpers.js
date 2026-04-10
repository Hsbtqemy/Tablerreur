(function initTablerreurNakalaTemplateMatchHelpers(globalScope) {
  'use strict';

  const TARGET_DEFINITIONS = Object.freeze({
    'nakala:type': {
      label: 'Type de ressource',
      aliases: ['type', 'resource_type', 'document_type', 'genre', 'type_ressource'],
    },
    'nakala:title': {
      label: 'Titre NAKALA',
      aliases: ['title', 'titre', 'main_title', 'resource_title'],
    },
    'nakala:title_*': {
      label: 'Titre multilingue',
      aliases: [
        'lang_title',
        'title_lang',
        { pattern: /^title [a-z]{2,3}$/, label: 'title_{lang}', score: 1 },
        { pattern: /^titre [a-z]{2,3}$/, label: 'titre_{lang}', score: 1 },
        { pattern: /^(translated|alternate|alt) title$/, label: 'translated_title', score: 0.97 },
      ],
    },
    'nakala:creator': {
      label: 'Créateur NAKALA',
      aliases: ['creator', 'author', 'auteur', 'creator_name', 'author_name', 'auteur_principal'],
    },
    'nakala:created': {
      label: 'Date de création',
      aliases: ['created', 'date_created', 'creation_date', 'year', 'annee', 'date_creation'],
    },
    'nakala:license': {
      label: 'Licence NAKALA',
      aliases: ['license', 'licence', 'rights_license', 'licence_usage'],
    },
    'dcterms:title': {
      label: 'Titre Dublin Core',
      aliases: ['dc_title', 'dcterms_title'],
    },
    'dcterms:creator': {
      label: 'Créateur Dublin Core',
      aliases: ['dc_creator', 'dcterms_creator'],
    },
    'dcterms:created': {
      label: 'Date Dublin Core',
      aliases: ['dc_created', 'dcterms_created'],
    },
    'dcterms:license': {
      label: 'Licence Dublin Core',
      aliases: ['dc_license', 'dcterms_license'],
    },
    'dcterms:language': {
      label: 'Langue',
      aliases: ['language', 'lang', 'langue', 'iso_lang', 'language_code', 'langue_notice'],
    },
    'dcterms:description': {
      label: 'Description',
      aliases: ['description', 'desc', 'description_libre'],
    },
    'dcterms:description_*': {
      label: 'Description multilingue',
      aliases: [
        { pattern: /^description [a-z]{2,3}$/, label: 'description_{lang}', score: 1 },
        { pattern: /^resume [a-z]{2,3}$/, label: 'resume_{lang}', score: 0.99 },
        { pattern: /^abstract [a-z]{2,3}$/, label: 'abstract_{lang}', score: 0.99 },
      ],
    },
    'dcterms:subject': {
      label: 'Sujets / mots-clés',
      aliases: ['subject', 'subjects', 'keyword', 'keywords', 'topic', 'sujet', 'mots_cles', 'tags'],
    },
    'keywords_*': {
      label: 'Mots-clés multilingues',
      aliases: [
        { pattern: /^keywords? [a-z]{2,3}( \d+)?$/, label: 'keywords_{lang}', score: 1 },
        { pattern: /^mots cles [a-z]{2,3}( \d+)?$/, label: 'mots_cles_{lang}', score: 1 },
        { pattern: /^tags? [a-z]{2,3}( \d+)?$/, label: 'tags_{lang}', score: 0.98 },
      ],
    },
    'dcterms:publisher': {
      label: 'Éditeur',
      aliases: ['publisher', 'editeur', 'editor'],
    },
    'dcterms:contributor': {
      label: 'Contributeur',
      aliases: ['contributor', 'contributors', 'contributor_name', 'coauthor', 'co_author'],
    },
    'dcterms:rights': {
      label: 'Droits',
      aliases: ['rights', 'droits', 'copyright', 'access_rights'],
    },
    'dcterms:rightsHolder': {
      label: 'Titulaire des droits',
      aliases: ['rights_holder', 'copyright_holder', 'titulaire_droits', 'holder'],
    },
    'dcterms:relation': {
      label: 'Relation',
      aliases: ['relation', 'related_url', 'related_identifier', 'lien_associe'],
    },
    'dcterms:relation*': {
      label: 'Relation (motif)',
      aliases: [
        { pattern: /^relation( \d+)?$/, label: 'relation_n', score: 0.99 },
        { pattern: /^related (url|identifier)( \d+)?$/, label: 'related_url', score: 0.99 },
      ],
    },
    'dcterms:source': {
      label: 'Source',
      aliases: ['source', 'provenance', 'origin', 'origine'],
    },
    'dcterms:spatial': {
      label: 'Couverture spatiale',
      aliases: ['spatial', 'coverage', 'couverture_geo', 'location', 'lieu'],
    },
    'dcterms:available': {
      label: 'Date de disponibilité',
      aliases: ['available', 'date_available', 'publication_date', 'date_publication'],
    },
    'dcterms:modified': {
      label: 'Date de modification',
      aliases: ['modified', 'last_modified', 'updated_at', 'date_modified'],
    },
    'dcterms:format': {
      label: 'Format MIME',
      aliases: ['format', 'mime_type', 'file_format', 'content_type'],
    },
    'dcterms:abstract': {
      label: 'Résumé',
      aliases: ['abstract', 'resume', 'summary'],
    },
    'dcterms:mediator': {
      label: 'Médiateur',
      aliases: ['mediator', 'mediation', 'teacher', 'enseignant_referent'],
    },
    'dcterms:identifier': {
      label: 'Identifiant',
      aliases: ['identifier', 'identifier_uri', 'resource_identifier', 'uri', 'url', 'doi', 'ark'],
    },
    'dcterms:identifier*': {
      label: 'Identifiant / URI (motif)',
      aliases: [
        { pattern: /^identifier( \d+)?$/, label: 'identifier_n', score: 0.99 },
        { pattern: /^(doi|ark|uri|url)( \d+)?$/, label: 'doi|ark|uri|url', score: 0.99 },
      ],
    },
  });

  function normalizeTemplateColumnName(value) {
    return String(value || '')
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/['’]/g, ' ')
      .replace(/[^a-z0-9]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function _tokenize(value) {
    const normalized = normalizeTemplateColumnName(value);
    return normalized ? normalized.split(' ') : [];
  }

  function _normalizeAliasEntry(alias) {
    if (typeof alias === 'string') {
      return { kind: 'text', label: alias, value: alias };
    }
    if (alias && typeof alias === 'object' && alias.pattern instanceof RegExp) {
      return {
        kind: 'pattern',
        label: String(alias.label || alias.pattern.source),
        pattern: alias.pattern,
        score: typeof alias.score === 'number' ? alias.score : 0.98,
      };
    }
    return null;
  }

  function _evaluateAliasMatch(sourceNorm, sourceTokens, alias) {
    const aliasEntry = _normalizeAliasEntry(alias);
    if (!sourceNorm || !aliasEntry) return null;
    if (aliasEntry.kind === 'pattern') {
      if (!aliasEntry.pattern.test(sourceNorm)) return null;
      return {
        score: aliasEntry.score,
        matchKind: 'pattern',
        matchedAlias: aliasEntry.label,
      };
    }

    const aliasNorm = normalizeTemplateColumnName(aliasEntry.value);
    if (!sourceNorm || !aliasNorm) return null;
    const aliasTokens = _tokenize(aliasNorm);
    const sourceSet = new Set(sourceTokens);

    if (sourceNorm === aliasNorm) {
      return { score: 1, matchKind: 'exact', matchedAlias: aliasEntry.label };
    }
    if (sourceNorm.startsWith(`${aliasNorm} `) || sourceNorm.endsWith(` ${aliasNorm}`)) {
      return { score: 0.96, matchKind: 'edge', matchedAlias: aliasEntry.label };
    }
    if (sourceNorm.includes(` ${aliasNorm} `)) {
      return { score: 0.94, matchKind: 'contains_tokens', matchedAlias: aliasEntry.label };
    }
    if (aliasTokens.length > 0 && aliasTokens.every((token) => sourceSet.has(token))) {
      return { score: aliasTokens.length === sourceTokens.length ? 0.93 : 0.89, matchKind: 'token_subset', matchedAlias: aliasEntry.label };
    }
    if (sourceNorm.includes(aliasNorm)) {
      return { score: 0.86, matchKind: 'contains', matchedAlias: aliasEntry.label };
    }
    return null;
  }

  function _requirementRank(requirement) {
    if (requirement === 'required') return 2;
    if (requirement === 'recommended') return 1;
    return 0;
  }

  function getNakalaFieldLabel(fieldName) {
    const field = String(fieldName || '').trim();
    return TARGET_DEFINITIONS[field]?.label || field;
  }

  function suggestTemplateFieldMappings({
    availableColumns = [],
    templateColumns = {},
    templateColumnGroups = {},
    requiredColumns = [],
    recommendedColumns = [],
    userSavedColumns = {},
  } = {}) {
    const sourceColumns = Array.isArray(availableColumns)
      ? availableColumns.map((value) => String(value || '').trim()).filter(Boolean)
      : [];
    const templateTargets = [
      ...Object.keys(templateColumns || {}).filter(
        (fieldName) => TARGET_DEFINITIONS[String(fieldName || '').trim()]
      ).map((fieldName) => ({ targetField: fieldName, targetSource: 'column' })),
      ...Object.keys(templateColumnGroups || {}).filter(
        (fieldName) => TARGET_DEFINITIONS[String(fieldName || '').trim()]
      ).map((fieldName) => ({ targetField: fieldName, targetSource: 'column_group' })),
    ];
    const exactSourceSet = new Set(sourceColumns);
    const requiredSet = new Set((requiredColumns || []).map((value) => String(value || '').trim()).filter(Boolean));
    const recommendedSet = new Set((recommendedColumns || []).map((value) => String(value || '').trim()).filter(Boolean));

    if (templateTargets.length === 0 || sourceColumns.length === 0) {
      return { suggestions: [] };
    }

    const candidates = [];
    sourceColumns.forEach((sourceColumn) => {
      if (sourceColumn.includes(':')) return;
      const sourceNorm = normalizeTemplateColumnName(sourceColumn);
      const sourceTokens = _tokenize(sourceNorm);
      if (!sourceNorm) return;

      templateTargets.forEach(({ targetField, targetSource }) => {
        if (exactSourceSet.has(targetField)) return;
        const definition = TARGET_DEFINITIONS[targetField];
        if (!definition) return;

        const bestMatch = (definition.aliases || []).reduce((best, alias) => {
          const match = _evaluateAliasMatch(sourceNorm, sourceTokens, alias);
          if (!match) return best;
          if (!best || match.score > best.score) return match;
          return best;
        }, null);

        if (!bestMatch || bestMatch.score < 0.86) return;

        let requirement = 'template';
        if (requiredSet.has(targetField)) {
          requirement = 'required';
        } else if (recommendedSet.has(targetField)) {
          requirement = 'recommended';
        }

        candidates.push({
          sourceColumn,
          targetField,
          targetSource,
          targetLabel: getNakalaFieldLabel(targetField),
          requirement,
          score: bestMatch.score,
          matchKind: bestMatch.matchKind,
          matchedAlias: bestMatch.matchedAlias,
          userSaved: !!userSavedColumns?.[sourceColumn],
        });
      });
    });

    candidates.sort((left, right) => {
      if (!!left.userSaved !== !!right.userSaved) return left.userSaved ? 1 : -1;
      const scoreDelta = right.score - left.score;
      if (scoreDelta !== 0) return scoreDelta;
      const rankDelta = _requirementRank(right.requirement) - _requirementRank(left.requirement);
      if (rankDelta !== 0) return rankDelta;
      if (left.targetSource !== right.targetSource) {
        return left.targetSource === 'column' ? -1 : 1;
      }
      return left.sourceColumn.localeCompare(right.sourceColumn, 'fr');
    });

    const usedSources = new Set();
    const usedTargets = new Set();
    const suggestions = [];

    candidates.forEach((candidate) => {
      if (usedSources.has(candidate.sourceColumn) || usedTargets.has(candidate.targetField)) return;
      usedSources.add(candidate.sourceColumn);
      usedTargets.add(candidate.targetField);
      suggestions.push(candidate);
    });

    return { suggestions };
  }

  const api = {
    getNakalaFieldLabel,
    normalizeTemplateColumnName,
    suggestTemplateFieldMappings,
  };

  globalScope.TablerreurNakalaTemplateMatchHelpers = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
