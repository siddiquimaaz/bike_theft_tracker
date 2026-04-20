import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeNotificationList } from './notifications.js';

test('normalizes nested paginated notifications payload', () => {
  const payload = {
    unread_count: 1,
    results: {
      count: 2,
      next: null,
      previous: null,
      results: [
        { id: 1, is_read: false },
        { id: 2, is_read: true },
      ],
    },
  };

  const list = normalizeNotificationList(payload);
  assert.equal(Array.isArray(list), true);
  assert.equal(list.length, 2);
  assert.equal(list[0].id, 1);
  assert.equal(list[0].is_read, false);
});
