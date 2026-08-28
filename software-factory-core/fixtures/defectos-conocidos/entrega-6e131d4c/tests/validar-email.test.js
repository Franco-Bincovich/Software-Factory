const test = require("node:test");
const assert = require("node:assert");
const { esEmailValido } = require("../src/validar-email.js");

test("a@b.com es valido", () => {
  assert.strictEqual(esEmailValido("a@b.com"), true);
});

test("juan.perez@empresa.com.ar es valido", () => {
  assert.strictEqual(esEmailValido("juan.perez@empresa.com.ar"), true);
});

test("nombre@dominio.io es valido", () => {
  assert.strictEqual(esEmailValido("nombre@dominio.io"), true);
});

test("user.name+tag@sub.dominio.com es valido", () => {
  assert.strictEqual(esEmailValido("user.name+tag@sub.dominio.com"), true);
});

test("x@y.co es valido", () => {
  assert.strictEqual(esEmailValido("x@y.co"), true);
});

test("texto-sin-arroba es invalido", () => {
  assert.strictEqual(esEmailValido("texto-sin-arroba"), false);
});

test("@dominio.com es invalido", () => {
  assert.strictEqual(esEmailValido("@dominio.com"), false);
});

test("usuario@ es invalido", () => {
  assert.strictEqual(esEmailValido("usuario@"), false);
});

test("usuario@dominio es invalido", () => {
  assert.strictEqual(esEmailValido("usuario@dominio"), false);
});

test("usuario con espacio antes de arroba es invalido", () => {
  assert.strictEqual(esEmailValido("usuario @dominio.com"), false);
});
