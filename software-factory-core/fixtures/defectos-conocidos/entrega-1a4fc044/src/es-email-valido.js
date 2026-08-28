// Valida que una cadena tenga el formato usuario@dominio.tld
function esEmailValido(valor) {
  if (typeof valor !== "string") {
    return false;
  }
  const patron = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return patron.test(valor);
}

if (typeof module !== "undefined") {
  module.exports = { esEmailValido };
}
