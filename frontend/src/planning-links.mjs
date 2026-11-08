// Only projected, unsaved drafts resume the wizard. Saved records open their
// profile even when they have an unfinished edit draft attached to them.
export function planningRecordHref(path, row) {
  const draft = row.name.startsWith('draft:') && row.pp_draft_name;
  return '/desk/' + path + (draft
    ? '?draft=' + encodeURIComponent(draft)
    : '?record=' + encodeURIComponent(row.name));
}
