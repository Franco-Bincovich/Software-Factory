// Determina si una cadena es sintacticamente una direccion de email
// valida, con el formato local@dominio.tld.
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
