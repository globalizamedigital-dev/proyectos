/**
 * Estado mock de cada fuente. El backend real expone esto vía SourceStatus
 * snapshot. Aquí cableado a mano para que la barra de estado tenga vida.
 */

export type SourceState = "ok" | "stub" | "down";

export interface SourceIndicator {
  key: string;
  state: SourceState;
  label: string;
  hint: string;
}

export const SOURCE_INDICATORS: readonly SourceIndicator[] = [
  { key: "BORME", state: "ok", label: "BORME", hint: "Boletín del Registro Mercantil — al día" },
  { key: "OSM", state: "ok", label: "OSM", hint: "Overpass API — mirror operativo" },
  { key: "Cartociudad", state: "ok", label: "Cartociudad", hint: "Geocoding IGN — respuesta normal" },
  { key: "PLACSP", state: "stub", label: "PLACSP", hint: "Requiere certificado cliente — degradado" },
  { key: "AEPD", state: "stub", label: "AEPD", hint: "Migrado a SPA — lookup parcial" },
  { key: "DDG", state: "down", label: "DDG", hint: "CAPTCHA detectado — fuente caída" },
];
