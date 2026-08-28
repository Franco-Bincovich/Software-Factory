const test = require("node:test");
const assert = require("node:assert");
const { resolverU1 } = require("../src/u1.js");

test("una entrada con texto se resuelve", () => {
  assert.deepStrictEqual(resolverU1("dato"), { ok: true, motivo: null, valor: "dato" });
});

test("una entrada vacia se rechaza", () => {
  assert.deepStrictEqual(resolverU1(""), { ok: false, motivo: "vacio" });
});
