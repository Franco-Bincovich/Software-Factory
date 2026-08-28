// Unidad U1 - producida por el stub del Developer. No hubo modelo.
function resolverU1(entrada) {
  if (typeof entrada !== "string" || entrada.trim() === "") {
    return { ok: false, motivo: "vacio" };
  }
  return { ok: true, motivo: null, valor: entrada.trim() };
}

if (typeof module !== "undefined") {
  module.exports = { resolverU1 };
}
