const test = require("node:test");
const assert = require("node:assert");
const { esEmailValido } = require("../src/es-email-valido.js");

test("usuario@dominio.com es valido", () => {
  assert.strictEqual(esEmailValido("usuario@dominio.com"), true);
});

test("usuario@dominio sin extension es invalido", () => {
  assert.strictEqual(esEmailValido("usuario@dominio"), false);
});
