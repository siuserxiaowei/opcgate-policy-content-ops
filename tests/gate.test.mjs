import test from "node:test";
import assert from "node:assert/strict";
import { evaluatePublicationGate } from "../public/gate.js";

test("publication gate stays locked until every required review is checked", () => {
  assert.deepEqual(
    evaluatePublicationGate([
      { required: true, checked: true },
      { required: true, checked: false },
      { required: false, checked: false }
    ]),
    { total: 2, completed: 1, open: false }
  );
  assert.deepEqual(
    evaluatePublicationGate([
      { required: true, checked: true },
      { required: true, checked: true }
    ]),
    { total: 2, completed: 2, open: true }
  );
  assert.equal(evaluatePublicationGate([]).open, false);
});
