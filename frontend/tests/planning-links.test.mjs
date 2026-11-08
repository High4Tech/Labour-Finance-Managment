import test from 'node:test';
import assert from 'node:assert/strict';
import {planningRecordHref} from '../src/planning-links.mjs';

test('saved events open details independently of planning status or an edit draft', () => {
  for (const planning_state of ['Draft', 'Ready']) {
    for (const pp_draft_name of [undefined, 'pending-edit']) {
      assert.equal(planningRecordHref('pp-event-plans', {
        name: 'saved-event', planning_state, pp_draft_name,
      }), '/desk/pp-event-plans?record=saved-event');
    }
  }
});

test('unsaved projected drafts resume their respective creation form', () => {
  for (const path of ['pp-event-plans', 'pp-agreements']) {
    assert.equal(planningRecordHref(path, {name: 'draft:partial', pp_draft_name: 'partial'}),
      '/desk/' + path + '?draft=partial');
  }
});
