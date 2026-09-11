// Real OMML equations, built with the docx Math primitives so that Word sees
// them as equation objects rather than styled text. One entry per numbered
// equation in the manuscript; the key is the leading token the markdown uses,
// so prepare_p2.py needs no equation-specific knowledge.
const d = require("docx");
const { Math: M, MathRun, MathFraction, MathNumerator, MathDenominator,
        MathSubScript, MathSuperScript, MathSubSuperScript, MathSum,
        MathRoundBrackets, MathSquareBrackets } = d;

const r = (t) => new MathRun(t);
const sub = (base, s) => new MathSubScript({
  children: [r(base)], subScript: [r(s)] });
const frac = (num, den) => new MathFraction({
  numerator: num, denominator: den });

// F^-1 with a subscript: rendered as a sub-superscript on F
const Finv = (s) => new MathSubSuperScript({
  children: [r("F")], subScript: [r(s)], superScript: [r("\u22121")] });

const EQUATIONS = {
  // (1) QM
  "QM: BC(": new M({ children: [
    r("BC"), new MathRoundBrackets({ children: [r("x")] }), r(" = "),
    Finv("obs,cal"),
    new MathRoundBrackets({ children: [
      sub("F", "mod,cal"),
      new MathRoundBrackets({ children: [r("x")] })] }),
  ]}),
  // (2) DetQM
  "DetQM: BC(": new M({ children: [
    r("BC"), new MathRoundBrackets({ children: [r("x")] }), r(" = s \u00b7 "),
    Finv("obs,cal"),
    new MathRoundBrackets({ children: [
      sub("F", "mod,cal"),
      new MathRoundBrackets({ children: [frac([r("x")], [r("s")])] })] }),
    r(",   s = "),
    frac([sub("\u03bc", "tgt")], [sub("\u03bc", "cal")]),
  ]}),
  // (3) QDM
  "QDM: BC(": new M({ children: [
    r("BC"), new MathRoundBrackets({ children: [r("x")] }), r(" = "),
    Finv("obs,cal"), new MathRoundBrackets({ children: [r("p")] }), r(" \u00b7 "),
    new MathSquareBrackets({ children: [
      frac([r("x")], [Finv("mod,cal"),
                      new MathRoundBrackets({ children: [r("p")] })])] }),
    r(",   p = "), sub("F", "mod,tgt"),
    new MathRoundBrackets({ children: [r("x")] }),
  ]}),
  // (4) MAB. Absolute-value bars wrapped around a fraction survive Word but are
  // mangled by other OMML consumers, so the summand is named and defined on the
  // next line; this renders identically everywhere.
  "MAB(": new M({ children: [
    r("MAB"), new MathRoundBrackets({ children: [r("k")] }), r(" = "),
    frac([r("1")], [r("NM")]),
    new MathSum({
      subScript: [r("i = 1")], superScript: [r("N")],
      children: [new MathSum({
        subScript: [r("j = 1")], superScript: [r("M")],
        children: [r("\u2223"), sub("\u03b5", "ijk"), r("\u2223")]})],
    }),
  ]}),
  // (4b) the summand
  "*\u03b5*~": new M({ children: [
    sub("\u03b5", "ijk"), r(" = 100 \u00b7 "),
    frac([sub("S", "ijk"), r(" \u2212 "), sub("O", "ik")], [sub("O", "ik")]),
  ]}),
  // (5) raw and corrected signal ratios
  "*S*": new M({ children: [
    sub("S", "raw"), r(" = "),
    frac([sub("q", "fut,raw")], [sub("q", "base,raw")]),
    r(",     "),
    sub("S", "BC"), r(" = "),
    frac([sub("q", "fut,BC")], [sub("q", "base,BC")]),
  ]}),
  // (6) signal-preservation error
  "PE(": new M({ children: [
    r("PE"), new MathRoundBrackets({ children: [r("q")] }), r(" = 100 \u00b7 "),
    frac([sub("S", "BC"), new MathRoundBrackets({ children: [r("q")] }),
          r(" \u2212 "), sub("S", "raw"),
          new MathRoundBrackets({ children: [r("q")] })],
         [sub("S", "raw"), new MathRoundBrackets({ children: [r("q")] })]),
  ]}),
  // (7) the canonical ensemble estimator
  "*E*~*j*~": new M({ children: [
    sub("E", "j"), r(" = "),
    frac([r("1")], [sub("N", "j")]),
    new MathSum({ subScript: [r("i = 1")], superScript: [sub("N", "j")],
                  children: [sub("PE", "ijkmc")] }),
    r(",    reported value = "),
    r("median"), new MathRoundBrackets({ children: [sub("E", "j")] }),
  ]}),
};

module.exports = { EQUATIONS };
